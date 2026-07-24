# PostgreSQL Lifecycle

A minimal, practical guide for working with the local PostgreSQL server used by this
project. The target database is **postcardv2**:

```text
postgres://postgres:admin12345@127.0.0.1:5432/postcardv2
```

## 1. Connecting

`psql` is PostgreSQL's interactive terminal. Connect to the server:

```powershell
# connect to the default database as the postgres superuser
psql -U postgres -h 127.0.0.1 -p 5432

# connect straight to postcardv2
psql -U postgres -h 127.0.0.1 -p 5432 -d postcardv2

# or with a connection string
psql "postgres://postgres:admin12345@127.0.0.1:5432/postcardv2"
```

!!! tip
    Set `$env:PGPASSWORD = "admin12345"` in PowerShell to avoid the password prompt.

## 2. Creating and dropping a database

From `psql` (connected to any database, e.g. `postgres`):

```sql
-- create
CREATE DATABASE postcardv2;

-- drop (disconnect everyone first if it complains)
DROP DATABASE postcardv2;

-- drop even with active connections (PostgreSQL 13+)
DROP DATABASE postcardv2 WITH (FORCE);
```

Or from PowerShell without entering psql:

```powershell
createdb -U postgres -h 127.0.0.1 postcardv2
dropdb   -U postgres -h 127.0.0.1 postcardv2
```

Recreating from scratch (common during migration testing):

```powershell
dropdb -U postgres -h 127.0.0.1 --if-exists postcardv2
createdb -U postgres -h 127.0.0.1 postcardv2
# then let Prisma build the schema — see the Prisma guide
```

## 3. Everyday psql commands

| Command | What it does |
|---|---|
| `\l` | list databases |
| `\c postcardv2` | switch to database |
| `\dt` | list tables |
| `\d tablename` | describe a table (columns, indexes, FKs) |
| `\dT+` | list enum types |
| `\x` | toggle expanded (vertical) output — great for wide rows |
| `\timing` | show query execution time |
| `\q` | quit |

## 4. Simple operations

```sql
-- how many rows in each key table
SELECT relname AS table, n_live_tup AS rows
FROM pg_stat_user_tables
ORDER BY n_live_tup DESC;

-- peek at data
SELECT * FROM collection_types ORDER BY priority;
SELECT id, name, slug, status FROM collections LIMIT 20;

-- count postcards per collection type
SELECT ct.name, COUNT(p.id)
FROM collection_types ct
LEFT JOIN postcards p ON p.collection_type_id = ct.id
GROUP BY ct.name;

-- delete data from one table (respects FKs)
DELETE FROM postcards;

-- empty a table fast and reset its id sequence, following FKs
TRUNCATE TABLE postcards RESTART IDENTITY CASCADE;
```

!!! warning
    `TRUNCATE ... CASCADE` also empties every table that references the one you
    name. To wipe **all** data safely, use `python scripts/truncate_all.py`,
    which skips Prisma's migration-history table.

## 5. Backup and restore

```powershell
# dump (custom format, compressed)
pg_dump -U postgres -h 127.0.0.1 -Fc postcardv2 -f postcardv2.dump

# dump plain SQL (readable, diff-able)
pg_dump -U postgres -h 127.0.0.1 postcardv2 -f postcardv2.sql

# restore a custom-format dump into a fresh database
createdb -U postgres -h 127.0.0.1 postcardv2_restore
pg_restore -U postgres -h 127.0.0.1 -d postcardv2_restore postcardv2.dump

# restore plain SQL
psql -U postgres -h 127.0.0.1 -d postcardv2_restore -f postcardv2.sql
```

Take a dump **before** experimenting with a destructive migration step — restoring
a dump is much faster than re-pulling everything from the Strapi API.

## 6. Useful checks

```sql
-- who is connected to postcardv2
SELECT pid, usename, application_name, state
FROM pg_stat_activity WHERE datname = 'postcardv2';

-- kill a stuck connection
SELECT pg_terminate_backend(<pid>);

-- database size
SELECT pg_size_pretty(pg_database_size('postcardv2'));

-- largest tables
SELECT relname, pg_size_pretty(pg_total_relation_size(relid)) AS size
FROM pg_catalog.pg_statio_user_tables
ORDER BY pg_total_relation_size(relid) DESC LIMIT 10;
```
