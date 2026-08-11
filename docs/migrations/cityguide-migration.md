# City Guide Migration

Everything about migrating legacy Strapi `city_guides` into the new
`collection_clusters` table under CollectionClusterType **City Guide**
(tracker row **#17**), including the geo-derived
**`collection_cluster_entries`** step. Executed by `scripts/cityguide.py`
(step 10 of `scripts/migrate_data.py`); the same logic lives in
`notebooks/cityguide_migration.ipynb` for interactive runs.

## Dependencies

No per-env map files are consumed — everything resolves against the DB:

- **geo migration** — cities are the match target (see below) and supply
  region/country fallbacks;
- **media migration** — covers find-or-create against `media` by url;
- **directory/album migration** — only for the derived-entries step (entries
  point at `collections` rows, and at the album-derived `postcards` rows for
  the non-dedicated types);
- **seed** — the `city-guide` cluster type row (the script asserts it exists
  and fails fast otherwise).

Schema prerequisite: migration
`20260810080000_add_cluster_cover_and_community_link` added
`cover_media_id` and `community_link` to `collection_clusters`.

## The central mapping decision — legacy region → v2 city

v2 cities were **synthesized 1:1 from legacy regions** during the geo
migration, so a legacy city-guide's `region` relation is matched against
`cities.name` (case-insensitive):

- `city_id` = the matched city;
- `region_id` = that city's parent region;
- `country_id` = legacy `country` by name, falling back to the matched
  region's country;
- region names matching **no** v2 city or **multiple** v2 cities leave the
  geo columns NULL → printed manual-review lists (no guessing).

## Field mapping — City Guide

Legacy `api::city-guide.city-guide` → new `collection_clusters`.

| Legacy field | Type | New column | Notes |
|---|---|---|---|
| *(none)* | — | `name` | **legacy has no name field** — derived from the matched city's name; guides without a region fall back to a title-cased slug |
| `slug` | UID | `slug` (unique) | legacy slug else slugify(name); de-duplicated in-run (`foo`, `foo-2`, ...) — id-sorted so suffixes stay stable across re-runs |
| `region` | relation | `city_id` + `region_id` (FKs) | **mapped to the cities tier** — see above |
| `country` | relation | `country_id` (FK) | by name; falls back to the matched region's country; misses printed for review |
| `description` | text | `intro` | trimmed; empty → NULL; `story` stays NULL (no legacy source) |
| `image` | media | `cover_media_id` (FK → `media`) | column added 2026-08-10; find-or-create by normalized url (reuses `media.py` rows, never duplicates) |
| `communityLink` | string | `community_link` | column added 2026-08-10 (WhatsApp/community URL) |
| `status` | enum (`draft`/`published`) | `status` | `published` → `live`, else `draft`; per-value counts printed |
| — | | `locality_id`, `managed_by_company_id` | stay NULL (managed_by is for Partner Affiliation clusters) |
| `follow_city_guides` | relation | — | deferred → tracker #24 (Circle `owned_type=collection_cluster`), blocked on the 'follow' relationship value |
| `createdAt/updatedAt/publishedAt`, `createdBy/updatedBy` | Strapi housekeeping | — | dropped — no timestamp columns on clusters |

### Design decision — geo-derived entries

Legacy city-guides carry **no explicit restaurant/postcard links** — the
legacy frontend listed content by region. The migration reproduces that
behaviour: with `DERIVE_ENTRIES = True` (script default; notebook section 4,
marked OPTIONAL), everything **live in the guide's region** becomes a
`collection_cluster_entries` row at `priority 0` (re-order in the CMS later):

| Source | Entry |
|---|---|
| live `collections` in the region | `entry_type='collection'` |
| live `postcards` in the region with `collection_id IS NULL` **and** a non-dedicated type | `entry_type='postcard'` |

The postcard branch was added 2026-08-11 with the
[album split](directory-album-migration.md#the-album-split-collections-vs-postcards):
Restaurants/Events/Shopping used to be collections and were picked up by the
first branch alone, so without it every guide would lose its
restaurant/shopping/event entries.

- `ON CONFLICT DO NOTHING` — hand-curated additions survive re-runs, and
  rows are only ever **added, never removed**;
- set `DERIVE_ENTRIES = False` (or skip the notebook cell) to keep clusters
  empty for hand-curation;
- postcards that hang off a Properties collection are still **not** derived —
  they would duplicate their parent collection; add them per-guide in the CMS
  if wanted.

!!! warning "Re-migrating over a pre-split database"
    A DB migrated before the split holds `entry_type='collection'` rows
    pointing at the old Restaurants/Shopping/Events collections (588 in prod).
    `scripts/directory_album.py` aborts on them rather than cascading — delete
    them with the SQL it prints, then re-run this step to get the equivalent
    `entry_type='postcard'` rows.

The tracker's *"'Todo' place type has no v2 home yet"* note remains an open
product decision — nothing here resolves it.

## Output artifact — legacy city-guide id map

The script writes `legacy_cityguide_id_map_dev.json` / `_prod.json` (legacy
city-guide id → new cluster id) to the repo root — the follow-city-guide
migration (#24) needs it. Suffix picked automatically from the DB name in
`DATABASE_URL`.

## Idempotency

Clusters upsert on `slug`; entries insert with
`ON CONFLICT (cluster_id, entry_type, entry_id) DO NOTHING`; cover media
rows are found-or-created by url. Safe to re-run.

## What needs manual work — checklist

1. **City misses/ambiguities** — region names that matched no (or multiple)
   v2 cities left geo NULL; fix the names or set the FKs by hand.
2. **Guides with no region** — printed list; they also fall back to a
   slug-derived name worth reviewing.
3. **Derived entries** — review per-guide entry counts in the verification
   output; prune or re-prioritize in the CMS (derivation never deletes).
4. **Follow-city-guides** — run with tracker #24 once the Circle 'follow'
   relationship value lands; consumes the id map written here.
5. **'Todo' place type** — open decision from the tracker, unresolved.

## Verification

The script ends with cluster counts, field-coverage totals (city / region /
country / cover / community link / live), entry counts, a duplicate-slug
check and a per-guide entry listing — compare against the source CMS counts
for the environment being migrated.

## Run order

```text
... → scripts/postcard.py → scripts/journey.py → scripts/cityguide.py
```

Needs geo/media/directory-album data in the DB (and seed for the cluster
type) but no map files — it is sequenced last so derived entries see the full
set of live collections **and** the album-derived postcards. Or just run
`python scripts/migrate_data.py`, which sequences everything and stops on
the first failure.
