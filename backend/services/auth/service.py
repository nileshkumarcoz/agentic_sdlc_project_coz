"""Auth business logic: authenticate, issue tokens, revoke tokens."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Optional, Protocol

from . import security

LOCKOUT_THRESHOLD: int = 5
LOCKOUT_MINUTES: int = 15


# ---------------------------------------------------------------------------
# Minimal user representation (framework-agnostic)
# ---------------------------------------------------------------------------

@dataclass
class User:
    id: str
    email: str
    hashed_password: str
    role: str = "architect"
    is_active: bool = True
    failed_attempts: int = 0
    locked_until: Optional[datetime] = None
    last_login_at: Optional[datetime] = None


# ---------------------------------------------------------------------------
# Port interfaces (implement these against real DB/Redis in integration layer)
# ---------------------------------------------------------------------------

class UserRepository(Protocol):
    async def get_by_email(self, email: str) -> Optional[User]: ...
    async def save(self, user: User) -> None: ...


class TokenDenylist(Protocol):
    async def add(self, jti: str, ttl_seconds: int) -> None: ...
    async def exists(self, jti: str) -> bool: ...


# ---------------------------------------------------------------------------
# Token payload
# ---------------------------------------------------------------------------

@dataclass
class TokenPair:
    access_token: str
    refresh_token: str
    access_jti: str
    refresh_jti: str
    token_type: str = "bearer"


# ---------------------------------------------------------------------------
# Auth service
# ---------------------------------------------------------------------------

class AuthService:
    def __init__(self, users: UserRepository, denylist: TokenDenylist) -> None:
        self._users = users
        self._denylist = denylist

    async def authenticate_user(
        self, email: str, password: str
    ) -> tuple[User, TokenPair]:
        """Validate credentials and return (user, tokens).

        Raises:
            AccountLockedError: account currently locked.
            InvalidCredentialsError: wrong email or password.
        """
        user = await self._users.get_by_email(email)

        # --- Lockout check (must happen before password verify) ---
        if user is not None and _is_locked(user):
            raise AccountLockedError(
                f"Account locked until {user.locked_until.isoformat()}"
            )

        # --- Password verification ---
        password_ok = (
            user is not None
            and security.verify_password(password, user.hashed_password)
        )

        if not password_ok:
            if user is not None:
                user.failed_attempts += 1
                if user.failed_attempts >= LOCKOUT_THRESHOLD:
                    user.locked_until = datetime.now(tz=timezone.utc) + timedelta(
                        minutes=LOCKOUT_MINUTES
                    )
                await self._users.save(user)
            raise InvalidCredentialsError("Invalid credentials.")

        # --- Success ---
        user.failed_attempts = 0
        user.locked_until = None
        user.last_login_at = datetime.now(tz=timezone.utc)
        await self._users.save(user)

        tokens = _issue_tokens(user)
        return user, tokens

    async def revoke_token(self, jti: str, exp_timestamp: int) -> None:
        """Add a JTI to the denylist with a TTL matching the token's remaining life."""
        remaining = exp_timestamp - int(datetime.now(tz=timezone.utc).timestamp())
        if remaining > 0:
            await self._denylist.add(jti, remaining)

    async def is_token_revoked(self, jti: str) -> bool:
        return await self._denylist.exists(jti)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _is_locked(user: User) -> bool:
    if user.locked_until is None:
        return False
    now = datetime.now(tz=timezone.utc)
    locked_until = user.locked_until
    if locked_until.tzinfo is None:
        locked_until = locked_until.replace(tzinfo=timezone.utc)
    return locked_until > now


def _issue_tokens(user: User) -> TokenPair:
    access_token, access_jti = security.create_access_token(user.id, user.role)
    refresh_token, refresh_jti = security.create_refresh_token(user.id)
    return TokenPair(
        access_token=access_token,
        refresh_token=refresh_token,
        access_jti=access_jti,
        refresh_jti=refresh_jti,
    )


# ---------------------------------------------------------------------------
# Domain exceptions
# ---------------------------------------------------------------------------

class AccountLockedError(Exception): ...
class InvalidCredentialsError(Exception): ...


__all__ = [
    "AuthService",
    "User",
    "TokenPair",
    "AccountLockedError",
    "InvalidCredentialsError",
    "LOCKOUT_THRESHOLD",
    "LOCKOUT_MINUTES",
]
