from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.weather import get_forecast


BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"

app = FastAPI(
    title="NeutWeather API",
    description="Weather intelligence dashboard built by Ahmed Omar.",
    version="2.0.0",
)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


CITY_SUGGESTIONS = [
    {"city": "Abu Dhabi", "country": "United Arab Emirates", "code": "AE"},
    {"city": "Alexandria", "country": "Egypt", "code": "EG"},
    {"city": "Amman", "country": "Jordan", "code": "JO"},
    {"city": "Amsterdam", "country": "Netherlands", "code": "NL"},
    {"city": "Athens", "country": "Greece", "code": "GR"},
    {"city": "Baghdad", "country": "Iraq", "code": "IQ"},
    {"city": "Barcelona", "country": "Spain", "code": "ES"},
    {"city": "Beirut", "country": "Lebanon", "code": "LB"},
    {"city": "Berlin", "country": "Germany", "code": "DE"},
    {"city": "Bucharest", "country": "Romania", "code": "RO"},
    {"city": "Cairo", "country": "Egypt", "code": "EG"},
    {"city": "Cape Town", "country": "South Africa", "code": "ZA"},
    {"city": "Casablanca", "country": "Morocco", "code": "MA"},
    {"city": "Dammam", "country": "Saudi Arabia", "code": "SA"},
    {"city": "Doha", "country": "Qatar", "code": "QA"},
    {"city": "Dubai", "country": "United Arab Emirates", "code": "AE"},
    {"city": "Frankfurt", "country": "Germany", "code": "DE"},
    {"city": "Giza", "country": "Egypt", "code": "EG"},
    {"city": "Istanbul", "country": "Türkiye", "code": "TR"},
    {"city": "Jeddah", "country": "Saudi Arabia", "code": "SA"},
    {"city": "Khobar", "country": "Saudi Arabia", "code": "SA"},
    {"city": "Kuwait City", "country": "Kuwait", "code": "KW"},
    {"city": "London", "country": "United Kingdom", "code": "GB"},
    {"city": "Madrid", "country": "Spain", "code": "ES"},
    {"city": "Manama", "country": "Bahrain", "code": "BH"},
    {"city": "Manchester", "country": "United Kingdom", "code": "GB"},
    {"city": "Mecca", "country": "Saudi Arabia", "code": "SA"},
    {"city": "Medina", "country": "Saudi Arabia", "code": "SA"},
    {"city": "Melbourne", "country": "Australia", "code": "AU"},
    {"city": "Milan", "country": "Italy", "code": "IT"},
    {"city": "Munich", "country": "Germany", "code": "DE"},
    {"city": "Muscat", "country": "Oman", "code": "OM"},
    {"city": "New York", "country": "United States", "code": "US"},
    {"city": "Paris", "country": "France", "code": "FR"},
    {"city": "Riyadh", "country": "Saudi Arabia", "code": "SA"},
    {"city": "Rome", "country": "Italy", "code": "IT"},
    {"city": "Sharjah", "country": "United Arab Emirates", "code": "AE"},
    {"city": "Sydney", "country": "Australia", "code": "AU"},
    {"city": "Toronto", "country": "Canada", "code": "CA"},
    {"city": "Vienna", "country": "Austria", "code": "AT"},
]


def first_value(data: dict[str, Any], *keys: str) -> Any:
    """Return the first existing value, allowing for provider-specific key names."""
    for key in keys:
        if key in data and data[key] is not None:
            return data[key]
    return None


def to_celsius(value: Any) -> float | None:
    """Normalize temperature values. Values above 170 are treated as Kelvin."""
    if value is None:
        return None

    try:
        numeric_value = float(value)
    except (TypeError, ValueError):
        return None

    if numeric_value > 170:
        numeric_value -= 273.15

    return round(numeric_value, 1)


def rain_probability_percent(value: Any) -> int | None:
    if value is None:
        return None

    try:
        numeric_value = float(value)
    except (TypeError, ValueError):
        return None

    if numeric_value <= 1:
        numeric_value *= 100

    return max(0, min(100, round(numeric_value)))


@app.get("/", include_in_schema=False)
def home() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/health", tags=["System"])
def health() -> dict[str, str]:
    return {"status": "healthy", "service": "neutweather-api"}


@app.get("/cities", tags=["Cities"])
def cities(
    q: str = Query(default="", max_length=60),
    limit: int = Query(default=8, ge=1, le=12),
) -> dict[str, list[dict[str, str]]]:
    """Return lightweight autocomplete suggestions for the frontend."""
    query = q.strip().lower()

    if not query:
        return {"suggestions": CITY_SUGGESTIONS[:limit]}

    starts_with = []
    contains = []

    for city in CITY_SUGGESTIONS:
        searchable = f"{city['city']} {city['country']} {city['code']}".lower()

        if city["city"].lower().startswith(query):
            starts_with.append(city)
        elif query in searchable:
            contains.append(city)

    return {"suggestions": (starts_with + contains)[:limit]}


@app.get("/forecast", tags=["Forecast"])
def forecast(
    city: str = Query(default="Cairo,EG", min_length=2, max_length=80),
    days: int = Query(default=3, ge=1, le=5),
) -> dict[str, Any]:
    try:
        data = get_forecast(city, days)

        if not isinstance(data, dict):
            raise ValueError("Invalid response received from the weather provider")

        city_data = data.get("city", {})
        forecast_items = data.get("list", [])

        if not forecast_items:
            raise ValueError("No forecast data found for this city")

        normalized_forecast = []

        for item in forecast_items:
            main_data = item.get("main", {})
            wind_data = item.get("wind", {})
            weather_items = item.get("weather") or [{}]
            weather_data = weather_items[0] if weather_items else {}

            normalized_forecast.append(
                {
                    "date_time": first_value(item, "dt_txt", "date_time"),
                    "timestamp": first_value(item, "dt", "timestamp"),
                    "temperature_c": to_celsius(
                        first_value(main_data, "temprature", "temperature", "temp")
                    ),
                    "feels_like_c": to_celsius(
                        first_value(
                            main_data,
                            "temprature_feels_like",
                            "temperature_feels_like",
                            "feels_like",
                        )
                    ),
                    "temp_min_c": to_celsius(first_value(main_data, "temp_min")),
                    "temp_max_c": to_celsius(first_value(main_data, "temp_max")),
                    "humidity": main_data.get("humidity"),
                    "pressure_hpa": main_data.get("pressure"),
                    "condition": weather_data.get("description", "Unknown"),
                    "condition_main": weather_data.get("main", "Unknown"),
                    "weather_icon": weather_data.get("icon"),
                    "wind_speed": wind_data.get("speed"),
                    "wind_direction": first_value(wind_data, "direction", "deg"),
                    "rain_probability": rain_probability_percent(
                        first_value(item, "probability_of_precipitation", "pop")
                    ),
                    "cloudiness": item.get("clouds", {}).get("all"),
                    "visibility_m": item.get("visibility"),
                }
            )

        return {
            "brand": "NeutWeather",
            "city": city_data.get("name", city.split(",")[0]),
            "country": city_data.get("country", ""),
            "forecast_count": len(normalized_forecast),
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "forecast": normalized_forecast,
        }

    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error)) from error
