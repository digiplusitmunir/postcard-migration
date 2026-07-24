# Seed Scripts

The two Python scripts that bracket every migration experiment: `seed.py`
puts the baseline in, `truncate_all.py` takes everything out. Both read
`DATABASE_URL` from the project-root `.env` and both are safe to run over
and over.

## `scripts/seed.py` — the developer-defined types

```powershell
python scripts/seed.py
```

Fills **every table the API/application will never write to** — the
type/definition tables that developers maintain and that all other data FKs
onto. Real known values where they exist, 2–3 samples elsewhere:

| Table | Rows seeded | Who depends on it |
|---|---|---|
| `collection_types` | Properties, Restaurants, Events, Shopping, Destination Expert | every Collection & Postcard |
| `subcollection_types` | Journey (under Properties) | every Subcollection |
| `collection_cluster_types` | City Guide, Partner Affiliation | every CollectionCluster |
| `user_types` | Member *(default)*, Partner *(creator)*, Staff Editor *(creator)*, Admin *(admin)* | every UserRole — the role *rows* are created by the app / user migration, only the types are seeded |
| `facet_types` | Property Type *(single-select, scoped to Properties)*, Experience Theme *(multi, broad)*, Cuisine *(multi, scoped to Restaurants)* | every FacetAssignment |
| `facet_values` | Boutique Stays, Signature Experiences, Glamping · Cultural, Wellness · Indian, Italian | starter values — extend the lists in the script |
| `tags` | Stargazing, Infinity Pool, Farm to Table | sample postcard feature tags |
| `response_types` | contact_form, feedback, newsletter_signup | every Response |
| `response_fields` | per-form field definitions (contact_form mirrors legacy ContactUs) | form rendering + validation |

**Not** seeded (created by migrations or the app): users, user_roles, geo
hierarchy, companies, media, and all content.

!!! tip "Idempotent by design"
    Every insert is an upsert on its natural key (slug / field name), so the
    sequence *truncate → seed* can be repeated endlessly while testing, and
    edits to the lists in the script land on the next run.

## `scripts/truncate_all.py` — wipe the data, keep the schema

```powershell
python scripts/truncate_all.py          # asks for confirmation
python scripts/truncate_all.py --yes    # no prompt (for notebooks/CI)
```

- Empties **every table in the public schema** with
  `TRUNCATE ... RESTART IDENTITY CASCADE` (identity sequences restart at 1).
- **Skips `_prisma_migrations`** — after a wipe the schema is still fully
  migrated; no need to touch Prisma.
- Prints the table list and requires a `y` before doing anything
  (unless `--yes`).

After a wipe, re-run `python scripts/seed.py` before injecting data again.

## Where they fit

```text
npm run migrate         (schema)
python scripts/seed.py  (types)          ←──────────────┐
notebooks / scripts     (data injection)                │
    ...wrong? →         python scripts/truncate_all.py ─┘
```

Next: [Migration Workflow](migration-workflow.md) for the full loop, or
[Migrations overview](../migrations/index.md) to start injecting real data.
