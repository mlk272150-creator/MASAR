ALTER TABLE tasks
    DROP CONSTRAINT IF EXISTS ck_tasks_reward_points_nonnegative;

ALTER TABLE tasks
    ADD COLUMN IF NOT EXISTS assignee_id INTEGER
        REFERENCES users(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS reward_points INTEGER NOT NULL DEFAULT 0;

ALTER TABLE tasks
    ADD CONSTRAINT ck_tasks_reward_points_nonnegative
    CHECK (reward_points >= 0);

ALTER TABLE ledger
    DROP CONSTRAINT IF EXISTS ck_ledger_entry_type;

ALTER TABLE ledger
    ADD CONSTRAINT ck_ledger_entry_type
    CHECK (entry_type IN ('credit', 'debit', 'adjustment', 'escrow_hold', 'escrow_release'));

CREATE UNIQUE INDEX IF NOT EXISTS uq_ledger_reference
    ON ledger(reference);
