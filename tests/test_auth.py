from uuid import uuid4

from app.core.config import Settings
from app.services.auth_service import AuthService


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


def test_brevo_api_delivery_uses_https(monkeypatch):
    captured = {}

    class Response:
        status_code = 201

    def fake_post(url, **kwargs):
        captured["url"] = url
        captured.update(kwargs)
        return Response()

    monkeypatch.setattr("app.services.auth_service.httpx.post", fake_post)
    settings = Settings(
        _env_file=None,
        otp_delivery_mode="brevo_api",
        brevo_api_key="test-brevo-api-key",
        smtp_from_email="verified@example.com",
    )
    AuthService(settings)._send_email("citizen@example.com", "123456")

    assert captured["url"] == "https://api.brevo.com/v3/smtp/email"
    assert captured["headers"]["api-key"] == "test-brevo-api-key"
    assert captured["json"]["sender"]["email"] == "verified@example.com"
    assert captured["json"]["to"] == [{"email": "citizen@example.com"}]
    assert "123456" in captured["json"]["textContent"]
