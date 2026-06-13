import json
from typing import Any

import app.weather as weather


class FakeRedis:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}

    def get(self, key: str) -> str | None:
        return self.values.get(key)

    def setex(self, key: str, ttl_seconds: int, value: str) -> bool:
        self.values[key] = value
        return True

    def ping(self) -> bool:
        return True


class DummyResponse:
    def __init__(self, payload: dict[str, Any]) -> None:
        self._payload = payload
        self.status_code = 200
        self.headers: dict[str, str] = {}

    def json(self) -> dict[str, Any]:
        return self._payload

    def raise_for_status(self) -> None:
        return None


def test_forecast_uses_redis_after_first_provider_call(monkeypatch):
    fake_redis = FakeRedis()
    calls: list[str] = []

    def fake_get(url, headers, params, timeout):
        calls.append(url)

        if url.endswith("/city"):
            return DummyResponse(
                {
                    "coord": {
                        "lat": 30.0444,
                        "lon": 31.2357,
                    }
                }
            )

        return DummyResponse(
            {
                "cod": "200",
                "cnt": 40,
                "list": [{"dt": index} for index in range(40)],
                "city": {
                    "name": "Cairo",
                    "country": "EG",
                },
            }
        )

    monkeypatch.setattr(weather, "RAPIDAPI_KEY", "test-key")
    monkeypatch.setattr(weather, "_redis_client", fake_redis)
    monkeypatch.setattr(weather.requests, "get", fake_get)

    weather._forecast_cache.clear()
    weather._coordinate_cache.clear()

    first = weather.get_forecast("Cairo,EG,EG", days=3)

    # Clear local dictionaries to prove the second read comes from Redis.
    weather._forecast_cache.clear()
    weather._coordinate_cache.clear()

    second = weather.get_forecast("Cairo,EG", days=3)

    assert len(first["list"]) == 24
    assert second == first
    assert len(calls) == 2


def test_cache_status_reports_redis(monkeypatch):
    monkeypatch.setattr(weather, "_redis_client", FakeRedis())

    status = weather.get_cache_status()

    assert status["backend"] == "redis"
    assert status["redis_connected"] is True
