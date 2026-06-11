import os
import time
from threading import Lock
from typing import Any

import requests
from requests import Response
from requests.exceptions import RequestException


class WeatherProviderError(RuntimeError):
    """Raised when the weather provider cannot return a valid response."""


class RapidApiRateLimitError(WeatherProviderError):
    """Raised when RapidAPI rejects a request because the quota is exhausted."""


RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY", "").strip()
RAPIDAPI_HOST = os.getenv(
    "RAPIDAPI_HOST",
    "open-weather13.p.rapidapi.com",
).strip()

CITY_ENDPOINT = os.getenv(
    "WEATHER_CITY_ENDPOINT",
    "/city",
).strip()

FORECAST_ENDPOINT = os.getenv(
    "WEATHER_FORECAST_ENDPOINT",
    "/fivedaysforcast",
).strip()

WEATHER_LANGUAGE = os.getenv(
    "WEATHER_LANGUAGE",
    "EN",
).strip().upper()

CACHE_TTL_SECONDS = int(
    os.getenv("WEATHER_CACHE_TTL_SECONDS", "600")
)

COORDINATE_CACHE_TTL_SECONDS = int(
    os.getenv("WEATHER_COORDINATE_CACHE_TTL_SECONDS", "86400")
)

_forecast_cache: dict[tuple[str, int], tuple[float, dict[str, Any]]] = {}
_coordinate_cache: dict[str, tuple[float, tuple[float, float]]] = {}
_cache_lock = Lock()


def normalize_place(value: str) -> str:
    """Normalize a city query and remove duplicated country codes.

    Examples:
        Cairo,EG,EG -> Cairo,EG
        Riyadh,SA   -> Riyadh,SA
        London      -> London
    """
    parts = [part.strip() for part in value.split(",") if part.strip()]

    if not parts:
        raise WeatherProviderError("City cannot be empty.")

    city_name = parts[0]

    country_code = next(
        (
            part.upper()
            for part in parts[1:]
            if len(part) == 2 and part.isalpha()
        ),
        "",
    )

    return f"{city_name},{country_code}" if country_code else city_name


def _validate_configuration() -> None:
    if not RAPIDAPI_KEY:
        raise WeatherProviderError(
            "RAPIDAPI_KEY is missing. Add it to your .env file."
        )

    if not RAPIDAPI_HOST:
        raise WeatherProviderError(
            "RAPIDAPI_HOST is missing. Add it to your .env file."
        )


def _headers() -> dict[str, str]:
    return {
        "Content-Type": "application/json",
        "x-rapidapi-key": RAPIDAPI_KEY,
        "x-rapidapi-host": RAPIDAPI_HOST,
    }


def _raise_for_provider_error(response: Response) -> None:
    if response.status_code == 429:
        retry_after = response.headers.get("Retry-After")

        message = (
            "RapidAPI request limit reached. "
            "Wait until your quota resets or review your RapidAPI plan."
        )

        if retry_after:
            message += f" Retry after: {retry_after} seconds."

        raise RapidApiRateLimitError(message)

    if response.status_code in {401, 403}:
        raise WeatherProviderError(
            "RapidAPI authentication failed. "
            "Check RAPIDAPI_KEY and RAPIDAPI_HOST in your .env file."
        )

    if response.status_code == 404:
        raise WeatherProviderError(
            "The requested city was not found by the weather provider."
        )

    try:
        response.raise_for_status()
    except RequestException as error:
        raise WeatherProviderError(
            f"Weather provider returned HTTP {response.status_code}."
        ) from error


def _request_json(endpoint: str, params: dict[str, Any]) -> dict[str, Any]:
    url = f"https://{RAPIDAPI_HOST}{endpoint}"

    try:
        response = requests.get(
            url,
            headers=_headers(),
            params=params,
            timeout=10,
        )
    except RequestException as error:
        raise WeatherProviderError(
            "Could not connect to the weather provider."
        ) from error

    _raise_for_provider_error(response)

    try:
        payload = response.json()
    except ValueError as error:
        raise WeatherProviderError(
            "Weather provider returned an invalid JSON response."
        ) from error

    if not isinstance(payload, dict):
        raise WeatherProviderError(
            "Weather provider returned an unexpected response."
        )

    provider_code = str(payload.get("cod", "200"))

    if provider_code not in {"200", ""}:
        provider_message = payload.get(
            "message",
            "Weather provider returned an error.",
        )

        raise WeatherProviderError(str(provider_message))

    return payload


