# 00 — Cross-cutting changes

Changes that are not owned by any single script but land on several tables at
once. Every per-table file references back here.

---

## X1. Geo tier removal (R1, tracker 2026-08-05)

> "GEO CHANGE 2026-08-05: City tier REMOVED — 3-tier Country/Region/Locality,
> disambiguated via Locality.google_place_id; City Guide re-anchors to Region."

Target hierarchy: `Country → Region → Locality`.

### Schema

| Action | Target |
|---|---|
| **Delete model** | `City` |
| **Drop column** | `collections.city_id` |
| **Drop column** | `postcards.city_id` |
| **Drop column** | `collection_clusters.city_id` |
| **Drop column** | `users.city_id` |
| **Drop column** | `memories.city_id` |
| **Drop column** | `localities.city_id` |
| **Add column** | `localities.region_id` (BigInt, required, FK → `regions.id`) |
| **Add column** | `localities.google_place_id` (String, **unique**) |
| **Add column** | `localities.lat` / `localities.lng` (Decimal(9,6), nullable) — already present, keep |
| **Drop constraint** | `localities @@unique([name, cityId])` |
| **Add constraint** | `localities @@unique([google_place_id])` |
| **Drop relation** | `City[]` back-relations on `Country`? — no, `City` hangs off `Region`; remove `Region.cities`, and every `City[]` back-relation on Collection/Postcard/CollectionCluster/User/Memory/Locality |

Note the `lat`/`lng` that currently live on `City` (centroid for map default
zoom) have no home once `City` is gone — `Region` has no `lat`/`lng`. If the map
still needs a region centroid, add `regions.lat` / `regions.lng`. **Flagging as
an unlisted gap in the tracker.**

### Locality uniqueness changes meaning

Old: `Unique(name, city_id)` — name was the key.
New: `google_place_id` is the key; `name` is a display label only.

> "this is the place_id of the neighborhood/sublocality itself — a DIFFERENT,
> coarser place_id than the one on each Collection/Postcard's own Location
> Component (which identifies that specific building/address). Both exist, at
> different levels."

`google_place_id` has **no v1 source** — it comes from the Gmap Address
Enrichment workstream. So the migration cannot enforce the unique key on first
load. Plan: load with `google_place_id` NULL, enrich, then add the unique
constraint in a follow-up migration.

### Script impact

- `geo_migration.py` — **the placeholder-city block is deleted outright**
  (lines 116–125 synthesize one city per region; lines 142–151 then parent
  localities to that fake city). Localities parent straight to Region by name.
- `cityguide.py` — the entire "legacy region → v2 city" matching path
  (`cities_by_name`, `city_missing`, `city_ambiguous`) is deleted. See [10](10-cityguide.md).
- `directory_album.py`, `postcard.py` — remove `city_id` from the INSERT column
  lists (both already pass literal `NULL`, so this is cosmetic but should go).
- `users.py` — the `MANUAL REVIEW — free-text city to resolve to city_id` list
  becomes moot; free-text `city` maps to `location.city_name` instead (see X2)
  or is archived.

---

## X2. Location component (tracker: *(cross-cutting) Location Component*)

Embedded on `Collection`, `Postcard`, `CollectionCluster`. Currently a
free-form `Json?` field written ad-hoc by `directory_album.py` as
`{lat, lng, google_place_id, location_link}`.

### Target shape

| Key | v1 source | Note |
|---|---|---|
| `address` | `formatted_address` | Google's full formatted string, kept as-is for display |
| `street_number` | *(new)* | From Google `address_components` |
| `route` | *(new)* | Street name |
| `subpremise` | *(new, optional)* | Unit/apt/suite, when Google returns one |
| `postal_code` | *(new)* | From `address_components` |
| `admin_area_level_2` | *(new, optional)* | County/district — **reference only, NOT a geo tier** |
| `city_name` | v1 `locality` | **Free text, NOT a foreign key.** Since City is no longer a tier this is informational display text only |
| `lat` / `lng` | *(no v1 source)* | Derived by geocoding the country/region/locality relations |
| `google_place_id` | `place_id` | Building/address-level — distinct from `Locality.google_place_id` |

Fields that route to the geo **tables**, not the component:
`administrative_area_level_1 → Region.name`,
`sublocality / neighborhood → Locality.name`,
`country → Country.name`.

### Schema decision

Keep as `Json?` (Prisma cannot express a reusable embedded component), but
document the shape in a schema comment and validate it at the service layer.
No column change needed — this is a **write-shape** change in the scripts.

### Script impact

- `directory_album.py` line 321 currently emits `location_link`, which is **not
  in the target shape** — it is a legacy Strapi field with no target. Either map
  it into the component as a documented extension or drop it. Currently it is
  silently carried.
- Nothing populates `address`, `street_number`, `route`, `subpremise`,
  `postal_code`, `admin_area_level_2`, `city_name` today. All are marked
  "Transform" in the tracker but most have no v1 source — they are Gmap
  Address Enrichment outputs. **These stay empty at migration time.**

---

## X3. Stay Details component (R5, tracker 2026-08-12 CORRECTION)

Attaches to `Subcollection` (Journey), "and elsewhere as needed".

> "CORRECTION 2026-08-12: real v1 pattern is ONE price field + a priceType enum
> ('per person'/'twin sharing') — NOT two separate price columns as the earlier
> (incorrect, pre-real-schema) Album draft assumed. CONFIRMED: the '2nd price'
> display value is CALCULATED via a formula off the stored price at
> read/display time — no separate v1 data needed for it."

### Target shape

