# Initialisation

Bringing a database from **nothing** to **ready for data injection**, in order:

```text
1. create database  →  2. point .env  →  3. migrate (Prisma)
→  4. seed (types)  →  5. inspect in Studio  →  then: migration notebooks
```

## 1. Create the database

```powershell
createdb -U postgres -h 127.0.0.1 postcardv2
```

Any name works — `postcardv2`, `postcardv2_test`, a throwaway experiment DB.
(More on drop/recreate/backup in [PostgreSQL Lifecycle](../prerequisites/postgresql-lifecycle.md).)

## 2. Point `.env` at it

Edit `DATABASE_URL` in the project-root `.env` — Prisma **and** every Python
script read this one line:

```text
DATABASE_URL=postgres://postgres:admin12345@127.0.0.1:5432/postcardv2
```

## 3. Run the migration (Prisma)

```powershell
npm run migrate -- --name init   # first time: generates + applies + records
# or, if migration files already exist in schema/migrations/:
npm run migrate:deploy           # replays them onto the fresh DB
npm run migrate:status           # verify: everything applied, no drift
```

All tables, enums and indexes now exist, plus Prisma's own
`_prisma_migrations` history table.

## 4. Seed — the developer-defined types

```powershell
python scripts/seed.py
```

`seed.py` fills **every table the API/application will never write to** —
the type/definition tables that developers maintain and that all other data
FKs onto (collection/user/facet/response types + values, sample tags).
It is idempotent, so *truncate → seed* can be repeated endlessly.

Full table-by-table breakdown: [Seed Scripts](seed-scripts.md).

## 5. Inspect with Prisma Studio

```powershell
npm run studio        # http://localhost:5555
```

Check `collection_types`, `user_types`, `facet_types` → `facet_values`, and
`response_types` → `response_fields`.

## 6. Continue with the migration notebooks

Seeded types in place, the dependent data comes from notebooks, in order:

1. [Geo migration](../migrations/geo-migration.md) — `notebooks/geo_migration.ipynb`
2. [User migration](../migrations/user-migration.md) — `notebooks/user_migration.ipynb`

Run order and dependencies: [Migrations overview](../migrations/index.md).

## Recap

```powershell
createdb -U postgres -h 127.0.0.1 postcardv2   # 1
# edit DATABASE_URL in .env                    # 2
npm run migrate:deploy                          # 3
python scripts/seed.py                          # 4
npm run studio                                  # 5
# then: geo_migration.ipynb → user_migration.ipynb
```
