from typing import Any

import app.weather as weather


class DummyResponse:
    def __init__(
        self,
        payload: dict[str, Any],
        status_code: int = 200,
    ) -> None:
        self._payload = payload
        self.status_code = status_code
        self.headers: dict[str, str] = {}

    def json(self) -> dict[str, Any]:
        return self._payload

    def raise_for_status(self) -> None:
        return None


def test_get_forecast_resolves_city_and_limits_days(monkeypatch):
    calls: list[tuple[str, dict[str, Any]]] = []

    def fake_get(url, headers, params, timeout):
        calls.append((url, params))

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
    monkeypatch.setattr(weather.requests, "get", fake_get)

    weather._forecast_cache.clear()
    weather._coordinate_cache.clear()

    payload = weather.get_forecast("Cairo,EG,EG", days=3)

    assert len(payload["list"]) == 24
    assert payload["cnt"] == 24

    assert calls[0][0].endswith("/city")
    assert calls[0][1]["city"] == "Cairo,EG"

    assert calls[1][0].endswith("/fivedaysforcast")
    assert calls[1][1]["latitude"] == 30.0444
    assert calls[1][1]["longitude"] == 31.2357


def test_forecast_cache_prevents_duplicate_provider_requests(monkeypatch):
    calls: list[str] = []

    def fake_get(url, headers, params, timeout):
        calls.append(url)

        if url.endswith("/city"):
            return DummyResponse(
                {
                    "coord": {
                        "lat": 24.7136,
                        "lon": 46.6753,
                    }
                }
            )

        return DummyResponse(
            {
                "cod": "200",
                "cnt": 40,
                "list": [{"dt": index} for index in range(40)],
                "city": {
                    "name": "Riyadh",
                    "country": "SA",
                },
            }
        )

    monkeypatch.setattr(weather, "RAPIDAPI_KEY", "test-key")
    monkeypatch.setattr(weather.requests, "get", fake_get)

    weather._forecast_cache.clear()
    weather._coordinate_cache.clear()

    weather.get_forecast("Riyadh,SA", days=1)
    weather.get_forecast("Riyadh,SA", days=1)

    assert len(calls) == 2
