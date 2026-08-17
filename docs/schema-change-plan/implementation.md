# Implementation Report & Runbook

The [Schema Change Plan](index.md) is **implemented**. This page records every
change made, the evidence behind each decision, and how to rebuild the database
from scratch.

**Verification status:** the full 13-step pipeline was executed end-to-end
against a throwaway database (`postcardv2_schemacheck`, created and dropped) on
2026-08-17, loading live production CMS data. Every step completed; the counts
in [§4](#4-verified-load-counts) are that run's output. The scratch database and
its unsuffixed map files were removed afterwards. **No existing database was
modified.**

---

## 1. How the open decisions were resolved

Every `D*` decision was settled by querying the live Strapi API rather than
guessing. Three of them contradicted the tracker, and the data won.

| # | Decision | Evidence | Outcome |
|---|---|---|---|
| **D1** | `Country.continent` enum values | Legacy stores 2-letter codes: `AS` 57, `AF` 57, `EU` 50, `NA` 37, `OC` 25, `SA` 14, `AN` 5, null 20 | Enum `Continent { africa, antarctica, asia, europe, north_america, oceania, south_america }`; script maps the codes |
| **D2** | Media `BigInt` vs `UUID` | UUID would cascade to 10 FKs across 7 tables; the tracker's actual requirement is "a permanent old→new mapping" | **Kept `BigInt`**, added `media.legacy_id` (unique). It *is* the mapping, and it is a stronger idempotency key than `url` |
| **D3** | `UserType.is_default` dropped by tracker, but required by `users.py` | Legacy has all three flags populated (`Regular` is `isDefault`); the canonical doc keeps them | **Kept all three.** Tracker deviation documented — dropping `is_default` would break role assignment with no replacement |
| **D4** | Where does v1 store Free/StarLife? | `isLoyaltyMember` is **NULL on all 3371 users** | **No v1 source exists.** Every user gets one `free`/`active` membership row (matches the old `tier` default). Toggle via `SEED_FREE_MEMBERSHIP` |
| **D5** | Are `media_kit`/`additionalInfo`/`sustainability`/`status`/`priority`/`company` really absent from v1 Album? | **They are all present and populated**: media_kit 1461, additionalInfo 1406, sustainability 47, status 1728, priority 2833, company 324, signature 946 | **Tracker was wrong** (partial schema paste) — but see the product decision below: `media_kit` and `additionalInfo` are dropped anyway, `sustainability` is renamed to `about`, and `status`/`priority`/`company` are kept and migrated |
| **D6** | How does `FacetType` scope to a SubcollectionType? | `property_itineraries` carry **no** category/environment relation — Journey 'Theme' has no legacy data | Added nullable `applies_to_subcollection_type_id` + `FacetOwnedType.subcollection` so the CMS can start collecting it. Nothing seeded or assigned |
| **D7** | Environment FacetType names ("TBD") | Read the actual values per directory — see [§2.4](#24-facet-nomenclature) | `Setting` / `Venue Type` / `Format` / `Department` |
| **D8** | Does `CollectionCluster` keep `locality_id`? | City guides carry only `region` + `country` | **Dropped** `locality_id` and `city_id` |
| **D9** | Delete `collection_cluster_entries`? | Tracker: "fully derived, not curated… there is NO join/entry table". Derived rows were also never deleted, needing manual pruning | **Deleted** the table and enum. Added `collection_cluster_types.match_field`; `cityguide.py` now *previews* membership instead of materialising it |
| **D10** | Drop the `Postcard ↔ Tag` M2M? | Nothing populated it; legacy tags become Experience facet values | **Dropped** (`_PostcardTags` table gone) |
| **D11** | `UserEvent.search_query` — String or Json? | `searchData` is **null on every sampled event** (0/3000); `meta` likewise | **Kept `String?`** — nothing to lose. `UserEventType` widened to cover the 12 real `event_master` codes |

### Extra decisions the plan did not anticipate

| Question | Evidence | Outcome |
|---|---|---|
| Is Restaurants' `Cuisine/Type` one facet or two? | Category = cuisines (*Awadhi cuisine*, *Seafood*); Environment = venue kinds (*Bar*, *Bakery*) | **Two facets** — `Cuisine` from Category, `Venue Type` from Environment |
| Would the album→postcard split lose data? | R/E/S albums: `signature` on **672/673**, but media_kit/additionalInfo/sustainability all **0** | Added `postcards.signature` only. The other three would be dead columns |
| Is `album.cuisines` really F&B-only? | Shopping albums use it too — `shopping-type` averages 2.2 values per album | **All four Category facets are `allows_multiple`**; Environment facets stay single-select. Single-select violations went 187 → **0** |
| Where do legacy follow-tags point? | Legacy tags become `facet_values`, not the v2 `tags` table | Added `CircleOwnedType.facet_value`. Using `tag` would have pointed at the wrong table |
| Multi-directory albums (tracker wanted a rule) | **0** albums have more than one directory | Rule recorded as "lowest legacy directory id wins" and now logged, not silent |

### Product decision on the D5 fields (2026-08-17)

D5 established that all six fields exist in v1. Product then confirmed which of
them v2 actually needs. Because the database is rebuilt from scratch, dropping
them costs nothing.

| Legacy field | v1 rows | Outcome |
|---|---|---|
| `media_kit` | 1461 | **Dropped** — no longer used by the app; no v2 column |
| `additionalInfo` | 1406 | **Dropped** — same |
| `sustainability` | 47 | **Kept, renamed to `collections.about`** — the field holds general "about" copy, not a sustainability-only block |
| `status` | 1728 | Kept and migrated (already the v2 vocabulary) |
| `priority` | 2833 | Kept and migrated |
| `company` | 324 | Kept and migrated (`managed_by_company_id`) |

---

## 2. Schema changes

`schema/schema.prisma` — **32 tables** (was 36).

### 2.1 Models

| Action | Model | Reason |
|---|---|---|
| **Deleted** | `City` | R1 — tier removed |
| **Deleted** | `CollectionClusterEntry` | R6/D9 — membership is derived |
| **Deleted** | `Example` | Vestigial scaffold |
| **Deleted** | `_PostcardTags` (implicit M2M) | D10 — duplicate classification path |
| **Added** | `Membership` | R2 — tier history/expiry |

### 2.2 Enums

| Action | Enum |
|---|---|
| **Added** | `Continent`, `MembershipTier`, `MembershipStatus`, `JourneyStatus`, `PriceType`, `EnquiryStatus`, `EnquirySubjectType` |
| **Deleted** | `UserTier`, `ClusterEntryType` |
| **Changed** | `CircleRelationship` — dropped `author`, `assigned_staff`, `owner` (R3) |
| **Changed** | `CircleOwnedType` — added `facet_value` |
| **Changed** | `FacetOwnedType` — added `subcollection` |
| **Changed** | `UserEventType` — widened to the 12 legacy `event_master` codes plus v2-native events |

### 2.3 Columns

| Table | Dropped | Added |
|---|---|---|
| `countries` | — | `code`, `continent`, `flag_media_id` |
| `regions` | — | `lat`, `lng` (replacing the lost City centroid) |
| `localities` | `city_id` | `region_id`, `google_place_id` (unique), `lat`, `lng` |
| `media` | — | `legacy_id` (unique), `name`, `caption`, `ext`, `hash`, `size`, `provider`, `preview_url`, `provider_metadata` |
| `companies` | — | `cover_image_media_id`; renamed `name`→`title`, `icon_media_id`→`logo_media_id` |
| `user_types` | — | renamed `name`→`title` |
| `users` | `city_id`, `tier` | `city_name` |
| `collections` | `city_id`, `media_kit`, `additional_info` | `signature`, `gallery`, `owner_user_id`, `assigned_to_user_id`; renamed `sustainability`→`about` |
| `postcards` | `city_id` | `user_id`, `signature`, `seo`, `location`, `is_founder_story` |
| `subcollections` | `price_starting_at`, `guests_min`, `guests_max` | `price_type`, `number_of_rooms`, `guests_per_room`, `day_wise_itinerary`, `terms_and_conditions`, `created_by_user_id`; `status` → `JourneyStatus` |
| `collection_cluster_types` | — | `match_field` |
| `collection_clusters` | `city_id`, `locality_id` | — |
| `memories` | `city_id` | `collection_id`, `internal_url`, `signature` |
| `enquiries` | `subcollection_id` | `subject_type`, `subject_id`, `start_date`, `end_date`, `number_of_travelers`, `assigned_to_user_id`; `status` → `EnquiryStatus` |
| `responses` | — | `user_id` made **nullable** (ContactUs accepts logged-out submissions) |
| `circles` | — | index `(user_id, owned_type)` — the locked query pattern |
| `user_roles` | — | unique `(user_id, user_type_id)` — makes the upsert idempotent |

`collections` keeps `status`, `priority` and `managed_by_company_id`, and carries
the old `sustainability` copy as `about`. `media_kit` and `additional_info` have
no v2 column — see **D5** and the product decision above.

### 2.4 Facet nomenclature

Resolved from the live values, not invented:

| Collection type | Category facet | Environment facet |
|---|---|---|
| Properties | **Type** (*Eco-Lodge, Glamping, Villas*) | **Setting** (*City, Farm, Jungle, Desert*) |
| Restaurants | **Cuisine** (*Awadhi, Seafood, Coffee*) | **Venue Type** (*Bar, Bakery, Speakeasy*) |
| Events | **Category** (*Cocktail Tasting, Gin, Techno*) | **Format** (*Supper Club, Chef Takeover*) |
| Shopping | **Type** (*Sustainable, Handmade, Jewellery*) | **Department** (*Fashion, Home Decor, Books*) |

### 2.5 Migrations squashed

The nine incremental migrations were replaced by a single baseline,
`schema/migrations/20260817090000_v2_baseline/migration.sql` (922 lines). This
is correct because the database is rebuilt from scratch, and it removes the
retracted `20260806060000_add_subcollection_price_starting_at` cleanly rather
than layering a revert on top.

> ⚠️ The existing `production` database still carries the old 9-migration
> history. It **cannot** be migrated forward onto this baseline — it must be
> dropped and rebuilt (see [§3](#3-runbook)). Nothing in this change set was
> applied to it.

---

## 3. Runbook

### 3.1 Prerequisites

`.env` in the project root:

```
CMS_BASE_URL=https://api-prod.postcard.travel
CMS_API_TOKEN=...
DATABASE_URL=postgres://user:pass@127.0.0.1:5432/postcardv2
CMS_ADMIN_EMAIL=...          # /api/users strips emails; the admin API is required
CMS_ADMIN_PASSWORD=...
```

`ENV_SUFFIX` for the id-map files is derived from the **database name** in
`DATABASE_URL`: `development` → `_dev`, `production` → `_prod`, anything else →
no suffix.

### 3.2 Build the database

```bash
# 1. create an empty database (psql, or your tool of choice)
createdb postcardv2

# 2. apply the baseline schema
npm run migrate:deploy        # prisma migrate deploy
npm run generate              # prisma client (only if the app needs it)
```

To rebuild an existing database instead:

```bash
npm run migrate:reset         # DROPS EVERYTHING, re-applies the baseline
```

### 3.3 Load the data

```bash
python scripts/migrate_data.py
```

Thirteen steps, each its own process; the pipeline stops on the first failure
and tells you how to resume:

```bash
python scripts/migrate_data.py --from postcard.py    # resume from a step
python scripts/migrate_data.py --only cityguide.py   # run one step
```

| # | Step | Produces |
|---|---|---|
| 1 | `seed.py` | collection/subcollection/cluster types, persona tags, response forms |
| 2 | `geo_migration.py` | countries → regions → localities |
| 3 | `media.py` | media (keyed on `legacy_id`) |
| 4 | `company.py` | companies → `legacy_company_id_map` |
| 5 | `users.py` | user_types, users, memberships, user_roles → `legacy_user_id_map` |
| 6 | `directory_album.py` | collection_types, collections, postcards → `legacy_album_id_map`, `legacy_album_postcard_id_map` |
| 7 | `tags_facet.py` | FacetType 'Experience' + values → `legacy_tag_id_map` |
| 8 | `postcard.py` | postcards + Experience assignments → `legacy_postcard_id_map` |
| 9 | `journey.py` | subcollections + ordered postcards → `legacy_itinerary_id_map` |
| 10 | `category_environment_facet.py` | 8 facet types, values, assignments → `legacy_category_id_map`, `legacy_environment_id_map` |
| 11 | `cityguide.py` | collection_clusters → `legacy_cityguide_id_map` |
| 12 | `bookmark.py` | circles (postcard) |
| 13 | `follows.py` | circles (user, collection, postcard, company, facet_value, cluster) |

Order matters — steps 6–13 consume the map files written by earlier steps.

### 3.4 Start over

```bash
python scripts/truncate_all.py --yes    # empties every table, keeps the schema
python scripts/migrate_data.py
```

Every step is idempotent (upsert on a natural key), so re-running without
truncating is also safe.

### 3.5 Rendering a cluster page (there is no entry table)

`collection_cluster_entries` no longer exists. Membership is a query driven by
the cluster type's `collection_type_ids` + `match_field`:

```sql
-- City Guide: match_field = 'region_id'
SELECT p.* FROM postcards p
JOIN collection_clusters cc ON cc.id = :cluster_id
JOIN collection_cluster_types cct ON cct.id = cc.cluster_type_id
WHERE p.collection_type_id = ANY(cct.collection_type_ids)
  AND p.region_id = cc.region_id
  AND p.status = 'live'
  AND p.collection_id IS NULL;
```

`cityguide.py` prints exactly this resolution at the end of its run as a sanity
check, without writing anything.

---

## 4. Verified load counts

From the end-to-end run against live production CMS data:

| Table | Rows | Notes |
|---|---|---|
| `countries` | 265 | 215 with code, 245 with continent, 132 with flag |
| `regions` | 1183 | 3 legacy rows have no country → reported |
| `localities` | 288 | now parented to region; 2 same-name-in-region collapsed |
| `media` | 16 287 | all with `legacy_id`; 0 skipped |
| `companies` | 210 | 99 legacy rows have `name: null` (verified empty shells) |
| `users` | 3356 | 0 skipped |
| `memberships` | 3356 | all `free` — no legacy StarLife source (D4) |
| `user_roles` | 3356 | across 11 role types |
| `collections` | 2102 | Properties only; 292 owner, 1440 assignee, 266 signature, ~20 `about` |
| `postcards` | 6894 | 673 album-derived (672 with signature) + 6221 legacy |
| `subcollections` | 24 | **7 per_person / 10 twin_sharing** — previously all migrated as per-person |
| `subcollection_postcards` | 172 | 0 invariant violations |
| `facet_types` | 9 | Experience + 4 Category + 4 Environment |
| `facet_values` | 1140 | 718 Experience, 312 Category, 110 Environment |
| `facet_assignments` | 9604 | 520 collection, 9084 postcard, **0 orphans, 0 single-select violations** |
| `collection_clusters` | 9 | all resolve to a region; derive 601 postcards between them |
| `circles` | 2139 | 1166 postcard, 460 company, 444 collection, 34 user, 25 cluster, 10 facet_value |

### Known skips (all reported by the scripts, none silent)

- **326** postcards + **59** albums under Designer Tours — they belong to the
  Destination Expert / dx-card migration, which does not exist yet.
- **146** legacy postcards with no name; **99** companies with a null name.
- **252** bookmarks and **130** orphan bookmarks pointing at unmigrated or
  missing postcards.
- **84** follow-affiliate rows — Partner Affiliation clusters are not migrated
  yet, so there is no cluster id to point at. Counted and reported by
  `follows.py`, not written.
- **12** albums whose region name did not resolve, **15** with an ambiguous
  locality (`Shanti Nagar` exists twice), **6** with an unmatched company.

---

## 5. Data deliberately not migrated

Verified empty in production, so nothing is lost:
`Country.otherNames`, `Postcard.articleURL`, `Album.album_themes`,
`Album.fixedDates`, `Album.placeId`, `Album.locationLink`,
`UserEvent.searchData`, `UserEvent.meta`, `property_itinerary.best_time_to_visits`
(the legacy `Month` collection has 0 rows), `property_itinerary.createdByUser`.

Real data with no v2 home — **archived, not migrated**:

| Source | Rows | Note |
|---|---|---|
| `Album.media_kit` | 1461 | Dropped by product decision — no longer used by the app |
| `Album.additionalInfo` | 1406 | Dropped by product decision — no longer used by the app |
| `Album.news_article` | 287 | Editorial press links (title/description/link/publishedDate) |
| `Album.on_boarding` | 2826 | Internal partner-onboarding workflow state |
| `Album.bestMonth` | 3 | Superseded by the Journey `best_months` component |
| `Album.tourInfo` / `avgPricePerPerson` / `pricesStartingAt` / `numberOfGuests*` | ≤129 | Journey fields that belong to `property_itineraries` |
| `Destination-expert.quotes` / `founderMessage` / `dxSections` | 20 | Tracker: "archived as-is, no structured target" |
| `Event.ipAddress` / `ipCountry` / `url` / `podcast` | 51 696 | Tracker: "ignored, not migrated" |
| `Memory.album` / `dx_card` anchors | 44 | Schema now supports them (`memories.collection_id`); the Memory migration itself is not written yet |

---

## 6. Still outstanding

Not blockers for the rebuild, but the plan flags them:

1. **No migration script exists yet** for `memories` (176), `user_events`
   (51 696), `enquiries` (0 — v2-native), Destination Expert (20), Dx-card
   (497) or Travelogue (22). The schema supports all of them.
2. **Designer Tours** content is skipped everywhere pending that Destination
   Expert work — 385 rows in total.
3. **`localities.google_place_id`** is the intended uniqueness key but has no
   legacy source. `(name, region_id)` is the load-time key until the Gmap
   Address Enrichment workstream populates it.
4. **Location components** carry only `lat`/`lng` from legacy. `address`,
   `route`, `postal_code`, `google_place_id` etc. are Gmap enrichment outputs.
5. **Membership tiers** are uniformly `free` (D4) — a StarLife source must be
   found or the tiers set by hand.
6. **Notebooks** in `notebooks/` still contain the old author/assigned_staff
   Circle sections, which R3 makes wrong. Per the repo rule those changes must
   be delivered as paste-able cell snippets, not direct `.ipynb` edits — not
   done in this pass.
