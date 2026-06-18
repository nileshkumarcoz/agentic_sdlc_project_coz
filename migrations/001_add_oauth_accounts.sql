-- Migration: 001_add_oauth_accounts
-- Description: Add oauth_accounts table for federated identity (Google OAuth 2.0)
-- Reversible: Yes (see DOWN section)

-- ============================================================
-- UP
-- ============================================================
CREATE TABLE IF NOT EXISTS oauth_accounts (
    id                  SERIAL PRIMARY KEY,
    user_id             INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    provider            VARCHAR(64) NOT NULL,
    provider_account_id VARCHAR(255) NOT NULL,
    access_token        TEXT,          -- encrypted at rest
    refresh_token       TEXT,          -- encrypted at rest
    token_expiry        BIGINT,        -- unix timestamp
    created_at          TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_provider_account UNIQUE (provider, provider_account_id)
);

CREATE INDEX IF NOT EXISTS idx_oauth_accounts_user_id
    ON oauth_accounts (user_id);

CREATE INDEX IF NOT EXISTS idx_oauth_accounts_provider_user
    ON oauth_accounts (user_id, provider);

-- ============================================================
-- DOWN  (run these statements to reverse the migration)
-- ============================================================
-- DROP INDEX IF EXISTS idx_oauth_accounts_provider_user;
-- DROP INDEX IF EXISTS idx_oauth_accounts_user_id;
-- DROP TABLE IF EXISTS oauth_accounts;
