from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Query, Response, status
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.database import Base, engine, get_db
from app.models import Favorite, SearchHistory
from app.schemas import (
    DeleteResponse,
    FavoriteCreate,
    FavoriteRead,
    FavoriteUpdate,
    SearchHistoryCreate,
    SearchHistoryRead,
    SearchHistoryUpdate,
)
from app.weather import RapidApiRateLimitError, WeatherProviderError, get_forecast


BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"

app = FastAPI(
    title="NeutWeather API",
    description="Weather intelligence dashboard built by Ahmed Omar.",
    version="3.0.0",
)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Suitable for this learning project. Introduce Alembic migrations when the
# database schema starts changing between deployed versions.
Base.metadata.create_all(bind=engine)


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
    """Return the first present, non-null value from a dictionary."""
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


def clean_city(value: str) -> str:
    city = value.strip()
    if not city:
        raise HTTPException(status_code=422, detail="City cannot be empty.")
    return city


def clean_country_code(value: str) -> str:
    return value.strip().upper()


def get_favorite_or_404(db: Session, favorite_id: int) -> Favorite:
    favorite = db.get(Favorite, favorite_id)
    if favorite is None:
        raise HTTPException(status_code=404, detail="Favorite city not found.")
    return favorite


def get_history_or_404(db: Session, history_id: int) -> SearchHistory:
    history_item = db.get(SearchHistory, history_id)
    if history_item is None:
        raise HTTPException(status_code=404, detail="Search history item not found.")
    return history_item


def favorite_exists(
    db: Session,
    city: str,
    country_code: str,
    exclude_id: int | None = None,
) -> bool:
    query = db.query(Favorite).filter(
        func.lower(Favorite.city) == city.lower(),
        func.lower(Favorite.country_code) == country_code.lower(),
    )
    if exclude_id is not None:
        query = query.filter(Favorite.id != exclude_id)
    return query.first() is not None


def create_history_record(
    db: Session,
    city: str,
    country_code: str,
    requested_days: int,
) -> SearchHistory:
    history_item = SearchHistory(
        city=clean_city(city),
        country_code=clean_country_code(country_code),
        requested_days=requested_days,
    )
    db.add(history_item)
    db.commit()
    db.refresh(history_item)
    return history_item


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
    for city_item in CITY_SUGGESTIONS:
        searchable = (
            f"{city_item['city']} {city_item['country']} {city_item['code']}"
        ).lower()
        if city_item["city"].lower().startswith(query):
            starts_with.append(city_item)
        elif query in searchable:
            contains.append(city_item)
    return {"suggestions": (starts_with + contains)[:limit]}