def _get_cached_coordinates(place: str) -> tuple[float, float] | None:
    key = place.casefold()

    with _cache_lock:
        cached = _coordinate_cache.get(key)

        if cached is None:
            return None

        created_at, coordinates = cached

        if time.monotonic() - created_at > COORDINATE_CACHE_TTL_SECONDS:
            _coordinate_cache.pop(key, None)
            return None

        return coordinates


def _store_cached_coordinates(
    place: str,
    latitude: float,
    longitude: float,
) -> None:
    key = place.casefold()

    with _cache_lock:
        _coordinate_cache[key] = (
            time.monotonic(),
            (latitude, longitude),
        )


def _extract_coordinates(payload: dict[str, Any]) -> tuple[float, float]:
    coord = payload.get("coord", {})

    if not isinstance(coord, dict):
        coord = {}

    latitude = coord.get("lat")
    longitude = coord.get("lon")

    if latitude is None or longitude is None:
        raise WeatherProviderError(
            "Weather provider did not return coordinates for this city."
        )

    try:
        return float(latitude), float(longitude)
    except (TypeError, ValueError) as error:
        raise WeatherProviderError(
            "Weather provider returned invalid city coordinates."
        ) from error


def _resolve_coordinates(place: str) -> tuple[float, float]:
    cached = _get_cached_coordinates(place)

    if cached is not None:
        return cached

    payload = _request_json(
        CITY_ENDPOINT,
        {
            "city": place,
            "lang": WEATHER_LANGUAGE,
        },
    )

    latitude, longitude = _extract_coordinates(payload)

    _store_cached_coordinates(
        place=place,
        latitude=latitude,
        longitude=longitude,
    )

    return latitude, longitude


def _get_cached_forecast(
    place: str,
    days: int,
) -> dict[str, Any] | None:
    key = (place.casefold(), days)

    with _cache_lock:
        cached = _forecast_cache.get(key)

        if cached is None:
            return None

        created_at, payload = cached

        if time.monotonic() - created_at > CACHE_TTL_SECONDS:
            _forecast_cache.pop(key, None)
            return None

        return payload


def _store_cached_forecast(
    place: str,
    days: int,
    payload: dict[str, Any],
) -> None:
    key = (place.casefold(), days)

    with _cache_lock:
        _forecast_cache[key] = (
            time.monotonic(),
            payload,
        )


def _limit_forecast_days(
    payload: dict[str, Any],
    days: int,
) -> dict[str, Any]:
    """Keep only the requested number of days.

    The provider returns forecasts every 3 hours:
    8 forecast entries per day and up to 40 entries for 5 days.
    """
    forecast_items = payload.get("list")

    if not isinstance(forecast_items, list):
        raise WeatherProviderError(
            "Weather provider response does not include a forecast list."
        )

    limited_payload = dict(payload)
    limited_payload["list"] = forecast_items[: days * 8]
    limited_payload["cnt"] = len(limited_payload["list"])

    return limited_payload


def get_forecast(place: str, days: int = 3) -> dict[str, Any]:
    """Fetch a forecast by city name while the provider uses coordinates.

    Flow:
        city name -> GET /city -> latitude and longitude
        coordinates -> GET /fivedaysforcast -> forecast JSON
    """
    _validate_configuration()

    normalized_place = normalize_place(place)

    try:
        normalized_days = int(days)
    except (TypeError, ValueError) as error:
        raise WeatherProviderError(
            "Forecast days must be an integer."
        ) from error

    normalized_days = max(1, min(5, normalized_days))

    cached = _get_cached_forecast(
        place=normalized_place,
        days=normalized_days,
    )

    if cached is not None:
        return cached

    latitude, longitude = _resolve_coordinates(normalized_place)

    payload = _request_json(
        FORECAST_ENDPOINT,
        {
            "latitude": latitude,
            "longitude": longitude,
            "lang": WEATHER_LANGUAGE,
        },
    )

    limited_payload = _limit_forecast_days(
        payload=payload,
        days=normalized_days,
    )

    _store_cached_forecast(
        place=normalized_place,
        days=normalized_days,
        payload=limited_payload,
    )

    return limited_payload
