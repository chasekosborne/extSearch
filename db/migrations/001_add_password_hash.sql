psql postgresql://extsearch:a@localhost:5432/extsearch_auth -f auth_server/db/schema.sql
-- Add password_hash column for registered users.
-- Guest users have NULL password_hash.
ALTER TABLE "users" ADD COLUMN IF NOT EXISTS "password_hash" varchar;
