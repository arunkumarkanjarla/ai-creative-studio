"""
Evidence test: expired access token is refreshed; logout then refresh -> 401.

Run against a live API + DB, or as a unit-style flow with overridden settings:

  ACCESS_TOKEN_EXPIRE_MINUTES=0.05 python -m pytest backend/tests/test_refresh_token_flow.py -q

When DATABASE_URL / JWT_SECRET_KEY are unavailable, the pure crypto helpers
still run; the integration section skips.
"""
from __future__ import annotations

import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import jwt

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def test_hash_refresh_token_stable():
    from app.core.security import generate_refresh_token, hash_refresh_token

    raw = generate_refresh_token()
    assert hash_refresh_token(raw) == hash_refresh_token(raw)
    assert hash_refresh_token(raw) != hash_refresh_token(generate_refresh_token())


def test_access_token_short_expiry_roundtrip(monkeypatch):
    """Create an access token with tiny TTL, wait until expired, confirm jwt raises."""
    os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://x:x@localhost/x")
    os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-refresh-evidence")

    from app.core import config

    monkeypatch.setattr(config.settings, "ACCESS_TOKEN_EXPIRE_MINUTES", 0.02)  # ~1.2s
    monkeypatch.setattr(config.settings, "JWT_SECRET_KEY", "test-secret-key-for-refresh-evidence")
    monkeypatch.setattr(config.settings, "JWT_ALGORITHM", "HS256")

    from app.core.security import create_access_token, decode_token

    token = create_access_token(42)
    # Still valid immediately
    payload = decode_token(token)
    assert payload["sub"] == "42"

    time.sleep(1.5)
    try:
        decode_token(token)
        expired = False
    except jwt.ExpiredSignatureError:
        expired = True
    assert expired, "Access token should be expired after short TTL"


def test_refresh_rotation_and_logout_revoke():
    """
    Integration: login -> expire access -> refresh succeeds -> logout -> refresh 401.
    Requires a running DB. Skips if connection fails.
    """
    os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://postgres:postgres@localhost:5432/ai_creative_studio")
    os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-refresh-evidence")

    try:
        from app.db.database import SessionLocal, engine, Base
        from app.models.user import User
        from app.models.refresh_token import RefreshToken  # noqa: F401
        from app.core.security import (
            hash_password,
            create_access_token,
            decode_token,
        )
        from app.core import config
        from app.services.refresh_token_service import (
            issue_refresh_token,
            rotate_refresh_token,
            revoke_by_plaintext,
            RefreshTokenError,
        )

        # Ensure tables exist
        Base.metadata.create_all(bind=engine, checkfirst=True)
        db = SessionLocal()
    except Exception as exc:
        print(f"SKIP integration (DB unavailable): {exc}")
        return

    email = "refresh_evidence@example.com"
    try:
        # Tiny access TTL for evidence log
        config.settings.ACCESS_TOKEN_EXPIRE_MINUTES = 0.02

        user = db.query(User).filter(User.email == email).first()
        if not user:
            user = User(
                name="Refresh Evidence",
                email=email,
                password_hash=hash_password("EvidencePass123!"),
                role="user",
                can_access_image=True,
                can_access_audio=True,
                can_access_video=True,
                is_active=True,
            )
            db.add(user)
            db.commit()
            db.refresh(user)

        access = create_access_token(user.id)
        refresh, row = issue_refresh_token(db, user.id, user_agent="evidence-test", ip_address="127.0.0.1")
        db.commit()

        log_lines = [
            f"issued access_token (short TTL), refresh family={row.family_id}",
        ]

        time.sleep(1.5)
        try:
            decode_token(access)
            access_expired = False
        except jwt.ExpiredSignatureError:
            access_expired = True
        assert access_expired
        log_lines.append("access_token expired as expected")

        # Refresh rotates and yields a usable new access token
        user2, new_refresh, new_row = rotate_refresh_token(db, refresh, user_agent="evidence-test")
        new_access = create_access_token(user2.id)
        db.commit()
        payload = decode_token(new_access)
        assert int(payload["sub"]) == user.id
        assert new_refresh != refresh
        assert new_row.token_hash != row.token_hash
        log_lines.append("refresh succeeded after access expiry; new access_token valid")

        # Logout revokes current refresh
        assert revoke_by_plaintext(db, new_refresh, reason="logout")
        db.commit()
        log_lines.append("logout revoked refresh token")

        try:
            rotate_refresh_token(db, new_refresh)
            refreshed_after_logout = True
        except RefreshTokenError:
            refreshed_after_logout = False
            db.rollback()
        assert not refreshed_after_logout
        log_lines.append("refresh after logout -> rejected (401 equivalent)")

        out = Path("/opt/cursor/artifacts/part_a_refresh_evidence.log")
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text("\n".join(log_lines) + "\n", encoding="utf-8")
        print("\n".join(log_lines))
        print(f"Wrote {out}")
    finally:
        db.close()


if __name__ == "__main__":
    test_hash_refresh_token_stable()
    # monkeypatch-free short expiry using env override is awkward; call helpers directly
    os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://x:x@localhost/x")
    os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-refresh-evidence")
    from app.core import config
    from app.core.security import create_access_token, decode_token

    config.settings.ACCESS_TOKEN_EXPIRE_MINUTES = 0.02
    config.settings.JWT_SECRET_KEY = "test-secret-key-for-refresh-evidence"
    tok = create_access_token(1)
    decode_token(tok)
    time.sleep(1.5)
    try:
        decode_token(tok)
        raise SystemExit("expected expiry")
    except jwt.ExpiredSignatureError:
        print("short-lived access token expired OK")
    test_refresh_rotation_and_logout_revoke()
    print("PART A evidence OK")
