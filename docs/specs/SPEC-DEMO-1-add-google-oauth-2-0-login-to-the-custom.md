# Spec: SPEC-DEMO-1 Add Google OAuth 2.0 Login to the Customer Portal

## Problem & Acceptance Criteria

Customers currently authenticate exclusively via email and password. There is no federated identity option, creating friction for users who prefer single sign-on. This story adds Sign in with Google (OAuth 2.0) to the customer portal, including access-token refresh, token revocation on logout/account disconnect, and deterministic linking of inbound Google identities to pre-existing email-based accounts to prevent duplicate user records.

**Acceptance Criteria:**

- A user with no existing account can click 'Sign in with Google', complete the Google OAuth consent flow, and land on the authenticated portal home page with a newly created account.
- A user with an existing email+password account whose email matches the Google identity is automatically linked on first Google sign-in — no duplicate account is created and the user retains access to all prior data.
- After a successful Google sign-in, the system stores and uses the OAuth refresh token to silently obtain new access tokens before expiry, with no user-visible re-authentication prompt during a normal session.
- When a user logs out or explicitly disconnects their Google account, the system revokes the Google OAuth token via Google's revocation endpoint and removes stored tokens from the database.
- A user who has linked Google can still log in via email+password (existing credential is preserved).
- The Google OAuth client ID and secret are configurable via environment variables and are never hard-coded in source.
- The OAuth callback endpoint validates the `state` parameter to prevent CSRF attacks and returns a 400 on mismatch.
- All OAuth-related DB columns (provider, provider_account_id, access_token, refresh_token, token_expiry) are added via versioned migrations that are reversible.
- End-to-end happy-path and error-path flows are covered by automated tests (unit + integration).

## Assumptions & Open Questions

**Assumptions:**

- The customer portal is a web application housed in the agentic_sdlc_project_coz repository.
- Google Cloud project credentials (Client ID, Client Secret) will be provisioned by the platform/infra team before QA; the dev team is responsible only for code integration.
- The existing user model has a unique index on email address that can serve as the linking key.
- The application already has a session or JWT mechanism that can be extended to represent Google-authenticated sessions.
- HTTPS is enforced in all environments where OAuth callbacks will be registered; localhost redirect URIs will be allowed only in development.
- The team has access to Google's OAuth 2.0 discovery document / well-known endpoint for token validation.
- Token storage at rest is handled by the existing secrets/encryption strategy already in place for passwords (e.g., encrypted columns or a secrets manager).

**Open Questions:**

- Should token revocation on logout be synchronous (block the logout response) or fire-and-forget? Failure handling strategy if Google's revocation endpoint is unavailable?
- What is the desired UX when a Google email matches an existing account but that account was created with a *different* Google sub (i.e., two Google accounts sharing an email) — merge, reject, or prompt?
- Is there a requirement to support Google Workspace / hd (hosted domain) restrictions, i.e., allow only a specific corporate domain?
- Should users be able to link *multiple* OAuth providers (future-proofing) or is this strictly Google-only for now? This affects the DB schema design.
- What is the session lifetime policy for Google-authenticated sessions vs. email+password sessions?
- Is there a requirement to surface the user's Google profile photo or display name in the portal after linking?
- Do we need an admin-facing view to see which accounts are Google-linked or to force-revoke tokens?

## Target Repos

| Repo | Provider | Why |
|---|---|---|
| agentic_sdlc_project_coz | github | This is the sole candidate repository and the one containing the customer portal application. All changes — OAuth flow, token management, account linking logic, DB migrations, and tests — will be implemented here. |

## Design / Approach

**High-level flow**
1. Frontend renders a 'Sign in with Google' button that initiates a redirect to a new backend endpoint `GET /auth/google` which builds the Google authorization URL (with `state`, `nonce`, required scopes: `openid email profile`, and `access_type=offline` to obtain a refresh token) and redirects the browser.
2. Google redirects to `GET /auth/google/callback?code=...&state=...`. The backend validates `state` against the value stored in the user's session/cookie, exchanges the code for tokens via Google's token endpoint, and decodes the ID token to extract `sub`, `email`, `name`.
3. **Account resolution logic** (executed in a DB transaction):
   - Look up `oauth_accounts` table by `(provider='google', provider_account_id=sub)` → if found, retrieve the linked user and log them in.
   - Else look up `users` table by `email` → if found, insert a row into `oauth_accounts` linking this Google identity to the existing user, then log in.
   - Else create a new `users` row and a corresponding `oauth_accounts` row, then log in.
