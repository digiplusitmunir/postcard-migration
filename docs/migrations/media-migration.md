# Media Migration

Everything about migrating the legacy Strapi upload library (`files`) into the
new `media` table. Executed by `scripts/media.py` (step 3 of
`scripts/migrate_data.py`); the same logic lives in
`notebooks/media_usertypes_companies_migration.ipynb` for interactive runs.

## Why media runs early

`media` is fully independent (no FK to any other table) and nearly everything
else references it — collection/postcard covers, user profile pics, memory
galleries, company icons. Migrating it first means every later migration can
resolve its images by url lookup.

## Source endpoint quirk

`/api/upload/files` (upload plugin) returns **flat** objects — no
`data/attributes` envelope like regular collection endpoints. Pagination
support varies by Strapi version, so the fetch loop pages with
`pagination[start]/[limit]` **and** guards against a server that ignores those
params (it stops as soon as a page returns no new ids).

## Field mapping — File

Legacy `plugin::upload.file` → new `media`.

| Legacy field | Type | New column | Notes |
|---|---|---|---|
| `url` | string | `url` | relative `/uploads/...` paths are made absolute with `CMS_BASE_URL` |
| `mime` | string | `mime_type` | |
| `alternativeText` | string | `alt` | fallback chain: `alternativeText` → `caption` → `name` |
| `caption` | string | → `alt` fallback | otherwise **dropped** |
| `name` | string | → `alt` fallback | otherwise **dropped** — no name/title column |
| `width` / `height` | int | `width` / `height` | |
| `formats` | json | — | **dropped** — Strapi's thumbnail/small/medium variants; only the original url survives |
| `hash`, `ext`, `size` | string/decimal | — | **dropped** |
| `previewUrl` | string | — | **dropped** |
| `provider`, `provider_metadata` | string/json | — | **dropped** — files stay wherever the legacy provider hosts them |
| `related` | morphToMany | — | **dropped** — each content migration re-links its own media by url lookup |
| `folder`, `folderPath` | relation/string | — | **dropped** — no folder concept in the new schema |
| `createdAt/updatedAt`, `createdBy/updatedBy` | Strapi housekeeping | — | dropped |

## Idempotency

`media.url` has **no unique constraint**, so the script does
select-then-insert on `url`: existing rows are updated in place, new urls are
inserted, and legacy duplicates (same url twice) collapse into one row. Safe
to re-run. `user_migration` and `company.py` use the same url lookup, so rows
created by any script are reused, never duplicated.

## What needs manual work — checklist

1. **File hosting** — urls still point at the legacy storage/CDN. Decide
   whether files get re-hosted; if so, rewrite `media.url` afterwards.
2. **Dropped fields** — if `size`, `formats` (responsive variants) or a
   name/title column turn out to be needed, extend the Prisma schema and
   re-run.
3. **Orphan media** — every legacy file is migrated, including ones nothing
   references. Prune unreferenced rows after the content migrations if
   desired.

## Run order

```text
npm run migrate:deploy  →  python scripts/seed.py  →  geo  →  scripts/media.py
```

Media must run **before** `company.py` (icons), the user migration (profile
pics) and every content migration (covers, galleries). Or just run
`python scripts/migrate_data.py`, which sequences everything and stops on the
first failure.
