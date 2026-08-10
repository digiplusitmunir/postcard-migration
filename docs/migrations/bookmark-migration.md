# Bookmark Migration

Everything about migrating legacy Strapi `bookmarks` into new `circles`
rows — `owned_type='postcard'`, `relationship='bookmark'` (tracker row
**#18**). This is the **first use of the universal Circle relationship
layer**, which replaces Bookmark and all the legacy Follow* tables.
Executed by `scripts/bookmark.py` (step 11 of `scripts/migrate_data.py`);
the same logic lives in `notebooks/bookmark_migration.ipynb` for
interactive runs.

## Dependencies

A bookmark consumes both per-environment map files produced by earlier
steps (suffix from the DB name in `DATABASE_URL`):

- `legacy_user_id_map_*.json` (user migration) — `bookmark.user` →
  `circles.user_id`.
- `legacy_postcard_id_map_*.json` (postcard migration) —
  `bookmark.postcard` → `circles.owned_id`.

No schema changes needed — Circle already carries every field this
migration wants.

## Field mapping — Bookmark

Legacy `api::bookmark.bookmark` → new `circles`.

| Legacy field | Type | New column | Notes |
|---|---|---|---|
| `user` | relation | `user_id` (FK) | via the user id map; unmapped users (deleted/skipped in #12) → skipped + printed |
| `postcard` | relation | `owned_id` + `owned_type='postcard'` | via the postcard id map; unmapped postcards (**Designer Tours**, skipped in #16) → skipped + printed |
| — | | `relationship` | constant `'bookmark'` |
| `createdAt` | timestamp | `added_at` | when the member saved it — the one timestamp carried over; falls back to `now()` if legacy has none |
| `updatedAt` | timestamp | — | **dropped** — meaningless for a bookmark row |

`sequence_date` and `source_enquiry_id` stay NULL — those belong to booked
journeys inside a forked Journey, not bookmarks.

### Duplicates and orphans

- Orphan bookmarks (no user or no postcard relation in legacy) are skipped
  → printed list.
- Legacy **duplicate (user, postcard) pairs collapse** into one row via the
  Circle unique key `(user_id, owned_type, owned_id, relationship)`.
  Processing is id-sorted with `ON CONFLICT DO NOTHING`, so the **earliest**
  bookmark's `created_at` wins — deterministic across re-runs.

## Output artifact

None — nothing downstream references legacy bookmark ids, so no id map file
is written.

## Idempotency

`ON CONFLICT DO NOTHING` on the Circle unique key. Safe to re-run; re-runs
never touch rows that already exist (bookmarks added in the new app are
never overwritten).

## What needs manual work — checklist

1. **Unmapped users** — bookmarks of users that didn't migrate; expected
   for deleted accounts, anything else means the user migration is stale.
2. **Designer Tours bookmarks** — postcards skipped in #16 take their
   bookmarks with them; **re-run this step after the dx-card migration
   (#13)** extends the postcard id map so those bookmarks re-attach.
3. **Orphans** — legacy rows with a missing relation; verify they're junk
   before the legacy CMS goes away.

## Verification

The script ends with circle totals, bookmark counts, distinct
users/postcards, an **app-level broken-reference check** (Circle's
polymorphic `owned_id` has no DB-level FK — this query must return 0) and a
check that `added_at` was actually carried over rather than defaulted.

## Run order

```text
... → scripts/postcard.py → ... → scripts/bookmark.py
```

Must run **after** the user and postcard migrations (their map files are
hard prerequisites — it fails fast if either is missing). Or just run
`python scripts/migrate_data.py`, which sequences everything and stops on
the first failure.
