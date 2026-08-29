def test_health(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "healthy"
    assert payload["ai_mode"] == "demo"
    assert payload["database"] == "sqlite"


def test_curated_schemes_are_available(client):
    response = client.get("/api/v1/schemes")
    assert response.status_code == 200
    schemes = response.json()
    assert len(schemes) >= 8
    assert any(item["slug"] == "pm-kisan" for item in schemes)


def test_scheme_detail_has_official_source(client):
    response = client.get("/api/v1/schemes/pm-kisan")
    assert response.status_code == 200
    item = response.json()
    assert item["short_name"] == "PM-KISAN"
    assert item["official_url"].startswith("https://")
    assert item["application_steps"]
