import os
import requests

RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")
RAPIDAPI_HOST = os.getenv("RAPIDAPI_HOST")

def get_forecast(city: str, days: int = 3):

    url = f"https://{RAPIDAPI_HOST}/api/weather/forecast"

    headers = {
        "x-rapidapi-key": RAPIDAPI_KEY,
        "x-rapidapi-host": RAPIDAPI_HOST,
        "Accept": "application/json"
    }

    params = {
        "place": f"{city},EG",
        "cnt": days,
        "units": "standard",
        "type": "three_hour",
        "mode": "json",
        "lang": "en"
    }

    response = requests.get(
        url,
        headers=headers,
        params=params,
        timeout=10
    )

    response.raise_for_status()

    return response.json()