| Field | v1 source | Disposition |
|---|---|---|
| `number_of_days` | `numberOfDays` | Direct |
| `number_of_nights` | `numberOfNights` | Direct |
| `price` | `price` | Direct — **single** price field |
| `price_type` | `priceType` | Transform → enum `per_person` / `twin_sharing` |
| `best_months` | `best_time_to_visits` (oneToMany → Month entity) | Transform — iterate the relation |
| `number_of_rooms` | *(new)* | No v1 source |
| `guests_per_room` | *(new)* | No v1 source. Angel's "number of persons per room" lives here |

### Schema impact on `subcollections`

| Action | Column | Reason |
|---|---|---|
| **DROP** | `price_starting_at` | Built on the retracted dual-price assumption. Reverts migration `20260806060000_add_subcollection_price_starting_at` |
| **DROP** | `guests_min` | Replaced by `number_of_rooms` + `guests_per_room` |
| **DROP** | `guests_max` | Same |
| **ADD** | `price_type` (enum `PriceType`) | Was being **dropped on the floor** by `journey.py` |
| **ADD** | `number_of_rooms` (Int?) | New, no v1 source |
| **ADD** | `guests_per_room` (Int?) | New, no v1 source |
| **KEEP** | `price`, `number_of_nights`, `number_of_days`, `best_months` | Already correct |

`journey.py` currently **discards `priceType`** and only prints non-default rows
for review (lines 200–201, and the `twin_sharing` manual-review list). Once
`price_type` exists, that data is migrated instead of reported.

---

## X4. Ownership is a direct FK, not a Circle (R3, tracker 2026-08-12)

> "OWNERSHIP CHANGE 2026-08-12: Circle is reserved for follow/bookmark
> engagement only — ownership/assignment (user/assignTo) fields are direct FKs,
> not Circle."

### New columns

| Table | Column | v1 source | Meaning |
|---|---|---|---|
| `collections` | `owner_user_id` | Album `user` | Who the property belongs to |
| `collections` | `assigned_to_user_id` | Album `assignTo` | Who works on / edits the content |
| `postcards` | `user_id` | Postcard `user` | Author |
| `subcollections` | `created_by_user_id` | Property-itinerary `createdByUser` | Author |
| `enquiries` | `assigned_to_user_id` | *(new)* | Concierge staff handling it |

All nullable, FK → `users.id`.

### Enum change

`CircleRelationship` loses three values:

```
enum CircleRelationship {
  author           // DELETE — now Postcard.user_id / Subcollection.created_by_user_id
  assigned_staff   // DELETE — now Collection.assigned_to_user_id
  owner            // DELETE — now Collection.owner_user_id
  bookmark         // keep
  booked           // keep
}
```

### Script impact

The "optional author/assigned_staff circles" sections that live only in the
notebooks (`directory_album_migration.ipynb` §6, `postcard_migration.ipynb` §6,
`journey_migration.ipynb` §6) are now **wrong** and must be replaced with a
direct-FK write in the `.py` scripts. Per the repo rule, notebook changes go out
as paste-able cell snippets, not direct edits.

`directory_album.py`, `postcard.py`, `journey.py` each need the legacy
`user` / `assignTo` / `createdByUser` relation resolved through
`legacy_user_id_map{_dev,_prod}.json` (already produced by `users.py`) and
written into the new column.

---

## X5. Circle consolidation (R4, tracker 2026-08-12)

> "CIRCLE CONSOLIDATION 2026-08-12: Bookmark + all 6 Follow-* tables collapse
> into ONE relationship='bookmark' value, differentiated only by owned_type."

No new enum values — `CircleOwnedType` already has all seven targets
(`postcard`, `collection`, `subcollection`, `collection_cluster`, `tag`,
`company`, `user`). **No schema change to the enum.**

### Required index

> "QUERY PATTERN LOCKED 2026-08-12: profile-page 'saved items' queries (e.g.
> Travel Diary) filter Circle by (user_id, owned_type) — needs a composite index
> on Circle(user_id, owned_type) to stay fast."

Current indexes are `(user_id, relationship, owned_type)` and
`(owned_type, owned_id)`. The existing three-column index does **not** serve
`(user_id, owned_type)` because `relationship` sits between them.

**ADD** `@@index([userId, ownedType])` on `Circle`.

### Migration mapping

| v1 table | `owned_type` | `relationship` |
|---|---|---|
| `bookmarks` | `postcard` | `bookmark` |
| `follows` | `user` | `bookmark` |
| `follow_albums` | `collection` | `bookmark` |
| `follow_companies` | `company` | `bookmark` |
| `follow_tags` | `tag` | `bookmark` |
| `follow_city_guides` | `collection_cluster` | `bookmark` |
| `follow_affiliates` | `collection_cluster` | `bookmark` |

Note the last two both land on `collection_cluster`. That is intentional per the
tracker, but it means a City Guide follow and an Affiliation follow are
indistinguishable in `circles` unless the cluster's own `cluster_type_id`
disambiguates them. It does — no data loss.

---

## X6. Media identity (tracker: *Upload - File → Media*)

> "-> Media (confirmed 2026-08-05: exact match, no field changes)"
> "id (numeric) → id (UUID). Build and retain a permanent old-numeric-ID →
> new-UUID mapping table."

The current `Media` model is described in the schema header as a "minimal stub".
It is **not** an exact match — it keeps only 5 of the 12 mapped fields. See
[03-media.md](03-media.md) for the full column list.

**Decision D2** — the UUID switch is the single most expensive item in this
plan. `media.id` is referenced by 8 relations across 6 tables. Recommend
**keeping `BigInt`** and satisfying the tracker's real requirement (a permanent
legacy-id mapping) with a `media.legacy_id` column, unless the UUID is a hard
external requirement.
