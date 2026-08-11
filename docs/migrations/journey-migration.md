# Journey Migration

Everything about migrating legacy Strapi `property_itineraries` into the new
`subcollections` table (SubcollectionType **Journey** under Properties),
including the ordered **`subcollection_postcards`** join (tracker row
**#31**). Executed by `scripts/journey.py` (step 9 of
`scripts/migrate_data.py`); the same logic lives in
`notebooks/journey_migration.ipynb` for interactive runs, which also carries
the optional author-circles step (notebook only).

## Dependencies — why this runs after postcards

A journey consumes both per-environment map files produced by earlier steps
(suffix from the DB name in `DATABASE_URL`):

- `legacy_album_id_map_*.json` (directory/album migration) —
  `property_itinerary.album` → `collection_id`, the **required** parent
  Property of every journey. Since 2026-08-11 this map holds only albums that
  became **collections**; Restaurants/Events/Shopping albums are postcards and
  are therefore absent, so an itinerary hanging off one is skipped (a Journey
  needs a real Collection parent).
- `legacy_postcard_id_map_*.json` (postcard migration) — each entry of the
  `postcards` many-to-many → one `subcollection_postcards` row.

The `journey` subcollection type itself comes from `scripts/seed.py`
(the script asserts it exists and fails fast otherwise). Schema prerequisite:
migration `20260810060000_add_subcollection_cover_and_days` added
`cover_media_id` and `number_of_days` to `subcollections`.

## Field mapping — Journey

Legacy `api::property-itinerary.property-itinerary` → new `subcollections`.

| Legacy field | Type | New column | Notes |
|---|---|---|---|
| `title` | text | `name` | trimmed; itineraries without a title are skipped → printed list |
| `description` | text | `intro` | trimmed; empty → NULL |
| `dayWiseItinerary` | richtext (markdown) | `story` | stored as markdown verbatim — render with a markdown component on the frontend |
| `termsAndConditions` | richtext (markdown) | `tour_info` | same — markdown verbatim |
| `slug` | UID | `slug` (unique) | from legacy slug else slugify(title); de-duplicated in-run (`foo`, `foo-2`, ...) — id-sorted so suffixes stay stable across re-runs |
| `album` | oneToOne | `collection_id` (FK, **required**) | via the album id map; itineraries whose album is **not a collection** are skipped — **no album**, a **Designer Tours** album (→ dx-card migration, tracker #11/#13), or an album of a **non-dedicated type** (Restaurants/Events/Shopping, which are postcards now — 0 in prod, 1 in dev) |
| `price` | integer | `price` | `priceType` context dropped (below) |
| `numberOfNights` | integer | `number_of_nights` | |
| `numberOfDays` | integer | `number_of_days` | column added 2026-08-10 |
| `coverImage` | media | `cover_media_id` (FK → `media`) | column added 2026-08-10; find-or-create by normalized url (reuses `media.py` rows, never duplicates) |
| `best_time_to_visits` | oneToMany (months) | `best_months` (JSON) | array of month names, legacy order kept |
| `status` | enum | `status` | `deckFreeze` / `onTrip` / `complete` → `live`; `deckBuild` / `draft` / empty → `draft`; per-value counts printed for review |
| — | | `managed_by_company_id` (FK) | inherited from the parent collection |
| `postcards` | manyToMany | `subcollection_postcards` rows | `sequence_order` = position in the legacy relation order (Day 1, Day 2, ...) — see below |
| `createdByUser` | relation | Circle `author` (`owned_type='subcollection'`) | **notebook-only optional step** (needs the per-env legacy user id map) |
| `priceType` | enum | — | **dropped — no v2 home**; v2 `price` is documented as avg-price-per-person, so non-default (`twin sharing`) rows are printed for manual review |
| `country` | relation | — | **dropped** — subcollections carry no geo; inherited implicitly from the parent Property collection |
| `createdAt/updatedAt/publishedAt`, `createdBy/updatedBy` | Strapi housekeeping | — | dropped — no timestamp columns on subcollections |

`price_starting_at`, `guests_min` and `guests_max` stay NULL — no legacy
source (they exist for the Album→Subcollection split, tracker #14).

### The postcard join and its invariant

The schema documents an app-level invariant: a joined postcard's
`collection_id` must equal the journey's `collection_id` (a journey can only
sequence postcards of its own Property). The migration enforces it:

- postcards **missing from the postcard id map** (skipped in #16 as Designer
  Tours) are flagged → printed list;
- postcards belonging to a **different collection** than the journey are
  **skipped** → printed list for manual review;
- `sequence_order` numbers only the inserted rows (1, 2, 3, ... with no gaps),
  and re-runs refresh it via upsert on the `(subcollection_id, postcard_id)`
  primary key.

The verification step ends with an invariant-violation query that must
return 0.

## Output artifact — legacy itinerary id map

The script writes `legacy_itinerary_id_map_dev.json` / `_prod.json` (legacy
property-itinerary id → new subcollection id) to the repo root — the future
Enquiry (#27) and Circle/booking migrations need it. Suffix picked
automatically from the DB name in `DATABASE_URL`.

## Idempotency

Subcollections upsert on `slug`; join rows upsert on their composite PK
(refreshing `sequence_order`); cover media rows are found-or-created by url.
Safe to re-run.

## What needs manual work — checklist

1. **Skipped itineraries** — no-album and Designer Tours lists are printed;
   Designer Tours is expected (dx-card migration later), anything else needs
   a look.
2. **`priceType` = twin sharing** — dropped field; the printed rows carry a
   price whose semantics differ from per-person. Decide whether to adjust
   those prices or add a facet/field before the legacy CMS goes away.
3. **Cross-collection postcards** — join rows skipped for the invariant;
   decide per case whether the postcard should move Property or be dropped
   from the journey.
4. **Status review** — the printed per-value counts show how many
   deckBuild/deckFreeze/onTrip itineraries landed on each side of the
   live/draft line.
5. **Author circles** — run notebook section 6 when circle work unblocks.

## Verification

The script ends with journey counts, field-coverage totals (price / nights /
days / cover / best_months / company / live), join-row counts, empty
journeys, a duplicate-slug check and the collection-invariant check —
compare against the source CMS counts for the environment being migrated.

## Run order

```text
... → scripts/directory_album.py → scripts/postcard.py → scripts/journey.py
```

Must run **after** the directory/album and postcard migrations (their map
files are hard prerequisites — it fails fast if either is missing). Or just
run `python scripts/migrate_data.py`, which sequences everything and stops on
the first failure.
