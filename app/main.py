from fastapi import FastAPI, HTTPException
from app.weather import get_forecast

app = FastAPI(title="Weather Forecasting App")

@app.get("/")
def home():
    return {"message": "Weather Forecasting API is running"}

@app.get("/health")
def health():
    return {"status": "healthy"}
@app.get("/forecast")
def forecast(city: str = "Cairo,EG", days: int = 3):
    try:
        data = get_forecast(city, days)

        return {
            "city": data["city"]["name"],
            "country": data["city"]["country"],
            "forecast_count": data["cnt"],
            "forecast": [
                {
                    "date_time": item["dt_txt"],
                    "temperature_k": item["main"]["temprature"],
                    "feels_like_k": item["main"]["temprature_feels_like"],
                    "humidity": item["main"]["humidity"],
                    "condition": item["weather"][0]["description"],
                    "wind_speed": item["wind"]["speed"],
                    "wind_direction": item["wind"]["direction"],
                    "rain_probability": item["probability_of_precipitation"]
                }
                for item in data["list"]
            ]
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))