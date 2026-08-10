# Company Migration

Everything about migrating legacy Strapi `companies` into the new `companies`
table. Executed by `scripts/company.py` (step 4 of
`scripts/migrate_data.py`); the same logic lives in
`notebooks/media_usertypes_companies_migration.ipynb` for interactive runs.

## Field mapping — Company

Legacy `api::company.company` → new `companies`.

| Legacy field | Type | New column | Notes |
|---|---|---|---|
| `name` | string | `name` | trimmed; companies without a name are skipped → printed list |
| — | | `slug` (unique) | **missing in legacy — generated** by slugify(name), de-duplicated (`acme`, `acme-2`, ...). Processing is sorted by legacy id so suffixes stay stable across re-runs |
| `website` | string | `website` | empty strings become NULL |
| `icon` | media | `icon_media_id` (FK → `media`) | **kept** — column added by schema migration `add-company-icon`. The icon's file finds-or-creates a `media` row by url (reusing what `media.py` inserted) |
| — | | `contact_email` / `contact_phone` | **NULL** — nothing to map in legacy |
| — | | `status` | set to `active` — these are existing live companies; the schema default `pending` is for new self-signups |
| `users` | oneToMany relation | — | FK lives on the user side; Partner ↔ Company linking happens via `user_roles.company_id` in the user/content migration |
| `albums` | oneToMany relation | — | becomes `collections.managed_by_company_id` in the content migration |
| `follow_companies` | relation | — | **dropped** — legacy social/follow feature not in the new model |
| `createdAt/updatedAt`, `createdBy/updatedBy` | Strapi housekeeping | — | dropped |

## Idempotency

Upsert on `slug` (`ON CONFLICT (slug) DO UPDATE` for name, website and
icon). Icon media rows are found-or-created by url, so re-runs never
duplicate them. Safe to re-run.

## What needs manual work — checklist

1. **Contact details** — `contact_email` / `contact_phone` are NULL for every
   migrated company; fill them in by hand (legacy never stored them).
2. **Status review** — everything lands as `active`; suspend or demote to
   `pending` case by case if some legacy companies are defunct.
3. **Slug collisions** — two legacy companies with the same name get
   `name`, `name-2` slugs; review the generated suffixes for anything
   customer-facing.
4. **Skipped companies** — the script prints legacy ids skipped for having no
   name; decide whether they are junk rows or need manual entry.
5. **Partner linking** — `user_roles.company_id` is not set here; the user
   migration assigns roles and the partner ↔ company link is completed there
   (match legacy `user.company`).

## Run order

```text
... geo  →  scripts/media.py  →  scripts/company.py
```

Company must run **after** `media.py` (so icons reuse existing media rows —
it still works standalone, inserting any missing icon urls itself) and
**before** the user migration completes partner ↔ company links. Or just run
`python scripts/migrate_data.py`, which sequences everything and stops on the
first failure.
