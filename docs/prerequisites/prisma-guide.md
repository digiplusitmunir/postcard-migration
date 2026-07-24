# Prisma Guide

How to use Prisma to create, migrate, inspect and repeatedly re-test the
**postcardv2** database. In this project **Prisma (JavaScript) owns the schema**;
data seeding/mapping is done from Python — see [Migration Workflow](../get-started/migration-workflow.md).

## 1. How it's wired up

This project uses **Prisma 7**. Three pieces:

- `schema/schema.prisma` — the data model
- `prisma.config.ts` — tells the CLI where the schema and
  migrations live, and reads `DATABASE_URL` from `.env`
- `package.json` — npm scripts wrapping the CLI

One-time install:

```powershell
npm install
npx prisma validate     # should print "schema is valid"
```

!!! note "Prisma 7 change"
    Older tutorials put `url = env("DATABASE_URL")` inside the `datasource`
    block of the schema. Prisma 7 removed that — the connection URL now lives
    in `prisma.config.ts`. If you see that error in the IDE, the schema and
    config are out of sync.

## 2. Creating the schema in the database

Two different commands — know which one you want:

| Command | What it does | When to use |
|---|---|---|
| `npm run migrate` | Generates a SQL migration file, applies it, records it in `_prisma_migrations` | Normal development — keeps history |
| `npm run migrate:deploy` | Replays existing migration files, creates nothing new | Fresh/experimental DBs, CI |
| `npm run push` | Syncs schema directly, **no** migration file, no history | Quick prototyping only |

First migration:

```powershell
npm run migrate -- --name init
```

This creates `schema/migrations/<timestamp>_init/migration.sql` and applies it.
Commit the migrations folder — it *is* the schema history.

## 3. Tracking migrations

```powershell
npm run migrate:status      # what's applied, what's pending, any drift?
```

Prisma records every applied migration in the `_prisma_migrations` table.
That is why `scripts/truncate_all.py` skips it: after a data wipe the schema
is still considered fully migrated.

After changing `schema.prisma`:

```powershell
npm run migrate -- --name add_xyz_field
```

If the database was changed outside Prisma (drift), development databases can
simply be rebuilt:

```powershell
npm run migrate:reset
```

`migrate:reset` drops the database schema, re-creates it, and replays every
migration — your cleanest possible starting point.

## 4. Prisma Studio

A visual browser/editor for the data:

```powershell
npm run studio
```

Opens at <http://localhost:5555>. Use it to eyeball migrated rows, follow
relations (e.g. Postcard → Collection → CollectionType), and hand-fix
individual records while testing.

## 5. The migration test loop

The whole point of this project is running data injections **multiple times**
until they're right. The loop:

```text
1. schema ready        npm run migrate                   (only when schema changed)
2. baseline data       python scripts/seed.py            (all type tables)
3. inject              run migration notebook / Python script against the Strapi API
4. inspect             npm run studio  /  psql queries
5. wrong? wipe & retry python scripts/truncate_all.py  → back to step 2
```

Full nuke (schema *and* data) when migrations themselves changed:

```powershell
npm run migrate:reset
python scripts/seed.py
```

## 6. Generated client (optional, for JS scripts)

```powershell
npm run generate    # emits the client to generated/client/
```

Only needed if you write a JS data script; Python scripts/notebooks talk to
PostgreSQL directly with `psycopg` — both hit the same database.

## 7. Gotchas specific to this schema

- **Polymorphic tables** (`facet_assignments`, `collection_cluster_entries`,
  `circles`, `user_events.subject`) have **no FK** on their `*_id` columns —
  Prisma can't model polymorphic relations. Integrity is the migration
  scripts' responsibility: always insert the target row first.
- **BigInt ids** — the Prisma client returns JavaScript `BigInt`, and psycopg
  returns Python `int`. When writing JSON exports, cast BigInt first.
- **Json columns** (`seo`, `location`, `social`, `tracking`, `best_months`,
  `event_details`) replace Strapi components — store the component object as-is.
- `SubcollectionPostcard.sequence_order` is a display position, not a date.
