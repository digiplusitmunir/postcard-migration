# Geo Migration

Everything about migrating the location entities from legacy Strapi to the new
4-tier geo hierarchy. Executed by `notebooks/geo_migration.ipynb`.

## The structural change

```text
LEGACY:   country ──< region ──< locality          (no City tier, 3 levels)
NEW:      countries ──< regions ──< cities ──< localities   (4 levels)
```

The new tier exists to kill name collisions the legacy system suffered from
(same city name in two countries, same locality name in two cities — e.g.
"Indira Nagar" in both Mumbai and Bangalore). Legacy uniqueness was **global**
per table; new uniqueness is **scoped to the parent**.

## Field mapping — Country

Legacy `api::country.country` → new `countries`.

| Legacy field | Type | New column | Notes |
|---|---|---|---|
| `name` | string | `name` (unique) | trimmed |
| `slug` | uid | `slug` (unique) | generated from name when legacy slug is empty |
| `code` | string | — | **dropped** — no column in new schema; add one if ISO codes are needed |
| `otherNames` | component (repeatable) | — | **dropped** — alternative names have no home yet |
| `continent` | enum (AF/AS/AN/EU/NA/OC/SA) | — | **dropped** |
| `coverImage` | media | — | **dropped** — country imagery not in new model |
| `regions` | relation | — | handled by the Region step (FK direction reversed) |
| `memories`, `city_guides` | relations | — | migrated later with Memory / CollectionCluster |
| `createdAt/updatedAt/publishedAt`, `createdBy/updatedBy` | Strapi housekeeping | — | dropped |

## Field mapping — Region

Legacy `api::region.region` → new `regions`.

| Legacy field | Type | New column | Notes |
|---|---|---|---|
| `name` | string, **globally unique** | `name` — unique per `(name, country_id)` | trimmed |
| — | | `slug` | **missing in legacy — generated** by slugify(name) |
| `country` | manyToOne relation | `country_id` (FK, required) | looked up by country name; regions **without a country are skipped** → manual review list in the notebook |
| `albums`, `memories`, `city_guides`, `locality` | relations | — | migrated with their own entities |

## City — synthesized (nothing to map)

No legacy entity exists. The notebook creates **one placeholder city per
region**, named and slugged after the region itself, so localities have a
valid parent.

| New column | Value | Manual work |
|---|---|---|
| `region_id` | the region | — |
| `name` / `slug` | copied from the region | ⚠️ rename placeholder cities into real cities; split localities across real cities where a region spans several |
| `lat` / `lng` | NULL | ⚠️ fill centroids manually (used for map default zoom) |

## Field mapping — Locality

Legacy `api::locality.locality` → new `localities`.

| Legacy field | Type | New column | Notes |
|---|---|---|---|
| `name` | string, **globally unique** | `name` — unique per `(name, city_id)` | trimmed |
| — | | `slug` | **missing in legacy — generated** |
| `region` | manyToOne relation | → `city_id` (FK, required) | legacy points at Region; new points at City. Attached to the region's **placeholder city**. Localities without a region are skipped → manual review list |
| — | | `lat` / `lng` | **missing in legacy** — NULL, fill manually |
| `albums` | relation | — | migrated with content |

## What needs manual work — checklist

1. **Placeholder cities**: rename each auto-created city (currently = region
   name) to a real city, or create the real cities and move localities onto
   them.
2. **City centroids** (`lat`/`lng`) — empty for every synthesized city.
3. **Locality centroids** — legacy never stored them.
4. **Orphan regions/localities** — anything in the notebook's
   `MANUAL REVIEW` lists (missing parent in legacy) must be re-parented by
   hand or discarded.
5. **Decide on dropped Country fields** — `code`, `continent`, `otherNames`,
   `coverImage`: extend the Prisma schema if any of these are still needed,
   then re-run.
6. **Duplicate-name sanity check** — legacy global uniqueness means no
   collisions on first run, but once you split placeholder cities, re-check
   locality uniqueness per city.

## Run order

```text
npm run migrate:deploy  →  python scripts/seed.py  →  notebooks/geo_migration.ipynb
```

Geo must run **before** user migration (users reference `country_id`) and
before any content migration (collections/postcards reference all four tiers).
