"""Tests for oauth.py — unit + integration (mocked HTTP + DB)."""
import time
import pytest
from unittest.mock import MagicMock, patch

import oauth


# ---------------------------------------------------------------------------
# Helpers / Fixtures
# ---------------------------------------------------------------------------

def _make_db(
    oauth_row=None,
    user=None,
    conflict_row=None,
):
    """Return a mock DB object with configurable query results."""
    db = MagicMock()
    db.find_oauth_account.return_value = oauth_row
    db.find_user_by_email.return_value = user
    db.find_oauth_account_by_user.return_value = conflict_row
    db.find_user_by_id.return_value = user
    db.create_user.return_value = {"id": 99, "email": "new@example.com", "name": "New"}
    db.get_oauth_account.return_value = oauth_row
    return db


TOKENS = {
    "access_token": "acc_token",
    "refresh_token": "ref_token",
    "expires_in": 3600,
}
USERINFO = {"sub": "google-sub-123", "email": "user@example.com", "name": "Test User"}


# ---------------------------------------------------------------------------
# build_auth_url
# ---------------------------------------------------------------------------

def test_build_auth_url_stores_state_in_session():
    session = {}
    url = oauth.build_auth_url(session)
    assert "oauth_state" in session
    assert session["oauth_state"] in url
    assert "access_type=offline" in url
    assert "openid" in url


# ---------------------------------------------------------------------------
# CSRF / state validation
# ---------------------------------------------------------------------------

def test_callback_raises_on_state_mismatch():
    session = {"oauth_state": "correct-state"}
    with pytest.raises(ValueError, match="state"):
        oauth.handle_callback("code", "wrong-state", session, MagicMock())


def test_callback_raises_on_missing_state():
    session = {}  # no state stored
    with pytest.raises(ValueError, match="state"):
        oauth.handle_callback("code", "any-state", session, MagicMock())


def test_state_consumed_on_first_use():
    """Second call with same state must fail (state popped from session)."""
    session = {"oauth_state": "one-time-state"}
    # First call will fail at token exchange (no HTTP mock), state is popped
    with patch.object(oauth, "_exchange_code", side_effect=RuntimeError("stop")):
        with pytest.raises(RuntimeError):
            oauth.handle_callback("code", "one-time-state", session, MagicMock())
    assert "oauth_state" not in session  # consumed


# ---------------------------------------------------------------------------
# Account resolution — Branch 1: already linked
# ---------------------------------------------------------------------------

def test_resolve_already_linked_updates_tokens():
    existing_user = {"id": 1, "email": "user@example.com"}
    oauth_row = {"id": 10, "user_id": 1, "provider_account_id": "google-sub-123"}
    db = _make_db(oauth_row=oauth_row, user=existing_user)

    user = oauth._resolve_account(db, "google-sub-123", "user@example.com", "Test", TOKENS)

    assert user["id"] == 1
    db.update_oauth_tokens.assert_called_once()
    db.insert_oauth_account.assert_not_called()
    db.create_user.assert_not_called()


# ---------------------------------------------------------------------------
# Account resolution — Branch 2: link to existing email user
# ---------------------------------------------------------------------------

def test_resolve_links_existing_email_user():
    existing_user = {"id": 2, "email": "user@example.com"}
    db = _make_db(oauth_row=None, user=existing_user, conflict_row=None)

    user = oauth._resolve_account(db, "google-sub-456", "user@example.com", "Test", TOKENS)

    assert user["id"] == 2
    db.insert_oauth_account.assert_called_once()
    db.create_user.assert_not_called()


def test_resolve_rejects_different_sub_for_same_email():
    existing_user = {"id": 2, "email": "user@example.com"}
    conflict_row = {"id": 11, "user_id": 2, "provider_account_id": "different-sub"}
    db = _make_db(oauth_row=None, user=existing_user, conflict_row=conflict_row)

    with pytest.raises(ValueError, match="different Google account"):
        oauth._resolve_account(db, "new-sub-999", "user@example.com", "Test", TOKENS)


# ---------------------------------------------------------------------------
# Account resolution — Branch 3: new user
# ---------------------------------------------------------------------------

def test_resolve_creates_new_user():
    db = _make_db(oauth_row=None, user=None)

    user = oauth._resolve_account(db, "brand-new-sub", "new@example.com", "New", TOKENS)

    assert user["id"] == 99
    db.create_user.assert_called_once_with(email="new@example.com", name="New")
    db.insert_oauth_account.assert_called_once()


# ---------------------------------------------------------------------------
# Token refresh
# ---------------------------------------------------------------------------

def test_refresh_returns_existing_token_if_not_expired():
    future_expiry = int(time.time()) + 600
    row = {"access_token": "valid_token", "refresh_token": "ref", "token_expiry": future_expiry}
    db = _make_db(oauth_row=row)
    db.get_oauth_account.return_value = row

    result = oauth.refresh_access_token(db, 1)
    assert result == "valid_token"


def test_refresh_calls_google_when_token_expired():
    past_expiry = int(time.time()) - 100
    row = {"id": 1, "access_token": "old", "refresh_token": "ref", "token_expiry": past_expiry}
    db = MagicMock()
    db.get_oauth_account.return_value = row

    new_tokens = {"access_token": "new_access", "expires_in": 3600}
    with patch("oauth.requests.post") as mock_post:
        mock_post.return_value.ok = True
        mock_post.return_value.raise_for_status = MagicMock()
        mock_post.return_value.json.return_value = new_tokens
        result = oauth.refresh_access_token(db, 1)

    assert result == "new_access"
    db.update_oauth_tokens.assert_called_once()


def test_refresh_returns_none_when_no_refresh_token():
    row = {"id": 1, "access_token": "x", "refresh_token": None, "token_expiry": 0}
    db = MagicMock()
    db.get_oauth_account.return_value = row
    result = oauth.refresh_access_token(db, 1)
    assert result is None


# ---------------------------------------------------------------------------
# Token revocation
# ---------------------------------------------------------------------------

def test_revoke_calls_google_and_clears_tokens():
    row = {"id": 1, "refresh_token": "ref_tok", "access_token": "acc_tok"}
    db = MagicMock()
    db.get_oauth_account.return_value = row

    with patch("oauth.requests.post") as mock_post:
        mock_post.return_value.ok = True
        oauth.revoke_token(db, 1)

    mock_post.assert_called_once()
    assert "ref_tok" in str(mock_post.call_args)
    db.clear_oauth_tokens.assert_called_once_with(1)


def test_revoke_proceeds_even_if_google_returns_error():
    """Fail-open: local cleanup must happen regardless of Google response."""
    row = {"id": 1, "refresh_token": "ref_tok", "access_token": None}
    db = MagicMock()
    db.get_oauth_account.return_value = row

    with patch("oauth.requests.post") as mock_post:
        mock_post.return_value.ok = False
        mock_post.return_value.status_code = 503
        oauth.revoke_token(db, 1)

    db.clear_oauth_tokens.assert_called_once_with(1)


def test_revoke_proceeds_on_network_error():
    row = {"id": 1, "refresh_token": "ref_tok", "access_token": None}
    db = MagicMock()
    db.get_oauth_account.return_value = row

    with patch("oauth.requests.post", side_effect=ConnectionError("timeout")):
        oauth.revoke_token(db, 1)  # must not raise

    db.clear_oauth_tokens.assert_called_once_with(1)
