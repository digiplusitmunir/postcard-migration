# 02 — `geo_migration.py` (step 2)

Tables: `countries`, `regions`, ~~`cities`~~, `localities`.

**This script needs the largest rewrite in the pipeline.** The City tier it
synthesizes no longer exists (see [00 — X1](00-cross-cutting.md#x1-geo-tier-removal-r1-tracker-2026-08-05)),
and `Country` gains three fields it currently ignores.

---

## `countries`

Tracker row: **Country → Country**.

| v1 field | v2 target | Disposition | Current schema | Action |
|---|---|---|---|---|
| `name` | `name` | Direct | ✅ present | **Keep** |
| `slug` | `slug` | Direct | ✅ present | **Keep** |
| `code` | `code` | Direct — *extension beyond canonical doc, confirmed intentional 2026-08-05* | ❌ **missing** | **ADD** `code` (String?, e.g. ISO-3166 alpha-2) |
| `continent` | `continent` (enum) | Transform — *extension, confirmed intentional* | ❌ **missing** | **ADD** `continent` (enum `Continent`?) — **enum values still TBD (D1)** |
| `coverImage` | `flag` (image) | Transform — *extension, confirmed intentional. ASSUMPTION: mapped from v1's coverImage* | ❌ **missing** | **ADD** `flag_media_id` (BigInt?, FK → `media.id`) |
| `otherNames` | *(no target)* | **Flag** — not in the confirmed field list | — | **Not migrated.** Archive if needed |

### Schema

```
model Country {
  id           BigInt     @id @default(autoincrement())
  name         String     @unique
  slug         String     @unique
  code         String?                              // NEW
  continent    Continent?                           // NEW — enum values TBD (D1)
  flagMediaId  BigInt?    @map("flag_media_id")     // NEW — from v1 coverImage
  flag         Media?     @relation("CountryFlag", fields: [flagMediaId], references: [id])
  ...
}
```

Requires a matching `Media.countryFlags Country[] @relation("CountryFlag")`
back-relation.

### ⚠️ Ordering problem

`Country.flag_media_id` points at `media`, but `geo_migration.py` runs at
**step 2** and `media.py` at **step 3**. Either:

- **(a)** move `media.py` ahead of `geo_migration.py` in `STEPS`, or
- **(b)** have `geo_migration.py` find-or-create its own media rows by
  normalized url — the same `media_id_for` helper every later script already
  carries.

**(b)** is more consistent with the rest of the pipeline and avoids reordering.

### Script impact

- Fetch `/api/countries` with `{"populate": "coverImage"}` — currently no
  populate, so the flag image is not even retrieved.
- Add `code` and `continent` to the INSERT and the `ON CONFLICT DO UPDATE` set.
- The `ON CONFLICT (name)` upsert key stays valid.

---

## `regions`

Tracker row: **Region → Region**.

| v1 field | v2 target | Disposition | Action |
|---|---|---|---|
| `name` / `slug` | `name` / `slug` | Direct — *"Enforce Unique(name, country_id) on load — dedupe first"* | **Keep** — `@@unique([name, countryId])` already present ✅ |
| `country` | `country_id` | Direct | **Keep** ✅ |

**No schema change** — except one unlisted consequence of X1:

⚠️ `City.lat` / `City.lng` ("centroid, for map default zoom") die with the City
model. Nothing on `Region` replaces them. If a region centroid is still needed,
**ADD** `regions.lat` / `regions.lng` (Decimal(9,6)?). Not in the tracker —
flagging as a gap.

### Script impact

Minimal. The existing region loop is correct.

---

## ~~`cities`~~ — DELETE

Tracker: *"GEO CHANGE 2026-08-05: City tier REMOVED"* and, on Locality,
*"Locality now parents directly to Region (City tier removed, was
Region→City→Locality)"*.

| Action | Target |
|---|---|
| **DELETE model** | `City` |
| **DELETE relation** | `Region.cities` |
| **DELETE back-relations** | `City.collections`, `.postcards`, `.collectionClusters`, `.users`, `.memories`, `.localities` |
| **DROP columns** | `collections.city_id`, `postcards.city_id`, `collection_clusters.city_id`, `users.city_id`, `memories.city_id`, `localities.city_id` |

### Script impact — delete this block entirely

```python
# scripts/geo_migration.py:116-125  — DELETE
with conn.cursor() as cur:
    cur.execute(
        """
        INSERT INTO cities (region_id, name, slug)
        SELECT id, name, slug FROM regions
        ON CONFLICT (name, region_id) DO NOTHING
        """
    )
    print(f"placeholder cities created: {cur.rowcount}")
conn.commit()
```

This synthesized one fake city per region purely so localities had a parent.
With X1 that scaffolding is dead — and `cityguide.py` currently *depends* on it
(it matches legacy region names against `cities.name`). See [10](10-cityguide.md).

---

## `localities`

Tracker row: **Locality → Locality (City tier REMOVED 2026-08-05)**.

| v1 field | v2 target | Disposition | Action |
|---|---|---|---|
| `name` | `name` | Direct — *"Display label — not the uniqueness key"* | **Keep**, but it stops being part of the unique key |
| `region` | `region_id` | Transform — *"Locality now parents directly to Region"* | **ADD** `region_id`, **DROP** `city_id` |
| *(new)* | `google_place_id` | Transform — *"this is now the real uniqueness/dedup key, replacing the old Unique(name, city_id)"* | **ADD**, unique |
| *(new)* | `lat` / `lng` (optional) | Transform — *"Centroid, sourced via the Gmap Address Enrichment workstream"* | ✅ already present — **Keep** |

> "CONFIRMED 2026-08-12: no direct `country_id` on Locality — Country is reached
> via `Region.country_id` (one join), not denormalized here since that's not a
> performance concern for this table."

→ **Do NOT add** `localities.country_id`.

### Schema

```
model Locality {
  id             BigInt   @id @default(autoincrement())
  regionId       BigInt   @map("region_id")          // was cityId
  name           String
  slug           String
  googlePlaceId  String?  @unique @map("google_place_id")   // NEW — the real dedup key
  lat            Decimal? @db.Decimal(9, 6)
  lng            Decimal? @db.Decimal(9, 6)
  region         Region   @relation(fields: [regionId], references: [id])
  ...
  // @@unique([name, cityId])  -- DROP
}
```

### ⚠️ The uniqueness key has no v1 source

`google_place_id` comes from Gmap enrichment, not from v1. On first load every
row would be NULL. Postgres allows multiple NULLs under a UNIQUE constraint, so
the constraint is technically satisfiable — but it enforces nothing until
enrichment runs, and the migration needs *some* idempotency key in the meantime.

**Recommended sequencing:**
1. Migrate with `@@unique([name, regionId])` as the working idempotency key
   (a direct translation of the old `(name, city_id)`).
2. Run Gmap Address Enrichment to populate `google_place_id`.
3. Follow-up migration: add `@@unique([google_place_id])`, and decide whether to
   drop `@@unique([name, regionId])` (the tracker implies yes — the same
   neighborhood name can legitimately repeat within a region).

### Script impact

Replace the locality insert (lines 142–151), which currently routes through the
placeholder city:

```python
# CURRENT — parents to the fake city
INSERT INTO localities (city_id, name, slug)
SELECT c.id, %s, %s
FROM cities c JOIN regions r ON c.region_id = r.id
WHERE r.name = %s AND c.name = r.name
ON CONFLICT (name, city_id) DO UPDATE SET slug = EXCLUDED.slug
```

becomes a direct region lookup:

```python
# TARGET
INSERT INTO localities (region_id, name, slug)
SELECT id, %s, %s FROM regions WHERE name = %s
ON CONFLICT (name, region_id) DO UPDATE SET slug = EXCLUDED.slug
```

⚠️ Note the existing region lookup by **name alone** is already ambiguous —
`regions` is unique on `(name, country_id)`, so two countries can hold a region
of the same name and this `WHERE r.name = %s` picks arbitrarily. Worth fixing in
the same pass by populating the locality's country from the legacy `region`
relation.

---

## Summary of actions

| Action | Target |
|---|---|
| **ADD column** | `countries.code`, `countries.continent`, `countries.flag_media_id` |
| **ADD enum** | `Continent` — **values TBD (D1)** |
| **ADD relation** | `Media.countryFlags` |
| **DELETE model** | `City` (+ all 6 `city_id` columns, all back-relations) |
| **ADD column** | `localities.region_id`, `localities.google_place_id` (unique, deferred) |
| **DROP column** | `localities.city_id` |
| **DROP constraint** | `localities @@unique([name, cityId])` |
| **CONSIDER** | `regions.lat` / `regions.lng` to replace the lost City centroid *(gap, not in tracker)* |
| **NOT MIGRATED** | `Country.otherNames` |
| **SCRIPT** | Populate `coverImage`; delete the placeholder-city block; re-point localities at `regions` |
