# PostgreSQL setup

1. Create the database (if it doesn't exist):

   ```bash
   createdb extsearch_dev
   ```

   Or with a specific user:

   ```bash
   createdb -U extsearch extsearch_dev
   ```

2. Run the schema:

   ```bash
   psql $DATABASE_URL -f db/Database.sql
   ```

3. Run migrations (adds `password_hash` for user accounts):

   ```bash
   psql $DATABASE_URL -f db/migrations/001_add_password_hash.sql
   ```

   Or if using the connection string from `.env`:

   ```bash
   psql postgresql://extsearch:a@localhost/extsearch_dev -f db/Database.sql
   ```

4. Configure `.env`:

   Ensure `DATABASE_URL` is set (already in `.env`):

   ```
   DATABASE_URL=postgresql://extsearch:a@localhost/extsearch_dev
   ```

   For production, also set:

   ```
   FLASK_SECRET_KEY=your-secure-random-secret
   ```

## Alternative: Docker

If you use Docker for PostgreSQL:

```bash
docker run -d --name extsearch-db -e POSTGRES_USER=extsearch -e POSTGRES_PASSWORD=a -e POSTGRES_DB=extsearch_dev -p 5432:5432 postgres:16
psql postgresql://extsearch:a@localhost:5432/extsearch_dev -f db/Database.sql
```
