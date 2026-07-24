# Postcard Migration

Documentation for migrating Postcard Travel Club from the legacy **Strapi CMS**
to the new **PostgreSQL + Prisma** stack.

- **Source**: Strapi API (`CMS_BASE_URL` in `.env`) — old schema in `schema/contentTypes.d.ts`
- **Target**: PostgreSQL database `postcardv2` — new schema in `schema/schema.prisma`
- **Tooling split**: schema changes via **Prisma/JavaScript** (`npm run ...`), data via **Python** (`scripts/`, `notebooks/`)

## Shortcuts

### Prerequisites — the tools

| Document | What it covers |
|---|---|
| [PostgreSQL Lifecycle](prerequisites/postgresql-lifecycle.md) | Creating/dropping databases, everyday psql operations, backup & restore |
| [Prisma Guide](prerequisites/prisma-guide.md) | How Prisma is wired up, running & tracking migrations, Prisma Studio, reset |

### Get Started — from empty DB to ready

| Document | What it covers |
|---|---|
| [Initialisation](get-started/initialisation.md) | Create DB → `.env` → migrate → seed → Studio, step by step |
| [Seed Scripts](get-started/seed-scripts.md) | Exactly what `seed.py` inserts and what `truncate_all.py` wipes |
| [Migration Workflow](get-started/migration-workflow.md) | The repeatable experiment loop: inject → inspect → wipe → repeat |

### Migrations — the data, in run order

| # | Document | Notebook |
|---|---|---|
| — | [Overview & run order](migrations/index.md) | |
| 1 | [Geo Migration](migrations/geo-migration.md) | `notebooks/geo_migration.ipynb` |
| 2 | [User Migration](migrations/user-migration.md) | `notebooks/user_migration.ipynb` |

## The developer loop

```text
npm run migrate  →  python scripts/seed.py  →  run migration notebooks (in order)
        ↑                                                     |
        └────────────  python scripts/truncate_all.py  ←──────┘
```
