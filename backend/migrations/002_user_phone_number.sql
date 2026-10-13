ALTER TABLE users
    ADD COLUMN IF NOT EXISTS phone_number VARCHAR(20);

CREATE UNIQUE INDEX IF NOT EXISTS ix_users_phone_number
    ON users(phone_number)
    WHERE phone_number IS NOT NULL;
