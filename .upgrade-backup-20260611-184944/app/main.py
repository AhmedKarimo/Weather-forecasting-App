from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.database import Base, engine, get_db
from app.models import SearchHistory
from app.weather import get_forecast


# ---------------------------------------------------------
# Application paths
# ---------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"


# ---------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------

app = FastAPI(
    title="NeutWeather API",
    description="Weather intelligence dashboard built by Ahmed Omar.",
    version="2.1.0",
)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


# Create database tables if they do not exist.
# Later, when the project grows, use Alembic migrations instead.
Base.metadata.create_all(bind=engine)


# ---------------------------------------------------------
# City suggestions for autocomplete
# ---------------------------------------------------------

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


# ---------------------------------------------------------
# Helper functions
# ---------------------------------------------------------

def first_value(data: dict[str, Any], *keys: str) -> Any:
    """
    Return the first available value from a dictionary.

    Weather providers sometimes use different names for the same field.
    Example: temperature may be called temp, temperature or temprature.
    """
    for key in keys:
        if key in data and data[key] is not None:
            return data[key]

    return None


def to_celsius(value: Any) -> float | None:
    """
    Convert a temperature value to Celsius.

    Values above 170 are treated as Kelvin.
    """
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
    """
    Normalize rain probability to a value between 0 and 100.
    """
    if value is None:
        return None

    try:
        numeric_value = float(value)
    except (TypeError, ValueError):
        return None

    if numeric_value <= 1:
        numeric_value *= 100

    return max(0, min(100, round(numeric_value)))


def save_search_history(
    db: Session,
    city: str,
    country: str,
) -> None:
    """
    Store a successful city search in PostgreSQL.
    """
    search = SearchHistory(
        city=city,
        country=country,
    )

    try:
        db.add(search)
        db.commit()
    except SQLAlchemyError as error:
        db.rollback()

        raise HTTPException(
            status_code=500,
            detail="Forecast loaded, but search history could not be saved.",
        ) from error


# ---------------------------------------------------------
# Frontend route
# ---------------------------------------------------------

@app.get("/", include_in_schema=False)
def home() -> FileResponse:
    """
    Serve the frontend homepage.
    """
    return FileResponse(STATIC_DIR / "index.html")


# ---------------------------------------------------------
# Health check
# ---------------------------------------------------------

@app.get("/health", tags=["System"])
def health() -> dict[str, str]:
    """
    Health endpoint used by Docker, Kubernetes and monitoring tools.
    """
    return {
        "status": "healthy",
        "service": "neutweather-api",
    }


# ---------------------------------------------------------
# City autocomplete
# ---------------------------------------------------------

@app.get("/cities", tags=["Cities"])
def cities(
    q: str = Query(default="", max_length=60),
    limit: int = Query(default=8, ge=1, le=12),
) -> dict[str, list[dict[str, str]]]:
    """
    Return city suggestions for the frontend dropdown.
    """
    query = q.strip().lower()

    if not query:
        return {
            "suggestions": CITY_SUGGESTIONS[:limit],
        }

    starts_with = []
    contains = []

    for city_item in CITY_SUGGESTIONS:
        searchable = (
            f"{city_item['city']} "
            f"{city_item['country']} "
            f"{city_item['code']}"
        ).lower()

        if city_item["city"].lower().startswith(query):
            starts_with.append(city_item)
        elif query in searchable:
            contains.append(city_item)

    return {
        "suggestions": (starts_with + contains)[:limit],
    }


# ---------------------------------------------------------
# Weather forecast
# ---------------------------------------------------------

