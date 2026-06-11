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

FORECAST_ENDPOINT = os.getenv(
    "WEATHER_FORECAST_ENDPOINT",
    "/api/weather/forecast",
).strip()

CACHE_TTL_SECONDS = int(
    os.getenv("WEATHER_CACHE_TTL_SECONDS", "600")
)

_cache: dict[tuple[str, int], tuple[float, dict[str, Any]]] = {}
_cache_lock = Lock()


def normalize_place(value: str) -> str:
    """Remove duplicated country codes before calling RapidAPI.

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


def _cache_key(place: str, count: int) -> tuple[str, int]:
    return place.casefold(), count


def _get_cached_forecast(place: str, count: int) -> dict[str, Any] | None:
    key = _cache_key(place, count)

    with _cache_lock:
        cached = _cache.get(key)

        if cached is None:
            return None

        created_at, payload = cached

        if time.monotonic() - created_at > CACHE_TTL_SECONDS:
            _cache.pop(key, None)
            return None

        return payload


def _store_cached_forecast(
    place: str,
    count: int,
    payload: dict[str, Any],
) -> None:
    key = _cache_key(place, count)

    with _cache_lock:
        _cache[key] = (time.monotonic(), payload)


def _validate_configuration() -> None:
    if not RAPIDAPI_KEY:
        raise WeatherProviderError(
            "RAPIDAPI_KEY is missing. Add it to your .env file."
        )

    if not RAPIDAPI_HOST:
        raise WeatherProviderError(
            "RAPIDAPI_HOST is missing. Add it to your .env file."
        )


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


def get_forecast(place: str, days: int = 3) -> dict[str, Any]:
    """Fetch a weather forecast and reuse successful responses temporarily.

    The short in-memory cache reduces accidental RapidAPI quota consumption
    when the same city is requested repeatedly from the frontend.
    """
    _validate_configuration()

    normalized_place = normalize_place(place)

    try:
        count = int(days)
    except (TypeError, ValueError) as error:
        raise WeatherProviderError("Forecast count must be an integer.") from error

    count = max(1, min(5, count))

    cached = _get_cached_forecast(normalized_place, count)

    if cached is not None:
        return cached

    url = f"https://{RAPIDAPI_HOST}{FORECAST_ENDPOINT}"

    headers = {
        "x-rapidapi-key": RAPIDAPI_KEY,
        "x-rapidapi-host": RAPIDAPI_HOST,
    }

    params = {
        "place": normalized_place,
        "cnt": count,
        "units": "standard",
        "type": "three_hour",
        "mode": "json",
        "lang": "en",
    }

    try:
        response = requests.get(
            url,
            headers=headers,
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

    _store_cached_forecast(normalized_place, count, payload)

    return payload
