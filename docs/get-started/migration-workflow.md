# Migration Workflow

The end-to-end process for experimenting with the migration. The division of labor:

- **Schema** (create/alter tables) → **Prisma** (JavaScript tooling, `npm run ...`)
- **Data** (seed, map, inject, verify) → **Python** (`scripts/*.py`, notebooks)

You can repeat this loop as many times as needed — against `postcardv2` or any
fresh experimental database.

## Step 0 — one-time setup

```powershell
# JavaScript side (Prisma CLI)
npm install

# Python side (psycopg, dotenv, mkdocs)
.venv\Scripts\activate
pip install -r requirements.txt
```

## Step 1 — create a database

Use the existing `postcardv2`, or spin up a fresh one for an experiment:

```powershell
createdb -U postgres -h 127.0.0.1 postcardv2_test
```

(See [PostgreSQL Lifecycle](../prerequisites/postgresql-lifecycle.md) for drop/recreate, backup, etc.)

## Step 2 — point `.env` at it

Everything — Prisma CLI **and** the Python scripts — reads `DATABASE_URL` from
the single `.env` in the project root:

```text
DATABASE_URL=postgres://postgres:admin12345@127.0.0.1:5432/postcardv2_test
```

Change this one line and the whole toolchain targets the new database.

## Step 3 — apply the schema (Prisma)

```powershell
# first time on this machine / after schema changes: creates + applies a migration
npm run migrate            # prisma migrate dev (prompts for a migration name)

# fresh database, migrations already exist: just replay them
npm run migrate:deploy

# check what's applied / pending
npm run migrate:status
```

Migration SQL files land in `schema/migrations/` — they are the schema history,
keep them.

## Step 4 — seed the type tables (Python)

```powershell
python scripts/seed.py
```

Inserts every developer-defined type table (collection/user/response
types + values, sample tags; facets come from the tags facet migration) —
details in [Seed Scripts](seed-scripts.md).
Idempotent — safe to run repeatedly.

## Step 5 — run migration scripts / notebooks (Python)

Data mapping lives in Python: pull entities from the Strapi API
(`CMS_BASE_URL` + `CMS_API_TOKEN` from `.env`), transform to the new model,
insert with `psycopg`. Notebooks go in `notebooks/`, reusable scripts in
`scripts/`.

```powershell
jupyter lab          # or run a script directly
python scripts/<your_migration_script>.py
```

## Step 6 — inspect the result

```powershell
npm run studio       # Prisma Studio at http://localhost:5555
# or
psql "postgres://postgres:admin12345@127.0.0.1:5432/postcardv2_test"
```

## Step 7 — wrong? wipe and go again

```powershell
# data only (schema stays, migration history stays)
python scripts/truncate_all.py
# → back to Step 4

# schema AND data (drops, recreates, replays all migrations)
npm run migrate:reset
# → back to Step 4
```

## Cheat sheet

| I want to... | Run |
|---|---|
| Target a different DB | edit `DATABASE_URL` in `.env` |
| Change the schema | edit `schema/schema.prisma`, then `npm run migrate` |
| Build schema on a fresh DB | `npm run migrate:deploy` |
| See applied/pending migrations | `npm run migrate:status` |
| Seed the type tables | `python scripts/seed.py` |
| Wipe all data | `python scripts/truncate_all.py` |
| Full rebuild | `npm run migrate:reset` then `python scripts/seed.py` |
| Browse data visually | `npm run studio` |
