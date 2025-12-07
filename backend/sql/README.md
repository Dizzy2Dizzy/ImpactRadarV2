# SQL Migrations - Alternative to Alembic

This directory contains raw SQL migration scripts for applying schema changes directly to PostgreSQL without using Alembic.

## Why This Approach?

**Problem:** Alembic is currently blocked by a pre-existing circular import issue with `releaseradar/logging.py`. This prevents `alembic upgrade head` from running successfully, blocking production databases from receiving critical schema updates.

**Solution:** These raw SQL scripts can be applied directly using `psql`, bypassing the Alembic dependency chain entirely.

## Prerequisites

- PostgreSQL client (`psql`) installed
- `DATABASE_URL` environment variable set, or connection string available
- Database user with CREATE TABLE permissions

## How to Apply Migrations

### Using Environment Variable

If `DATABASE_URL` is set:

```bash
psql $DATABASE_URL -f backend/sql/migrations/001_add_data_quality_tables.sql
```

### Using Connection String Directly

```bash
psql "postgresql://user:password@host:port/database" -f backend/sql/migrations/001_add_data_quality_tables.sql
```

### Using Replit Development Database

```bash
cd backend
psql $DATABASE_URL -f sql/migrations/001_add_data_quality_tables.sql
```

## How to Rollback Migrations

**WARNING:** Rollback will delete all data in the affected tables.

```bash
psql $DATABASE_URL -f backend/sql/migrations/001_add_data_quality_tables_rollback.sql
```

## Available Migrations

### 001_add_data_quality_tables

**Purpose:** Adds data quality monitoring and auditing infrastructure.

**Tables Created:**
- `data_quality_snapshots` - Tracks quality metrics and data freshness
- `data_pipeline_runs` - Logs pipeline execution status and timing
- `data_lineage_records` - Tracks data provenance and source URLs
- `audit_log_entries` - Audit log for all entity mutations

**Forward Migration:** `001_add_data_quality_tables.sql`  
**Rollback Migration:** `001_add_data_quality_tables_rollback.sql`

**Usage:**
```bash
# Apply migration
psql $DATABASE_URL -f backend/sql/migrations/001_add_data_quality_tables.sql

# Rollback (if needed)
psql $DATABASE_URL -f backend/sql/migrations/001_add_data_quality_tables_rollback.sql
```

## Verification

After applying a migration, verify the tables were created:

```bash
psql $DATABASE_URL -c "\dt data_*"
psql $DATABASE_URL -c "\dt audit_*"
```

You should see:
- data_quality_snapshots
- data_pipeline_runs
- data_lineage_records
- audit_log_entries

To inspect the schema of a specific table:

```bash
psql $DATABASE_URL -c "\d+ data_quality_snapshots"
```

## Schema Consistency

These SQL scripts are manually synchronized with the SQLAlchemy models in `backend/releaseradar/db/models.py`. The schemas match exactly:

- Column names, types, and nullability match SQLAlchemy definitions
- Indexes match the `Index()` declarations in model `__table_args__`
- Foreign keys match SQLAlchemy `ForeignKey()` constraints
- Default values match SQLAlchemy `default=` parameters

## Production Deployment

For production databases:

1. **Backup first:**
   ```bash
   pg_dump $PRODUCTION_DATABASE_URL > backup_$(date +%Y%m%d_%H%M%S).sql
   ```

2. **Apply migration:**
   ```bash
   psql $PRODUCTION_DATABASE_URL -f backend/sql/migrations/001_add_data_quality_tables.sql
   ```

3. **Verify:**
   ```bash
   psql $PRODUCTION_DATABASE_URL -c "\dt data_*"
   psql $PRODUCTION_DATABASE_URL -c "\dt audit_*"
   ```

## Future Migrations

When adding new migrations:

1. Use sequential numbering: `002_`, `003_`, etc.
2. Always create both forward and rollback scripts
3. Test on development database first
4. Document the migration in this README
5. Keep SQLAlchemy models in sync

## When to Use Alembic vs SQL Scripts

**Use SQL scripts when:**
- Alembic is blocked by import/dependency issues
- Applying hotfixes to production
- Working with external/legacy databases
- Debugging schema issues

**Use Alembic when:**
- Alembic is working properly
- Need auto-generated migrations
- Want revision history tracking
- Working with complex schema changes

## Troubleshooting

### Error: "relation already exists"

The migration uses `CREATE TABLE IF NOT EXISTS`, so it's safe to re-run. However, if you see this error, the tables may already exist. Verify with:

```bash
psql $DATABASE_URL -c "\dt"
```

### Error: "permission denied"

Your database user needs CREATE privileges. Grant them:

```sql
GRANT CREATE ON DATABASE your_database TO your_user;
```

### Error: "foreign key constraint violation"

The `audit_log_entries` table has a foreign key to `users.id`. Ensure the `users` table exists before running the migration.

## Support

For issues or questions:
1. Check PostgreSQL logs for detailed error messages
2. Verify DATABASE_URL is correct
3. Ensure database user has sufficient permissions
4. Review the SQL script comments for schema details
