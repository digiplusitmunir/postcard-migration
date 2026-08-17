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
- **seed** — the `city-guide` cluster type row **and its
  `collection_type_ids`** (the script asserts both and fails fast otherwise).

Schema prerequisites: migration
`20260810080000_add_cluster_cover_and_community_link` added `cover_media_id`
and `community_link` to `collection_clusters`;
`20260811090000_add_cluster_type_collection_type_ids` added
`collection_type_ids` to `collection_cluster_types`.

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

## What a cluster type is a cluster OF

`collection_cluster_types.collection_type_ids` (`BIGINT[]`, added 2026-08-11 by
migration `20260811090000_add_cluster_type_collection_type_ids`) declares which
collection types a kind of cluster groups. **City Guide is a cluster of
Restaurants + Events + Shopping**:

| Cluster type | `collection_type_ids` → | Held as |
|---|---|---|
| City Guide (`city-guide`) | Restaurants, Events, Shopping | `entry_type='postcard'` — those types have no Collection layer |

Array **order is display order**, so `[restaurants, events, shopping]` is the
order a guide should render its sections in. It is a plain id array, not an FK
join table: read it with `= ANY(...)`, and remember nothing stops a deleted
collection type from leaving a dangling id (the ids come from `scripts/seed.py`,
so in practice they track `COLLECTION_TYPES`).

Seeded by `scripts/seed.py` from the 4th element of `COLLECTION_CLUSTER_TYPES`:

```python
# name, slug, priority, collection_type_slugs
COLLECTION_CLUSTER_TYPES = [
    ("City Guide", "city-guide", 1, ["restaurants", "events", "shopping"]),
]
```

Slugs are resolved to ids in list order (`unnest(...) WITH ORDINALITY`), and the
seed **fails loudly** if a slug doesn't resolve, so a typo can't silently
shrink a cluster type's scope.

### Design decision — geo-derived entries, scoped by the cluster type

Legacy city-guides carry **no explicit restaurant/postcard links** — the
legacy frontend listed content by region. The migration reproduces that
behaviour, but only for content the cluster type actually clusters: with
`DERIVE_ENTRIES = True` (script default; notebook section 4, marked OPTIONAL),
everything **live in the guide's region whose collection type is in
`collection_type_ids`** becomes an entry at `priority 0`:

| Source | Entry |
|---|---|
| live `collections` of an in-scope type in the region | `entry_type='collection'` |
| live `postcards` of an in-scope type in the region with `collection_id IS NULL` | `entry_type='postcard'` |

For City Guide today that means **all entries are postcards** — Restaurants,
Events and Shopping live in `postcards` since the
[album split](directory-album-migration.md#the-album-split-collections-vs-postcards),
and **Properties collections are no longer derived** because Properties is not
in the City Guide scope.

- `ON CONFLICT DO NOTHING` — hand-curated additions survive re-runs, and
  rows are only ever **added, never removed**;
- set `DERIVE_ENTRIES = False` (or skip the notebook cell) to keep clusters
  empty for hand-curation;
- postcards that hang off a Properties collection are still **not** derived
  (`collection_id IS NULL` filter) — they would duplicate their parent
  collection; add them per-guide in the CMS if wanted;
- widening a cluster type is a one-line seed change: add a collection type slug
  and re-run `seed.py`, then re-run this step;
- the script **aborts** if `collection_type_ids` is empty for `city-guide` —
  that means `seed.py` hasn't run and nothing could be derived.

!!! warning "Entries left over from a wider scope"
    Derivation never deletes, so entries created before the scope existed can
    sit outside it. The verification step counts them under
    **`out-of-scope entries`** and lists the first 20 with cluster + type names.
    In prod that is **7 Properties collection entries** (Goa 4, Jaipur 2,
    Kolkata 1) from earlier runs — prune them, or add `properties` to the City
    Guide scope if they are wanted:

    ```sql
    DELETE FROM collection_cluster_entries e
     USING collection_clusters cc, collection_cluster_types cct, collections c
     WHERE e.cluster_id = cc.id AND cct.id = cc.cluster_type_id
       AND e.entry_type = 'collection' AND c.id = e.entry_id
       AND NOT (c.collection_type_id = ANY(cct.collection_type_ids));
    ```

!!! warning "Re-migrating over a pre-split database"
    A DB migrated before the album split holds `entry_type='collection'` rows
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
3. **Derived entries** — review the per-guide collection/postcard counts in the
   verification output; prune or re-prioritize in the CMS (derivation never
   deletes).
4. **Out-of-scope entries** — `out-of-scope entries` should be 0; in prod it is
   7 (Properties collections from pre-scope runs). Prune them with the SQL
   above, or widen the City Guide scope if they belong.
5. **Cluster type scope** — confirm the printed
   `cluster type 'city-guide' is a cluster of: …` line matches what the product
   wants before trusting the derived entries.
6. **Follow-city-guides** — run with tracker #24 once the Circle 'follow'
   relationship value lands; consumes the id map written here.
7. **'Todo' place type** — open decision from the tracker, unresolved.

## Verification

The script ends with the cluster-type scope line, cluster counts,
field-coverage totals (city / region / country / cover / community link /
live), entry counts split by `entry_type`, the out-of-scope entry count and
list, a duplicate-slug check and a per-guide `collection / postcard` entry
listing.

Expected (prod, 2026-08-11): 9 live city guides, all with city/region/country
and a cover; **602 entries — 595 postcard, 7 collection**; the 7 collection
rows are the out-of-scope Properties leftovers. Per guide: Bengaluru 151,
Mumbai 90, Delhi NCR 85, Kolkata 67, Goa 55, Hyderabad 50, Jaipur 47,
Mysuru 25, Pondicherry 25.

## Run order

```text
... → scripts/postcard.py → scripts/journey.py → scripts/cityguide.py
```

Needs geo/media/directory-album data in the DB (and seed for the cluster
type) but no map files — it is sequenced last so derived entries see the full
set of live collections **and** the album-derived postcards. Or just run
`python scripts/migrate_data.py`, which sequences everything and stops on
the first failure.
