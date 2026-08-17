# Schema Change Plan — v2 schema vs. Field-Mapping Tracker

Source of truth for this plan:
`Postcard_Migration_Tracker(Field Mapping).csv` (baseline: *Postcard Travel Club
— Domain Model — Diagrams & Explanations*, 9 Jul 2026, confirmed authoritative
2026-08-05; revised 2026-08-05 and 2026-08-12).

Compared against: `schema/schema.prisma` (current) and every script in
`scripts/migrate_data.py`'s `STEPS` list.

!!! success "Status: IMPLEMENTED (2026-08-17)"
    The schema, the squashed baseline migration and all thirteen pipeline
    scripts are updated, and the full pipeline has been run end-to-end against
    live CMS data on a throwaway database.

    **See [Implementation Report & Runbook](implementation.md)** for everything
    that changed, how each open decision was resolved against real production
    data, the verified load counts, and how to rebuild the database.

    The per-table pages below are kept as the analysis that produced those
    changes. Where the live data contradicted the tracker — most notably
    **D5**, where the six "not in the real v1 Album schema" fields turned out to
    exist and be heavily populated — the implementation followed the data, and
    the Implementation Report records why.

    On **D5** specifically, product then decided which of those fields v2 needs:
    `media_kit` and `additionalInfo` are dropped, `sustainability` is renamed to
    `collections.about`, and `status` / `priority` / `company` are kept and
    migrated.

---

## 1. The four tracker revisions the schema has not absorbed

These are the headline items. Everything in the per-table files hangs off them.

| # | Revision | Dated | Blast radius |
|---|---|---|---|
| R1 | **City tier REMOVED** — geo is 3-tier `Country → Region → Locality`; Locality dedups on `google_place_id`; City Guide re-anchors to Region | 2026-08-05 | `City` model + 6 `city_id` columns dropped; `geo_migration.py` placeholder-city hack deleted; `cityguide.py` region→city matching deleted |
| R2 | **Membership split out of User** — Free/StarLife moves to its own `Membership` table with history/expiry | 2026-08-12 | `User.tier` + `UserTier` enum removed; new `Membership` model; `users.py` writes a second table |
| R3 | **Ownership is a direct FK, not a Circle** — `Circle` is reserved for follow/bookmark engagement only | 2026-08-12 | New `owner_user_id` / `assigned_to_user_id` / `user_id` / `created_by_user_id` columns on Collection, Postcard, Subcollection, Enquiry; `CircleRelationship` loses `author`, `assigned_staff`, `owner` |
| R4 | **Circle consolidation** — `Bookmark` + all six `Follow-*` tables collapse into ONE `relationship='bookmark'`, differentiated only by `owned_type` | 2026-08-12 | No new enum values; six new migration passes reuse `bookmark.py`'s shape; composite index `(user_id, owned_type)` required |

Two more structural items sit alongside them:

- **R5 — Stay Details is a component, and the dual-price fix was wrong.** The
  real v1 schema is ONE `price` + a `priceType` enum (`per person` /
  `twin_sharing`); the second display price is *calculated at read time*.
  `subcollections.price_starting_at` (migration
  `20260806060000_add_subcollection_price_starting_at`) was built on the earlier
  incorrect assumption and must be **reverted**.
- **R6 — CollectionCluster entries are fully derived, not curated.**
  `CollectionClusterType` gains a *match field* config (City Guide → `region_id`,
  Affiliation → `company_id`). There is no join table to migrate, which puts
  `collection_cluster_entries` up for deletion.

---

## 2. Files in this plan

| File | Script | Tables covered |
|---|---|---|
| [00-cross-cutting.md](00-cross-cutting.md) | — | Geo tier, Location component, Stay Details component, ownership FKs, Circle, Media identity |
| [01-seed-types.md](01-seed-types.md) | `seed.py` | `collection_types`, `subcollection_types`, `collection_cluster_types`, `tags`, `response_types`, `response_fields` |
| [02-geo.md](02-geo.md) | `geo_migration.py` | `countries`, `regions`, ~~`cities`~~, `localities` |
| [03-media.md](03-media.md) | `media.py` | `media` |
| [04-company.md](04-company.md) | `company.py` | `companies` |
| [05-users.md](05-users.md) | `users.py` | `user_types`, `users`, `user_roles`, **`memberships` (new)** |
| [06-directory-album.md](06-directory-album.md) | `directory_album.py` | `collection_types`, `collections`, `postcards` |
| [07-tags-facet.md](07-tags-facet.md) | `tags_facet.py` | `facet_types`, `facet_values` |
| [08-postcard.md](08-postcard.md) | `postcard.py` | `postcards`, `facet_assignments` |
| [09-journey.md](09-journey.md) | `journey.py` | `subcollections`, `subcollection_postcards` |
| [10-cityguide.md](10-cityguide.md) | `cityguide.py` | `collection_clusters`, ~~`collection_cluster_entries`~~ |
| [11-bookmark.md](11-bookmark.md) | `bookmark.py` | `circles` |
| [12-category-environment-facet.md](12-category-environment-facet.md) | **NEW `category_environment_facet.py`** | `facet_types`, `facet_values`, `facet_assignments` |
| [13-not-yet-scripted.md](13-not-yet-scripted.md) | — | `memories`, `user_events`, `enquiries`, Destination Expert, Dx-card, Travelogue, Tag-group |

---

## 3. All schema changes at a glance

### Models to DELETE

| Model | Why |
|---|---|
| `City` | R1 — tier removed |
| `Example` | Vestigial scaffold from `20260724081500_added_example`; nothing references it |
| `CollectionClusterEntry` | R6 — membership is fully derived (**decision D9**) |

