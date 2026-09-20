/*
 SQL Server/T-SQL equivalent for environments where Bancs is hosted on SQL Server.
 The runnable MVP uses PostgreSQL; this script demonstrates portable relational
 design, constraints, auditing and the locking approach expected in T-SQL.
*/
CREATE TABLE dbo.Accounts (
    account_id varchar(40) NOT NULL PRIMARY KEY,
    owner_id varchar(40) NOT NULL,
    currency char(3) NOT NULL,
    balance decimal(18,2) NOT NULL CHECK (balance >= 0),
    version bigint NOT NULL CONSTRAINT DF_Accounts_Version DEFAULT (0),
    created_at datetime2(3) NOT NULL CONSTRAINT DF_Accounts_Created DEFAULT (SYSUTCDATETIME())
);

CREATE TABLE dbo.Transactions (
    transaction_id uniqueidentifier NOT NULL PRIMARY KEY,
    source_account varchar(40) NOT NULL,
    destination_account varchar(40) NOT NULL,
    amount decimal(18,2) NOT NULL CHECK (amount > 0),
    currency char(3) NOT NULL,
    status varchar(20) NOT NULL,
    created_at datetime2(3) NOT NULL CONSTRAINT DF_Tx_Created DEFAULT (SYSUTCDATETIME()),
    completed_at datetime2(3) NULL,
    CONSTRAINT FK_Tx_Source FOREIGN KEY (source_account) REFERENCES dbo.Accounts(account_id),
    CONSTRAINT FK_Tx_Destination FOREIGN KEY (destination_account) REFERENCES dbo.Accounts(account_id)
);

CREATE INDEX IX_Transactions_CreatedAt ON dbo.Transactions(created_at);

-- T-SQL equivalent of the deterministic PostgreSQL row lock:
-- SELECT ... FROM dbo.Accounts WITH (UPDLOCK, ROWLOCK) WHERE account_id IN (...).
