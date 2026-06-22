"""Password hashing and JWT utilities for the Auth Service."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

# ---------------------------------------------------------------------------
# Configuration (replace with env-var / secrets-manager values in production)
# ---------------------------------------------------------------------------
SECRET_KEY: str = "CHANGE_ME_IN_PRODUCTION"  # placeholder — load from env
ALGORITHM: str = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
REFRESH_TOKEN_EXPIRE_DAYS: int = 7

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=12)


# ---------------------------------------------------------------------------
# Password helpers
# ---------------------------------------------------------------------------

def hash_password(plain: str) -> str:
    """Return a bcrypt hash (cost 12) of *plain*."""
    return _pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """Return True if *plain* matches *hashed*."""
    return _pwd_context.verify(plain, hashed)


# ---------------------------------------------------------------------------
# JWT helpers
# ---------------------------------------------------------------------------

def _build_token(data: dict[str, Any], expires_delta: timedelta) -> tuple[str, str]:
    """Sign a JWT and return (encoded_token, jti)."""
    jti = str(uuid.uuid4())
    now = datetime.now(tz=timezone.utc)
    payload = {
        **data,
        "jti": jti,
        "iat": now,
        "exp": now + expires_delta,
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM), jti


def create_access_token(user_id: str, role: str) -> tuple[str, str]:
    """Return (access_token, jti) valid for ACCESS_TOKEN_EXPIRE_MINUTES."""
    return _build_token(
        {"sub": user_id, "role": role, "type": "access"},
        timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    )


def create_refresh_token(user_id: str) -> tuple[str, str]:
    """Return (refresh_token, jti) valid for REFRESH_TOKEN_EXPIRE_DAYS."""
    return _build_token(
        {"sub": user_id, "type": "refresh"},
        timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
    )


def decode_token(token: str) -> dict[str, Any]:
    """Decode and verify a JWT; raises JWTError on failure."""
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])


__all__ = [
    "hash_password",
    "verify_password",
    "create_access_token",
    "create_refresh_token",
    "decode_token",
    "ACCESS_TOKEN_EXPIRE_MINUTES",
    "REFRESH_TOKEN_EXPIRE_DAYS",
]
