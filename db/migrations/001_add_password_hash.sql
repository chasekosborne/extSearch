-- Add password_hash column for registered users.
-- Guest users have NULL password_hash.
ALTER TABLE "users" ADD COLUMN IF NOT EXISTS "password_hash" varchar;