### Models to ADD

| Model | Why |
|---|---|
| `Membership` | R2 — `user_id`, `tier`, `started_at`, `ends_at`, `status` |

### Enums to CHANGE

| Enum | Change |
|---|---|
| `UserTier` | **Delete**; replaced by `MembershipTier { free, star_life }` on `Membership` |
| `CircleRelationship` | Drop `author`, `assigned_staff`, `owner` (R3). Keep `bookmark`, `booked` |
| `FacetOwnedType` | **Add `subcollection`** — Journeys carry a 'Theme' facet |
| `ClusterEntryType` | Delete with `CollectionClusterEntry` (D9) |
| `Continent` | **New** — for `Country.continent`; value list still TBD (**decision D1**) |
| `PriceType` | **New** — `{ per_person, twin_sharing }` on Stay Details (R5) |
| `JourneyStatus` | **New** — `{ draft, deckBuild, deckFreeze, onTrip, complete }`; explicitly NOT harmonized with `ContentStatus` |
| `EnquiryStatus` | **New** — `{ new, in_progress, responded, closed }` |
| `EnquirySubjectType` | **New** — `{ subcollection, collection, postcard }` |

### Columns to DROP (by table)

| Table | Columns |
|---|---|
| `collections` | `city_id`, `media_kit`, `additional_info`, `sustainability` |
| `postcards` | `city_id` |
| `collection_clusters` | `city_id`, `locality_id` (**decision D8**) |
| `users` | `city_id`, `tier` |
| `memories` | `city_id` |
| `localities` | `city_id` |
| `subcollections` | `price_starting_at`, `guests_min`, `guests_max` |
| `user_types` | `is_default`, `is_creator`, `is_admin` |
| `enquiries` | `subcollection_id` (→ polymorphic) |

### Columns to ADD (by table)

| Table | Columns |
|---|---|
| `countries` | `code`, `continent`, `flag_media_id` |
| `localities` | `region_id`, `google_place_id` (unique), `lat`, `lng` |
| `media` | `name`, `caption`, `formats`, `hash`, `ext`, `size`, `provider`, `legacy_id` |
| `companies` | `cover_image_media_id` |
| `collections` | `signature`, `gallery`, `owner_user_id`, `assigned_to_user_id` |
| `postcards` | `user_id` |
| `subcollections` | `price_type`, `number_of_rooms`, `guests_per_room`, `day_wise_itinerary`, `terms_and_conditions`, `created_by_user_id` |
| `collection_cluster_types` | `match_field` |
| `enquiries` | `subject_type`, `subject_id`, `start_date`, `end_date`, `number_of_travelers`, `assigned_to_user_id` |
| `circles` | index `(user_id, owned_type)` |

### Columns to RENAME

| Table | From → To |
|---|---|
| `user_types` | `name` → `title` |
| `companies` | `name` → `title`, `icon_media_id` → `logo_media_id` |
| `collection_clusters` | (none — `intro` already correct) |

---

## 4. Open decisions — needed before any migration is written

| # | Decision | Blocks |
|---|---|---|
| D1 | `Country.continent` enum value list | `02-geo` |
| D2 | Media `id`: keep `BigInt` or move to `UUID` as the tracker says? A UUID switch cascades to every FK in the schema | `03-media` |
| D3 | `UserType.is_default` is dropped by the tracker, but `users.py` **requires** an `is_default` row to assign a fallback role. Need a replacement rule | `05-users` |
| D4 | Where does v1 store Free/StarLife? Tracker still says "TBD — locate v1 source". `users.py` currently reads `isLoyaltyMember` — confirm that is the source | `05-users` |
| D5 | Keep or drop `collections.status` / `priority` / `managed_by_company_id`? Tracker says "not in real v1 Album — archived", but they are v2-functional fields with no v1 source | `06-directory-album` |
| D6 | `FacetType.applies_to` must also scope to a **SubcollectionType** (Journeys → 'Theme'). Add `applies_to_subcollection_type_id`, or make `applies_to` polymorphic? | `07-tags-facet`, `12-category-environment` |
| D7 | Environment `FacetType.name` per CollectionType — tracker says "names TBD" | `12-category-environment` |
| D8 | Does `CollectionCluster` keep `locality_id`? Tracker confirms `country_id` + `region_id` only | `10-cityguide` |
| D9 | Delete `collection_cluster_entries` entirely (fully derived), or keep it as an optional hand-curation override on top of derivation? | `10-cityguide` |
| D10 | Drop the `Postcard ↔ Tag` M2M? Legacy tags now live as `Experience` facet values; nothing populates the M2M | `08-postcard` |
| D11 | `UserEvent.search_query` — tracker says v1 `searchData` is JSON but the canonical field name implies a plain string. Confirm shape | `13-not-yet-scripted` |

---

## 5. Suggested execution order

Do not touch scripts until the schema settles — most script breakage is a
direct consequence of a schema decision above.

1. **Resolve D1–D11.**
2. **Schema pass A — destructive/structural:** R1 (City tier), R2 (Membership),
   R3 (ownership FKs), R5 (`price_starting_at` revert). These invalidate data,
   so they land before any re-run.
3. **Schema pass B — additive:** Country/Media/Collection/Subcollection/Enquiry
   new columns, new enums, `match_field`.
4. **Script pass:** `geo_migration.py` and `cityguide.py` need real rewrites;
   the rest need field-level edits. See each file's *Script impact* section.
5. **New script:** `category_environment_facet.py` slots in between
   `tags_facet.py` (7) and `postcard.py` (8) — see [12](12-category-environment-facet.md).
6. **Backfill scripts** for the six `Follow-*` tables — see [11](11-bookmark.md).
