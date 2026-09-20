CREATE TABLE IF NOT EXISTS accounts (
    account_id VARCHAR(40) PRIMARY KEY,
    owner_id VARCHAR(40) NOT NULL,
    currency CHAR(3) NOT NULL,
    balance NUMERIC(18,2) NOT NULL CHECK (balance >= 0),
    version BIGINT NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS transactions (
    transaction_id UUID PRIMARY KEY,
    source_account VARCHAR(40) NOT NULL REFERENCES accounts(account_id),
    destination_account VARCHAR(40) NOT NULL REFERENCES accounts(account_id),
    amount NUMERIC(18,2) NOT NULL CHECK (amount > 0),
    currency CHAR(3) NOT NULL,
    status VARCHAR(20) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    error_code VARCHAR(80)
);

CREATE INDEX IF NOT EXISTS idx_transactions_created_at ON transactions(created_at);
CREATE INDEX IF NOT EXISTS idx_transactions_source ON transactions(source_account);

CREATE TABLE IF NOT EXISTS recommendations (
    id BIGSERIAL PRIMARY KEY,
    account_id VARCHAR(40) NOT NULL,
    source_transaction_id UUID,
    recommendation TEXT NOT NULL,
    model_version VARCHAR(30) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_recommendations_source_transaction
    ON recommendations(source_transaction_id)
    WHERE source_transaction_id IS NOT NULL;

CREATE TABLE IF NOT EXISTS audit_events (
    id BIGSERIAL PRIMARY KEY,
    transaction_id UUID,
    event_type VARCHAR(60) NOT NULL,
    details JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

INSERT INTO accounts(account_id, owner_id, currency, balance)
VALUES
('ACC-1001', 'CUS-001', 'USD', 1000.00),
('ACC-1002', 'CUS-002', 'USD', 500.00),
('ACC-1003', 'CUS-003', 'USD', 750.00),
('ACC-1004', 'CUS-004', 'USD', 1200.00),
('ACC-1005', 'CUS-005', 'USD', 300.00),
('ACC-1006', 'CUS-006', 'USD', 900.00),
('ACC-1007', 'CUS-007', 'USD', 1500.00),
('ACC-1008', 'CUS-008', 'USD', 425.00),
('ACC-1009', 'CUS-009', 'USD', 680.00),
('ACC-1010', 'CUS-010', 'USD', 2500.00)
ON CONFLICT (account_id) DO NOTHING;
