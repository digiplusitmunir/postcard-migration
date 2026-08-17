# 01 — `seed.py` (step 1)

Seeds developer-defined type/definition tables. Nothing here has a v1 source —
these are v2-only admin config, so the tracker mostly does not cover them. The
changes below are consequences of tracker decisions elsewhere.

Tables: `collection_types`, `subcollection_types`, `collection_cluster_types`,
`tags`, `response_types`, `response_fields`.

---

## `collection_types`

Tracker row: **Directory → CollectionType**.

| v1 field | v2 target | Disposition | Action |
|---|---|---|---|
| `name` | `name` | Direct | **Keep** |
| `slug` | `slug` | Direct | **Keep** |
| *(new)* | `description` | Flag — no v1 source | **Keep**, stays NULL at seed |
| *(new)* | `icon` | Flag — no v1 source | **Keep**. `directory_album.py` fills it from the legacy `logo` url |
| *(new)* | `has_dedicated_collection` | Transform — derived business rule | **Keep** — true only for Properties and Destination Expert |
| *(new)* | `priority` | Flag — no v1 source | **Keep** |

**No schema change.** Seed list already matches the tracker's five types.

⚠️ Consistency check: `seed.py` sets `Destination Expert` →
`has_dedicated_collection = True`. `directory_album.py`'s `DIRECTORY_TO_CT`
does not include it (Designer Tours is skipped). That is correct today, but the
Dx-card migration ([13](13-not-yet-scripted.md)) must not regress it.

---

## `subcollection_types`

No tracker row. `Journey` under `properties` is correct per the
Property-itinerary row ("→ Subcollection (SubcollectionType = 'Journey')").

**No schema change** to the table itself.

⚠️ **Related — decision D6.** The Category tracker row says
*"Journeys (Subcollection) → 'Theme'"*, i.e. a `FacetType` must be scopeable to
a **SubcollectionType**, not just a CollectionType. `FacetType` currently only
has `applies_to_collection_type_id`. See [07](07-tags-facet.md).

⚠️ **Travelogue** ("→ Subcollection under Destination Expert", source schema not
yet pulled) will need a second `SubcollectionType` row seeded here once its
fields are known.

---

## `collection_cluster_types`

Tracker row #182 (the `NEEDS SOURCE SCHEMA` block under City-guide) —
**FULLY RESOLVED 2026-08-12, architecture not schema**:

> "CollectionClusterType defines TWO things per type — (1) which CollectionTypes
> are eligible (for City Guide: Restaurants, Shopping, Events) and (2) which
> FIELD is used to match Collections to a cluster instance (for City Guide:
> region_id). A CollectionCluster instance stores the actual value for that
> field. Rendering a cluster page = query Collections WHERE collection_type_id
> IN (allowed types) AND [match field] = [cluster's value] — fully derived, not
> curated."

| Action | Column | Reason |
|---|---|---|
| **KEEP** | `collection_type_ids` (BigInt[]) | This is part (1). Already implemented by migration `20260811090000_add_cluster_type_collection_type_ids` |
| **ADD** | `match_field` (String) | This is part (2) — **missing entirely from the schema** |

`match_field` values: `'region_id'` for City Guide, `'company_id'` for the
deferred Affiliation type. A plain string column read by the service layer is
sufficient; an enum would need widening every time a new match field appears.

> "DIFFERENT cluster types can use DIFFERENT match fields with no collision
> risk: City Guide filters by region_id, while a company-based cluster would
> filter by company_id — since they key off different fields, a Collection's
> City Guide membership and its Affiliation membership are fully independent."

### Seed change

```
# name, slug, priority, collection_type_slugs, match_field
COLLECTION_CLUSTER_TYPES = [
    ("City Guide", "city-guide", 1, ["restaurants", "events", "shopping"], "region_id"),
]
```

⚠️ The seed's collection-type list is **`restaurants, events, shopping`**; the
tracker writes it as **"Restaurants, Shopping, Events"**. The array order is the
*display order*, so this is a real (if minor) discrepancy — confirm which order
the design intends.

### Knock-on

If `match_field` lands and derivation moves to the service layer, `cityguide.py`'s
`DERIVE_ENTRIES` block and the whole `collection_cluster_entries` table become
redundant. That is **decision D9** — see [10](10-cityguide.md).

---

## `tags`

No tracker row for the *new* `tags` table. The tracker's **Tag** row maps legacy
tags to `FacetValue` under FacetType `Experience` — **not** to this table, and
`tags_facet.py` correctly honours that.

So `tags` is now used only by:
- `UserPersonaTag` (weighted persona join), and
- `Postcard.tags` M2M — **which nothing populates**.

**Decision D10:** drop the `Postcard ↔ Tag` M2M relation. If it goes, the three
sample rows seeded here exist purely for `UserPersonaTag`. See [08](08-postcard.md).

**No schema change to the table.**

---

## `response_types` / `response_fields`

No tracker row. `contact_form` mirrors the legacy Strapi `ContactUs` collection.

**No schema change.**

ℹ️ Gap: the `Response` model requires `user_id` (non-null, cascade). A legacy
`ContactUs` submission from a logged-out visitor has no user. If ContactUs data
is ever migrated, `responses.user_id` must become nullable. Not blocking — no
ContactUs migration script exists yet.

---

## Summary of actions

| Action | Target |
|---|---|
| **ADD column** | `collection_cluster_types.match_field` (String) |
| **EDIT seed** | `COLLECTION_CLUSTER_TYPES` gains a `match_field` element |
| **CONFIRM** | Display order of City Guide's `collection_type_ids` |
| **DECISION D6** | FacetType scoping to SubcollectionType (affects future Journey/Theme seeding) |
| **DECISION D9** | Whether derivation moves to the service layer (removes `cityguide.py`'s entry step) |
| **DECISION D10** | Drop `Postcard ↔ Tag` M2M |
