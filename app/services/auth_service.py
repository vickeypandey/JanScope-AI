from __future__ import annotations

import hashlib
import hmac
import re
import secrets
import smtplib
import uuid
from datetime import datetime, timedelta
from email.message import EmailMessage

import httpx

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.db.models import OtpChallenge, User, UserSession


class AuthService:
    EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")

    def __init__(self, settings: Settings):
        self.settings = settings

    @staticmethod
    def _now() -> datetime:
        return datetime.utcnow()

    @staticmethod
    def _token_hash(token: str) -> str:
        return hashlib.sha256(token.encode()).hexdigest()

    def _otp_hash(self, challenge_id: str, email: str, code: str) -> str:
        value = f"{challenge_id}:{email}:{code}".encode()
        return hmac.new(self.settings.otp_secret.encode(), value, hashlib.sha256).hexdigest()

    def normalize_email(self, email: str) -> str:
        normalized = email.strip().casefold()
        if not self.EMAIL_PATTERN.fullmatch(normalized):
            raise ValueError("Enter a valid email address")
        return normalized

    def request_otp(self, db: Session, email: str, purpose: str) -> tuple[OtpChallenge, str | None]:
        normalized = self.normalize_email(email)
        challenge_id = str(uuid.uuid4())
        code = f"{secrets.randbelow(1_000_000):06d}"
        challenge = OtpChallenge(
            id=challenge_id,
            email=normalized,
            purpose=purpose,
            code_hash=self._otp_hash(challenge_id, normalized, code),
            expires_at=self._now() + timedelta(minutes=self.settings.otp_expiry_minutes),
        )
        db.add(challenge)
        db.commit()
        if self.settings.otp_delivery_mode == "development" and not self.settings.is_production:
            return challenge, code
        self._send_email(normalized, code)
        return challenge, None

    def _send_email(self, recipient: str, code: str) -> None:
        if self.settings.otp_delivery_mode == "brevo_api":
            self._send_brevo_api(recipient, code)
            return
        if self.settings.otp_delivery_mode != "smtp":
            raise RuntimeError("Email delivery is not configured")
        message = EmailMessage()
        message["Subject"] = "Your JanScope verification code"
        message["From"] = self.settings.smtp_from_email
        message["To"] = recipient
        message.set_content(
            f"Your JanScope verification code is {code}. "
            f"It expires in {self.settings.otp_expiry_minutes} minutes. "
            "If you did not request this code, you can ignore this email."
        )
        with smtplib.SMTP(self.settings.smtp_host, self.settings.smtp_port, timeout=15) as server:
            if self.settings.smtp_use_tls:
                server.starttls()
            server.login(self.settings.smtp_username, self.settings.smtp_password)
            server.send_message(message)

    def _send_brevo_api(self, recipient: str, code: str) -> None:
        response = httpx.post(
            "https://api.brevo.com/v3/smtp/email",
            headers={
                "accept": "application/json",
                "api-key": self.settings.brevo_api_key,
                "content-type": "application/json",
            },
            json={
                "sender": {"name": "JanScope AI", "email": self.settings.smtp_from_email},
                "to": [{"email": recipient}],
                "subject": "Your JanScope verification code",
                "textContent": (
                    f"Your JanScope verification code is {code}. "
                    f"It expires in {self.settings.otp_expiry_minutes} minutes. "
                    "If you did not request this code, you can ignore this email."
                ),
            },
            timeout=15,
        )
        if response.status_code != 201:
            raise RuntimeError(f"Brevo email delivery failed with status {response.status_code}")

    def verify(self, db: Session, challenge_id: str, code: str) -> tuple[str, User, int]:
        challenge = db.get(OtpChallenge, challenge_id)
        if not challenge or challenge.consumed or challenge.expires_at < self._now():
            raise ValueError("The code has expired. Request a new one")
        if challenge.attempts >= self.settings.otp_max_attempts:
            raise ValueError("Too many incorrect attempts. Request a new code")
        challenge.attempts += 1
        expected = self._otp_hash(challenge.id, challenge.email, code)
        if not hmac.compare_digest(expected, challenge.code_hash):
            db.commit()
            raise ValueError("That code is incorrect")
        user = db.scalar(select(User).where(User.email == challenge.email))
        if challenge.purpose == "login" and user is None:
            challenge.consumed = True
            db.commit()
            raise ValueError("No account was found for this email. Choose Create account")
        if user is None:
            user = User(id=str(uuid.uuid4()), email=challenge.email)
            db.add(user)
        user.last_login_at = self._now()
        challenge.consumed = True
        token = secrets.token_urlsafe(32)
        seconds = self.settings.auth_session_days * 86400
        db.add(
            UserSession(
                id=str(uuid.uuid4()),
                user_id=user.id,
                token_hash=self._token_hash(token),
                expires_at=self._now() + timedelta(seconds=seconds),
            )
        )
        db.commit()
        return token, user, seconds

    def user_for_token(self, db: Session, token: str | None) -> User | None:
        if not token:
            return None
        session = db.scalar(
            select(UserSession).where(
                UserSession.token_hash == self._token_hash(token),
                UserSession.revoked.is_(False),
            )
        )
        if not session or session.expires_at < self._now():
            return None
        return db.get(User, session.user_id)

    def revoke(self, db: Session, token: str) -> None:
        session = db.scalar(select(UserSession).where(UserSession.token_hash == self._token_hash(token)))
        if session:
            session.revoked = True
            db.commit()
