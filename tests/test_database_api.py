from app import main as main_module


def fake_forecast(city: str, days: int):
    return {
        "city": {"name": city.split(",")[0], "country": "SA"},
        "cnt": 1,
        "list": [
            {
                "dt": 1781186400,
                "dt_txt": "2026-06-11 18:00:00",
                "main": {
                    "temp": 308.15,
                    "feels_like": 309.15,
                    "temp_min": 307.15,
                    "temp_max": 309.15,
                    "humidity": 35,
                    "pressure": 1006,
                },
                "weather": [
                    {"main": "Clear", "description": "clear sky", "icon": "01d"}
                ],
                "wind": {"speed": 3.5, "deg": 210},
                "clouds": {"all": 0},
                "visibility": 10000,
                "pop": 0.1,
            }
        ],
    }


def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "service": "neutweather-api"}


def test_favorites_crud(client):
    create_response = client.post(
        "/favorites",
        json={"city": "Riyadh", "country_code": "sa"},
    )
    assert create_response.status_code == 201
    favorite = create_response.json()
    assert favorite["city"] == "Riyadh"
    assert favorite["country_code"] == "SA"

    list_response = client.get("/favorites")
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1

    get_response = client.get(f"/favorites/{favorite['id']}")
    assert get_response.status_code == 200
    assert get_response.json()["city"] == "Riyadh"

    update_response = client.put(
        f"/favorites/{favorite['id']}",
        json={"city": "Dammam", "country_code": "sa"},
    )
    assert update_response.status_code == 200
    assert update_response.json()["city"] == "Dammam"

    delete_response = client.delete(f"/favorites/{favorite['id']}")
    assert delete_response.status_code == 200
    assert delete_response.json()["message"] == "Favorite city deleted."
    assert client.get("/favorites").json() == []


def test_duplicate_favorite_is_rejected_case_insensitively(client):
    first_response = client.post(
        "/favorites",
        json={"city": "Riyadh", "country_code": "SA"},
    )
    assert first_response.status_code == 201

    duplicate_response = client.post(
        "/favorites",
        json={"city": "riyadh", "country_code": "sa"},
    )
    assert duplicate_response.status_code == 409


def test_search_history_crud(client):
    create_response = client.post(
        "/history",
        json={"city": "Cairo", "country_code": "eg", "requested_days": 3},
    )
    assert create_response.status_code == 201
    history_item = create_response.json()
    assert history_item["country_code"] == "EG"

    list_response = client.get("/history")
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1

    update_response = client.put(
        f"/history/{history_item['id']}",
        json={"requested_days": 5},
    )
    assert update_response.status_code == 200
    assert update_response.json()["requested_days"] == 5

    get_response = client.get(f"/history/{history_item['id']}")
    assert get_response.status_code == 200
    assert get_response.json()["city"] == "Cairo"

    delete_response = client.delete(f"/history/{history_item['id']}")
    assert delete_response.status_code == 200
    assert client.get("/history").json() == []


def test_forecast_saves_search_history(client, monkeypatch):
    monkeypatch.setattr(main_module, "get_forecast", fake_forecast)

    forecast_response = client.get("/forecast?city=Riyadh,SA&days=4")
    assert forecast_response.status_code == 200
    forecast = forecast_response.json()
    assert forecast["city"] == "Riyadh"
    assert forecast["country"] == "SA"

    history_response = client.get("/history")
    assert history_response.status_code == 200
    history = history_response.json()
    assert len(history) == 1
    assert history[0]["city"] == "Riyadh"
    assert history[0]["country_code"] == "SA"
    assert history[0]["requested_days"] == 4


def test_clear_history(client):
    client.post(
        "/history",
        json={"city": "Cairo", "country_code": "EG", "requested_days": 3},
    )
    client.post(
        "/history",
        json={"city": "Riyadh", "country_code": "SA", "requested_days": 2},
    )

    clear_response = client.delete("/history")
    assert clear_response.status_code == 200
    assert clear_response.json()["message"] == "Deleted 2 search history item(s)."
    assert client.get("/history").json() == []