4. Store `access_token`, `refresh_token`, `token_expiry` in `oauth_accounts`. A background job or middleware checks expiry before each authenticated request and calls Google's token endpoint to refresh silently.
5. On logout or 'Disconnect Google', call `POST https://oauth2.googleapis.com/revoke?token=<refresh_token>`, then delete or null-out stored tokens, and destroy the session.

**DB schema additions** (versioned, reversible migrations):
- `oauth_accounts` table: `id`, `user_id` (FK → users), `provider` (varchar), `provider_account_id` (varchar), `access_token` (encrypted text), `refresh_token` (encrypted text), `token_expiry` (timestamp), `created_at`, `updated_at`. Unique index on `(provider, provider_account_id)`.

**Configuration**: `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI` as environment variables read at startup.

**Security controls**: CSRF via `state` param; PKCE not required for server-side flow but may be added; tokens encrypted at rest; refresh token stored only if `access_type=offline` grant is received.

## Edge Cases & Test Plan

**Edge cases**
- Google returns an email that matches an existing account already linked to a *different* Google `sub` → reject with a clear error message; do not overwrite the existing link.
- Google revocation endpoint returns a non-2xx response during logout → log the error, proceed with local session destruction anyway, surface no error to the user (fail-open for UX, fail-safe for session).
- Refresh token is absent (user denied offline access or previously revoked) → detect missing refresh token, prompt user to re-authenticate with `prompt=consent`.
- Access token expired and refresh fails (revoked externally) → invalidate local session, redirect to login with an informative message.
- Duplicate callback request (replay attack or double browser tab) → `state` consumed on first use; second request receives 400.
- User creates a Google account then later changes their Google email → `sub` remains stable; linking by `sub` still works, but stored email should be updated on next login.
- Network timeout calling Google's token or revocation endpoint → handle with timeout + retry (max 2 retries), surface appropriate error.

**Test plan**
- *Unit tests*: account resolution logic (all three branches), state validation, token refresh logic, revocation call with mocked HTTP client.
- *Integration tests*: full OAuth callback flow with a stubbed Google OAuth server; DB state assertions for new-account, link-existing, and already-linked scenarios.
- *Security tests*: missing `state`, mismatched `state`, replayed `code` all return 400; tokens are not logged in application logs.
- *Manual / QA*: end-to-end test in a staging environment with a real Google OAuth app in test mode; verify linked accounts in DB; verify token revocation via Google's token-info endpoint post-logout.

## Out of Scope

- Support for other OAuth providers (GitHub, Apple, Microsoft) — schema should not preclude them but no implementation is included.
- Mobile app OAuth flow (this spec covers the web customer portal only).
- Admin UI for managing or auditing linked OAuth accounts.
- Changes to the email+password registration or password-reset flows.
- Google One Tap / FedCM silent sign-in widget.
- Rate limiting or brute-force protection on the OAuth endpoints (assumed to be handled by existing API gateway/middleware).
- GDPR data-export or account-deletion flows for OAuth-linked data (separate story).

## Definition of Done

- All acceptance criteria pass and are verified by automated tests in CI.
- DB migrations run cleanly forward and backward in the staging environment.
- No Google credentials or tokens appear in application logs (verified by log-scan step in CI).
- Environment-variable configuration is documented in the repo's README / `.env.example`.
- A peer code review has been approved by at least one other engineer.
- The feature has been smoke-tested end-to-end in the staging environment against a real (test-mode) Google OAuth application.
- No new high or critical severity findings from a static-analysis or dependency-audit scan.
- Open questions marked as blockers are resolved before merge to main.
