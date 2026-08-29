from uuid import uuid4


def test_passwordless_registration_login_and_logout(client):
    email = f"test-{uuid4().hex}@example.com"
    requested = client.post(
        "/api/v1/auth/request-otp",
        json={"email": email, "purpose": "register"},
    )
    assert requested.status_code == 200
    challenge = requested.json()
    assert len(challenge["development_code"]) == 6

    verified = client.post(
        "/api/v1/auth/verify-otp",
        json={"challenge_id": challenge["challenge_id"], "code": challenge["development_code"]},
    )
    assert verified.status_code == 200
    session = verified.json()
    assert session["email"] == email
    assert session["token_type"] == "bearer"
    assert session["access_token"]

    logout = client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {session['access_token']}"},
    )
    assert logout.status_code == 204


def test_wrong_otp_has_safe_friendly_error(client):
    requested = client.post(
        "/api/v1/auth/request-otp",
        json={"email": f"test-{uuid4().hex}@example.com", "purpose": "register"},
    ).json()
    response = client.post(
        "/api/v1/auth/verify-otp",
        json={"challenge_id": requested["challenge_id"], "code": "999999"},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "That code is incorrect"
