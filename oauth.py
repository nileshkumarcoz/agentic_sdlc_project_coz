"""Google OAuth 2.0 integration for the customer portal.

Configuration (environment variables):
    GOOGLE_CLIENT_ID      - OAuth 2.0 client ID
    GOOGLE_CLIENT_SECRET  - OAuth 2.0 client secret
    GOOGLE_REDIRECT_URI   - Registered callback URI
    SESSION_SECRET        - Secret key for session signing
"""
import os
import secrets
import time
import logging
from typing import Optional, Dict, Any
from urllib.parse import urlencode

import requests

log = logging.getLogger(__name__)

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_REVOKE_URL = "https://oauth2.googleapis.com/revoke"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"

CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")
CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")
REDIRECT_URI = os.environ.get("GOOGLE_REDIRECT_URI", "")


# ---------------------------------------------------------------------------
# Authorization URL
# ---------------------------------------------------------------------------

def build_auth_url(session: dict) -> str:
    """Build the Google OAuth authorization URL and store state in session."""
    state = secrets.token_urlsafe(32)
    session["oauth_state"] = state
    params = {
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
    }
    return f"{GOOGLE_AUTH_URL}?{urlencode(params)}"


# ---------------------------------------------------------------------------
# Callback handler
# ---------------------------------------------------------------------------

def handle_callback(
    code: str,
    state: str,
    session: dict,
    db,  # duck-typed DB connection/session
) -> Dict[str, Any]:
    """Process the OAuth callback. Returns the resolved user dict.

    Raises:
        ValueError: on CSRF mismatch or account-conflict.
        RuntimeError: on token-exchange failure.
    """
    # --- CSRF validation ---
    expected = session.pop("oauth_state", None)
    if not expected or not secrets.compare_digest(expected, state):
        raise ValueError("Invalid or missing OAuth state parameter.")

    # --- Exchange code for tokens ---
    tokens = _exchange_code(code)

    # --- Fetch user info ---
    userinfo = _fetch_userinfo(tokens["access_token"])
    google_sub = userinfo["sub"]
    email = userinfo["email"]
    name = userinfo.get("name", "")

    # --- Resolve account (all in one transaction) ---
    user = _resolve_account(db, google_sub, email, name, tokens)
    return user


# ---------------------------------------------------------------------------
# Account resolution
# ---------------------------------------------------------------------------

def _resolve_account(
    db, google_sub: str, email: str, name: str, tokens: dict
) -> Dict[str, Any]:
    """Link or create a user record. Executed inside a DB transaction."""
    access_token = tokens.get("access_token")
    refresh_token = tokens.get("refresh_token")
    expires_in = tokens.get("expires_in", 3600)
    token_expiry = int(time.time()) + int(expires_in)

    # Branch 1: already linked via (provider, sub)
    oauth_row = db.find_oauth_account("google", google_sub)
    if oauth_row:
        db.update_oauth_tokens(
            oauth_row["id"], access_token, refresh_token, token_expiry
        )
        return db.find_user_by_id(oauth_row["user_id"])

    # Branch 2: existing user with matching email
    user = db.find_user_by_email(email)
    if user:
        # Guard: email already linked to a *different* Google sub
        conflict = db.find_oauth_account_by_user(user["id"], "google")
        if conflict and conflict["provider_account_id"] != google_sub:
            raise ValueError(
                "This email is already linked to a different Google account."
            )
        if not conflict:
            db.insert_oauth_account(
                user["id"], "google", google_sub,
                access_token, refresh_token, token_expiry,
            )
        return user

    # Branch 3: brand-new user
    user = db.create_user(email=email, name=name)
    db.insert_oauth_account(
        user["id"], "google", google_sub,
        access_token, refresh_token, token_expiry,
    )
    return user


# ---------------------------------------------------------------------------
# Token refresh
# ---------------------------------------------------------------------------

def refresh_access_token(db, oauth_account_id: int) -> Optional[str]:
    """Silently refresh the access token. Returns new access token or None."""
    row = db.get_oauth_account(oauth_account_id)
    if not row or not row.get("refresh_token"):
        return None
    if int(time.time()) < row["token_expiry"] - 60:
        return row["access_token"]  # still valid

    try:
        resp = requests.post(GOOGLE_TOKEN_URL, data={
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "refresh_token": row["refresh_token"],
            "grant_type": "refresh_token",
        }, timeout=5)
        resp.raise_for_status()
        data = resp.json()
        new_access = data["access_token"]
        new_expiry = int(time.time()) + int(data.get("expires_in", 3600))
        db.update_oauth_tokens(
            oauth_account_id, new_access, row["refresh_token"], new_expiry
        )
        return new_access
    except Exception as exc:
        log.error("Token refresh failed for oauth_account %s", oauth_account_id)
        return None


# ---------------------------------------------------------------------------
# Token revocation (logout / disconnect)
# ---------------------------------------------------------------------------

def revoke_token(db, oauth_account_id: int) -> None:
    """Revoke the Google refresh token and clear stored tokens. Fail-open."""
    row = db.get_oauth_account(oauth_account_id)
    token = (row or {}).get("refresh_token") or (row or {}).get("access_token")
    if token:
        try:
            resp = requests.post(
                GOOGLE_REVOKE_URL,
                params={"token": token},
                timeout=5,
            )
            if not resp.ok:
                log.warning(
                    "Google revocation returned %s for account %s",
                    resp.status_code, oauth_account_id,
                )
        except Exception:
            log.warning("Google revocation request failed; proceeding with local cleanup.")
    db.clear_oauth_tokens(oauth_account_id)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _exchange_code(code: str) -> dict:
    resp = requests.post(GOOGLE_TOKEN_URL, data={
        "code": code,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "redirect_uri": REDIRECT_URI,
        "grant_type": "authorization_code",
    }, timeout=10)
    if not resp.ok:
        raise RuntimeError(f"Token exchange failed: {resp.status_code}")
    return resp.json()


def _fetch_userinfo(access_token: str) -> dict:
    resp = requests.get(
        GOOGLE_USERINFO_URL,
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()