@app.get("/forecast", tags=["Forecast"])
def forecast(
    city: str = Query(default="Cairo,EG", min_length=2, max_length=80),
    days: int = Query(default=3, ge=1, le=5),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """
    Fetch the weather forecast from RapidAPI and save the successful
    search in PostgreSQL.
    """
    try:
        data = get_forecast(city, days)

        if not isinstance(data, dict):
            raise ValueError(
                "Invalid response received from the weather provider."
            )

        city_data = data.get("city", {})
        forecast_items = data.get("list", [])

        if not isinstance(city_data, dict):
            city_data = {}

        if not isinstance(forecast_items, list) or not forecast_items:
            raise ValueError(
                "No forecast data found for this city."
            )

        normalized_forecast = []

        for item in forecast_items:
            if not isinstance(item, dict):
                continue

            main_data = item.get("main", {})
            wind_data = item.get("wind", {})
            clouds_data = item.get("clouds", {})
            weather_items = item.get("weather") or [{}]

            if not isinstance(main_data, dict):
                main_data = {}

            if not isinstance(wind_data, dict):
                wind_data = {}

            if not isinstance(clouds_data, dict):
                clouds_data = {}

            weather_data = (
                weather_items[0]
                if isinstance(weather_items, list) and weather_items
                else {}
            )

            if not isinstance(weather_data, dict):
                weather_data = {}

            normalized_forecast.append(
                {
                    "date_time": first_value(
                        item,
                        "dt_txt",
                        "date_time",
                    ),
                    "timestamp": first_value(
                        item,
                        "dt",
                        "timestamp",
                    ),
                    "temperature_c": to_celsius(
                        first_value(
                            main_data,
                            "temprature",
                            "temperature",
                            "temp",
                        )
                    ),
                    "feels_like_c": to_celsius(
                        first_value(
                            main_data,
                            "temprature_feels_like",
                            "temperature_feels_like",
                            "feels_like",
                        )
                    ),
                    "temp_min_c": to_celsius(
                        first_value(
                            main_data,
                            "temp_min",
                        )
                    ),
                    "temp_max_c": to_celsius(
                        first_value(
                            main_data,
                            "temp_max",
                        )
                    ),
                    "humidity": main_data.get("humidity"),
                    "pressure_hpa": main_data.get("pressure"),
                    "condition": weather_data.get(
                        "description",
                        "Unknown",
                    ),
                    "condition_main": weather_data.get(
                        "main",
                        "Unknown",
                    ),
                    "weather_icon": weather_data.get("icon"),
                    "wind_speed": wind_data.get("speed"),
                    "wind_direction": first_value(
                        wind_data,
                        "direction",
                        "deg",
                    ),
                    "rain_probability": rain_probability_percent(
                        first_value(
                            item,
                            "probability_of_precipitation",
                            "pop",
                        )
                    ),
                    "cloudiness": clouds_data.get("all"),
                    "visibility_m": item.get("visibility"),
                }
            )

        if not normalized_forecast:
            raise ValueError(
                "No usable forecast data found for this city."
            )

        city_name = city_data.get(
            "name",
            city.split(",")[0],
        )

        country_code = city_data.get(
            "country",
            "",
        )

        save_search_history(
            db=db,
            city=city_name,
            country=country_code,
        )

        return {
            "brand": "NeutWeather",
            "city": city_name,
            "country": country_code,
            "forecast_count": len(normalized_forecast),
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "forecast": normalized_forecast,
        }

    except HTTPException:
        raise

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=str(error),
        ) from error


# ---------------------------------------------------------
# Search history
# ---------------------------------------------------------

@app.get("/history", tags=["History"])
def history(
    limit: int = Query(default=10, ge=1, le=50),
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    """
    Return the most recent successful city searches from PostgreSQL.
    """
    try:
        searches = (
            db.query(SearchHistory)
            .order_by(SearchHistory.created_at.desc())
            .limit(limit)
            .all()
        )

        return [
            {
                "id": search.id,
                "city": search.city,
                "country": search.country,
                "created_at": search.created_at,
            }
            for search in searches
        ]

    except SQLAlchemyError as error:
        raise HTTPException(
            status_code=500,
            detail="Search history could not be loaded.",
        ) from error