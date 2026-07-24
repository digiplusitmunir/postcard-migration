# Migrations — Overview & Run Order

Each data migration is a Jupyter notebook in `notebooks/` with a companion
document here describing the full field mapping, what gets dropped, and what
needs manual work afterwards.

## Run order — this matters

Migrations depend on each other's data. Always run them in this order:

```text
0. Prerequisites   npm run migrate:deploy  +  python scripts/seed.py
                        (schema + type tables — see Get Started)

1. Geo             notebooks/geo_migration.ipynb
                        countries → regions → cities (synthesized) → localities
                        nothing depends on users; everything depends on geo

2. Users           notebooks/user_migration.ipynb
                        users + user_roles — requires geo (country lookups)
                        and seed.py (user_types)

3. ...next         companies, media, content (collections/postcards),
                        circles, memories — notebooks to be added, in an
                        order that respects their FKs
```

| # | Migration | Depends on | Mapping doc | Notebook (rendered) |
|---|---|---|---|---|
| 1 | Geo | seed only | [Geo Migration](geo-migration.md) | [geo_migration.ipynb](notebooks/geo_migration.ipynb) |
| 2 | Users | seed + **1** | [User Migration](user-migration.md) | [user_migration.ipynb](notebooks/user_migration.ipynb) |

The **Notebook (rendered)** column shows the live notebook — every markdown and
code cell — rendered straight from `notebooks/*.ipynb`. It is the same file you
run in Jupyter; the mapping doc beside it explains the field-by-field decisions.

!!! warning "Don't skip ahead"
    Running the user notebook before geo leaves every `users.country_id`
    NULL — the lookups silently miss. Each notebook states its prerequisites
    in its first cell; trust that list.

## Re-running

All notebooks are idempotent (upserts on natural keys). To restart an
experiment from scratch:

```powershell
python scripts/truncate_all.py
python scripts/seed.py
# then re-run the notebooks, again in order
```
