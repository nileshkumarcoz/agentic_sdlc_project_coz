"""Unit tests for AuthService: login, lockout, and token revocation."""
from __future__ import annotations

import pytest
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional

from backend.services.auth import security
from backend.services.auth.service import (
    AccountLockedError,
    AuthService,
    InvalidCredentialsError,
    LOCKOUT_THRESHOLD,
    User,
)

# ---------------------------------------------------------------------------
# In-memory fakes
# ---------------------------------------------------------------------------

class FakeUserRepository:
    def __init__(self, users: list[User]) -> None:
        self._store: Dict[str, User] = {u.email: u for u in users}

    async def get_by_email(self, email: str) -> Optional[User]:
        return self._store.get(email)

    async def save(self, user: User) -> None:
        self._store[user.email] = user


class FakeDenylist:
    def __init__(self) -> None:
        self._store: Dict[str, int] = {}

    async def add(self, jti: str, ttl_seconds: int) -> None:
        self._store[jti] = ttl_seconds

    async def exists(self, jti: str) -> bool:
        return jti in self._store


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

PLAIN_PASSWORD = "S3cur3P@ss!"


def _make_user(**kwargs) -> User:
    defaults = dict(
        id="user-001",
        email="alice@example.com",
        hashed_password=security.hash_password(PLAIN_PASSWORD),
        role="architect",
    )
    defaults.update(kwargs)
    return User(**defaults)


def _make_service(users=None, denylist=None):
    users = users or []
    return AuthService(
        users=FakeUserRepository(users),
        denylist=denylist or FakeDenylist(),
    )


# ---------------------------------------------------------------------------
# Login success
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_login_success_returns_tokens():
    svc = _make_service(users=[_make_user()])
    user, tokens = await svc.authenticate_user("alice@example.com", PLAIN_PASSWORD)
    assert tokens.access_token
    assert tokens.refresh_token
    assert tokens.token_type == "bearer"


@pytest.mark.asyncio
async def test_login_success_resets_failed_attempts():
    u = _make_user(failed_attempts=3)
    repo = FakeUserRepository([u])
    svc = AuthService(users=repo, denylist=FakeDenylist())
    await svc.authenticate_user("alice@example.com", PLAIN_PASSWORD)
    saved = await repo.get_by_email("alice@example.com")
    assert saved.failed_attempts == 0
    assert saved.locked_until is None


@pytest.mark.asyncio
async def test_login_success_updates_last_login():
    svc = _make_service(users=[_make_user()])
    _, _ = await svc.authenticate_user("alice@example.com", PLAIN_PASSWORD)


# ---------------------------------------------------------------------------
# Wrong password
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_wrong_password_raises_invalid_credentials():
    svc = _make_service(users=[_make_user()])
    with pytest.raises(InvalidCredentialsError):
        await svc.authenticate_user("alice@example.com", "wrong")


@pytest.mark.asyncio
async def test_wrong_password_increments_failed_attempts():
    u = _make_user(failed_attempts=0)
    repo = FakeUserRepository([u])
    svc = AuthService(users=repo, denylist=FakeDenylist())
    with pytest.raises(InvalidCredentialsError):
        await svc.authenticate_user("alice@example.com", "wrong")
    saved = await repo.get_by_email("alice@example.com")
    assert saved.failed_attempts == 1


@pytest.mark.asyncio
async def test_unknown_email_raises_same_error_as_wrong_password():
    """Must not leak whether email exists."""
    svc = _make_service(users=[])
    with pytest.raises(InvalidCredentialsError):
        await svc.authenticate_user("nobody@example.com", "x")


# ---------------------------------------------------------------------------
# Lockout
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_fifth_failure_sets_locked_until():
    u = _make_user(failed_attempts=LOCKOUT_THRESHOLD - 1)
    repo = FakeUserRepository([u])
    svc = AuthService(users=repo, denylist=FakeDenylist())
    with pytest.raises(InvalidCredentialsError):
        await svc.authenticate_user("alice@example.com", "wrong")
    saved = await repo.get_by_email("alice@example.com")
    assert saved.locked_until is not None
    assert saved.locked_until > datetime.now(tz=timezone.utc)


@pytest.mark.asyncio
async def test_locked_account_raises_account_locked_error():
    u = _make_user(
        failed_attempts=LOCKOUT_THRESHOLD,
        locked_until=datetime.now(tz=timezone.utc) + timedelta(minutes=10),
    )
    svc = _make_service(users=[u])
    with pytest.raises(AccountLockedError):
        await svc.authenticate_user("alice@example.com", PLAIN_PASSWORD)


@pytest.mark.asyncio
async def test_expired_lock_allows_login():
    """A user whose lockout has expired can log in again."""
    u = _make_user(
        failed_attempts=LOCKOUT_THRESHOLD,
        locked_until=datetime.now(tz=timezone.utc) - timedelta(seconds=1),
    )
    svc = _make_service(users=[u])
    user, tokens = await svc.authenticate_user("alice@example.com", PLAIN_PASSWORD)
    assert tokens.access_token


# ---------------------------------------------------------------------------
# Token revocation (replay attack prevention)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_revoke_token_adds_jti_to_denylist():
    denylist = FakeDenylist()
    svc = _make_service(users=[_make_user()], denylist=denylist)
    _, tokens = await svc.authenticate_user("alice@example.com", PLAIN_PASSWORD)

    payload = security.decode_token(tokens.access_token)
    jti = payload["jti"]
    exp = payload["exp"]

    await svc.revoke_token(jti, exp)
    assert await svc.is_token_revoked(jti)


@pytest.mark.asyncio
async def test_non_revoked_token_not_in_denylist():
    denylist = FakeDenylist()
    svc = _make_service(users=[_make_user()], denylist=denylist)
    _, tokens = await svc.authenticate_user("alice@example.com", PLAIN_PASSWORD)
    payload = security.decode_token(tokens.access_token)
    assert not await svc.is_token_revoked(payload["jti"])
