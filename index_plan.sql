-- Consolidated Index Plan
-- Generated after deterministic deduplication
-- Total indexes: 10

CREATE INDEX idx_users_last_login_country_code ON users (last_login DESC, country_code);;
CREATE INDEX idx_positions_status_account_id ON positions (status, account_id);;
CREATE INDEX idx_accounts_user_id ON accounts (user_id);;
CREATE INDEX idx_users_email ON users (email);;
CREATE INDEX idx_transactions_account_id_type_status_created_at ON transactions (account_id, transaction_type, status, created_at DESC);;
CREATE INDEX idx_users_id ON users(id);;
CREATE INDEX idx_users_created_at ON users(created_at);;
CREATE INDEX idx_users_country_code_created_at ON users(country_code, created_at);;
CREATE INDEX idx_users_kyc_status ON users(kyc_status);;
CREATE INDEX idx_users_created_at_last_login ON users(created_at, last_login);;
