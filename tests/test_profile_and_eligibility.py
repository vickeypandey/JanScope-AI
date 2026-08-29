def test_hinglish_profile_extraction(client):
    response = client.post(
        "/api/v1/profile/extract",
        json={"message": "Mere pita ji 65 saal ke farmer hain aur Bihar se hain. Income 150000 hai."},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["profile"]["age"] == 65
    assert payload["profile"]["state"] == "Bihar"
    assert payload["profile"]["occupation"] == "farmer"
    assert payload["profile"]["annual_income"] == 150000
    assert payload["language"] == "hi-en"


def test_pm_sym_age_rule_is_deterministic(client):
    response = client.post(
        "/api/v1/eligibility/check",
        json={
            "scheme_slug": "pm-sym",
            "profile": {
                "age": 65,
                "annual_income": 150000,
                "state": "Bihar",
                "occupation": "farmer",
            },
        },
    )
    assert response.status_code == 200
    result = response.json()["results"][0]
    assert result["status"] == "not_eligible"
    assert any("Maximum entry age" in item for item in result["failed_rules"])
    assert any("Income requirement" in item for item in result["matched_rules"])


def test_missing_information_is_reported_not_guessed(client):
    response = client.post(
        "/api/v1/eligibility/check",
        json={"scheme_slug": "pm-sym", "profile": {"state": "Bihar"}},
    )
    result = response.json()["results"][0]
    assert result["status"] == "potentially_eligible"
    assert {"age", "annual_income", "occupation"}.issubset(set(result["missing_information"]))


def test_bihar_scheme_rejects_other_state(client):
    response = client.post(
        "/api/v1/eligibility/check",
        json={
            "scheme_slug": "bihar-fasal-sahayata",
            "profile": {"state": "Jharkhand", "occupation": "farmer"},
        },
    )
    result = response.json()["results"][0]
    assert result["status"] == "not_eligible"
    assert any("Bihar" in item for item in result["failed_rules"])