@app.get("/forecast", tags=["Forecast"])
def forecast(
    city: str = Query(default="Cairo,EG", min_length=2, max_length=80),
    days: int = Query(default=3, ge=1, le=5),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Fetch a forecast and record the successful search in PostgreSQL."""
    try:
        data = get_forecast(city, days)
        if not isinstance(data, dict):
            raise ValueError("Invalid response received from the weather provider.")

        city_data = data.get("city", {})
        forecast_items = data.get("list", [])
        if not isinstance(city_data, dict):
            city_data = {}
        if not isinstance(forecast_items, list) or not forecast_items:
            raise ValueError("No forecast data found for this city.")

        normalized_forecast: list[dict[str, Any]] = []
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
                    "cloudiness": clouds_data.get("all"),
                    "visibility_m": item.get("visibility"),
                }
            )

        if not normalized_forecast:
            raise ValueError("No usable forecast data found for this city.")

        city_name = clean_city(city_data.get("name", city.split(",")[0]))
        country_code = clean_country_code(city_data.get("country", ""))
        create_history_record(db, city_name, country_code, days)

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
    except RapidApiRateLimitError as error:
        raise HTTPException(status_code=429, detail=str(error)) from error
    except WeatherProviderError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error
    except SQLAlchemyError as error:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Forecast loaded, but search history could not be saved.",
        ) from error
    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error)) from error


# ---------------------------------------------------------------------------
# Favorites CRUD
# ---------------------------------------------------------------------------

@app.post(
    "/favorites",
    response_model=FavoriteRead,
    status_code=status.HTTP_201_CREATED,
    tags=["Favorites"],
)
def create_favorite(payload: FavoriteCreate, db: Session = Depends(get_db)) -> Favorite:
    city = clean_city(payload.city)
    country_code = clean_country_code(payload.country_code)
    if favorite_exists(db, city, country_code):
        raise HTTPException(status_code=409, detail="City is already saved as a favorite.")

    favorite = Favorite(city=city, country_code=country_code)
    try:
        db.add(favorite)
        db.commit()
        db.refresh(favorite)
        return favorite
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="City is already saved as a favorite.",
        ) from error


@app.get("/favorites", response_model=list[FavoriteRead], tags=["Favorites"])
def list_favorites(
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> list[Favorite]:
    return (
        db.query(Favorite)
        .order_by(Favorite.created_at.desc(), Favorite.id.desc())
        .limit(limit)
        .all()
    )


@app.get("/favorites/{favorite_id}", response_model=FavoriteRead, tags=["Favorites"])
def get_favorite(favorite_id: int, db: Session = Depends(get_db)) -> Favorite:
    return get_favorite_or_404(db, favorite_id)


@app.put("/favorites/{favorite_id}", response_model=FavoriteRead, tags=["Favorites"])
def update_favorite(
    favorite_id: int,
    payload: FavoriteUpdate,
    db: Session = Depends(get_db),
) -> Favorite:
    favorite = get_favorite_or_404(db, favorite_id)
    updates = payload.model_dump(exclude_unset=True)

    new_city = clean_city(updates.get("city", favorite.city))
    new_country_code = clean_country_code(
        updates.get("country_code", favorite.country_code)
    )
    if favorite_exists(db, new_city, new_country_code, exclude_id=favorite.id):
        raise HTTPException(status_code=409, detail="City is already saved as a favorite.")

    favorite.city = new_city
    favorite.country_code = new_country_code
    try:
        db.commit()
        db.refresh(favorite)
        return favorite
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="City is already saved as a favorite.",
        ) from error


@app.delete(
    "/favorites/{favorite_id}",
    response_model=DeleteResponse,
    tags=["Favorites"],
)
def delete_favorite(favorite_id: int, db: Session = Depends(get_db)) -> DeleteResponse:
    favorite = get_favorite_or_404(db, favorite_id)
    db.delete(favorite)
    db.commit()
    return DeleteResponse(message="Favorite city deleted.")


# ---------------------------------------------------------------------------
# Search history CRUD
# ---------------------------------------------------------------------------

@app.post(
    "/history",
    response_model=SearchHistoryRead,
    status_code=status.HTTP_201_CREATED,
    tags=["History"],
)
def create_history(
    payload: SearchHistoryCreate,
    db: Session = Depends(get_db),
) -> SearchHistory:
    return create_history_record(
        db=db,
        city=payload.city,
        country_code=payload.country_code,
        requested_days=payload.requested_days,
    )


@app.get("/history", response_model=list[SearchHistoryRead], tags=["History"])
def list_history(
    limit: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db),
) -> list[SearchHistory]:
    return (
        db.query(SearchHistory)
        .order_by(SearchHistory.created_at.desc(), SearchHistory.id.desc())
        .limit(limit)
        .all()
    )


@app.get("/history/{history_id}", response_model=SearchHistoryRead, tags=["History"])
def get_history(history_id: int, db: Session = Depends(get_db)) -> SearchHistory:
    return get_history_or_404(db, history_id)


@app.put("/history/{history_id}", response_model=SearchHistoryRead, tags=["History"])
def update_history(
    history_id: int,
    payload: SearchHistoryUpdate,
    db: Session = Depends(get_db),
) -> SearchHistory:
    history_item = get_history_or_404(db, history_id)
    updates = payload.model_dump(exclude_unset=True)
    if "city" in updates:
        history_item.city = clean_city(updates["city"])
    if "country_code" in updates:
        history_item.country_code = clean_country_code(updates["country_code"])
    if "requested_days" in updates:
        history_item.requested_days = updates["requested_days"]
    db.commit()
    db.refresh(history_item)
    return history_item


@app.delete("/history/{history_id}", response_model=DeleteResponse, tags=["History"])
def delete_history(history_id: int, db: Session = Depends(get_db)) -> DeleteResponse:
    history_item = get_history_or_404(db, history_id)
    db.delete(history_item)
    db.commit()
    return DeleteResponse(message="Search history item deleted.")


@app.delete("/history", response_model=DeleteResponse, tags=["History"])
def clear_history(db: Session = Depends(get_db)) -> DeleteResponse:
    deleted_count = db.query(SearchHistory).delete(synchronize_session=False)
    db.commit()
    return DeleteResponse(message=f"Deleted {deleted_count} search history item(s).")
