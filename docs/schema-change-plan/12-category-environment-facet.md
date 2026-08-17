# 12 — NEW SCRIPT: `category_environment_facet.py`

Tables: `facet_types`, `facet_values`, `facet_assignments`.

Tracker rows: **Category → FacetType (scoped per CollectionType) / FacetValue /
FacetAssignment** and **Environment → FacetType (scoped per CollectionType,
name TBD) / FacetValue / FacetAssignment**.

**This is the answer to "prepare 1 more script for category and environment
migration inside the facettype and facetvalue thing".** Yes — and it should be
**one script covering both**, because they are structurally identical: same
transform, same scoping rule, same assignment rule. Only the FacetType naming
differs.

---

## Why one script, not two

| | Category | Environment |
|---|---|---|
| Value → | `FacetValue.name` / `.slug` | `FacetValue.name` |
| Grouping → | `FacetType` scoped per CollectionType | `FacetType` scoped per CollectionType |
| Assignment → | `FacetAssignment`, `owned_type` by CollectionType | **"Same binding rule as Category"** |
| FacetType names | Confirmed 2026-08-05 | **TBD (D7)** |

The tracker's Environment row says the naming is *"same family as Category's
Type/Cuisine-Type/Theme/Category nomenclature"* and the binding is *"Same binding
rule as Category"*. Two scripts would be two copies of one algorithm.

---

## Pipeline position

Between `tags_facet.py` (7) and `postcard.py` (8):

```python
STEPS = [
    ...
    "tags_facet.py",
    "category_environment_facet.py",   # NEW — needs collections + postcards to exist
    "postcard.py",
    ...
]
```

⚠️ **Ordering conflict.** Assignments need `collections` (from step 6) *and*
`postcards` (from step 8) to already exist — but step 8 runs *after*. Two ways
out:

- **(a)** Split into two passes: **facet types + values** before `postcard.py`,
  **assignments** after. Cleanest.
- **(b)** Run the whole script after `postcard.py` (position 9). Simpler, and
  the facet values are not needed by `postcard.py` — it consumes only the
  *Experience* map from `tags_facet.py`.

**Recommend (b)** — one script, positioned after `postcard.py`.

---

## Step 1 — FacetTypes

> "CONFIRMED 2026-08-05: Properties → 'Type', Restaurants → 'Cuisine/Type',
> Journeys (Subcollection) → 'Theme', Events → 'Category', Shopping → 'Type'."

### Category FacetTypes

| Legacy `directory` | CollectionType | `FacetType.name` | slug | `allows_multiple` |
|---|---|---|---|---|
| `mindful-luxury-hotels` | Properties | `Type` | `property-type` | false (single-select) |
| `food-and-beverages` | Restaurants | `Cuisine` *(see below)* | `cuisine` | true (multi-select) |
| `postcard-events` | Events | `Category` | `event-category` | ? |
| `postcard-shopping` | Shopping | `Type` | `shopping-type` | ? |
| *(Journey subcollection type)* | — | `Theme` | `journey-theme` | ? |

⚠️ **"Cuisine/Type" is ambiguous** — the tracker writes Restaurants as
`Cuisine/Type` with a slash. That is either one facet named "Cuisine/Type", or
two separate facets (`Cuisine` **and** `Type`) for Restaurants. Elsewhere the
tracker treats Cuisine as its own thing (*"single-select (Property Type) vs
multi-select (Cuisine)"* on the `FacetType.allows_multiple` comment). **Confirm
before implementing.**

⚠️ `allows_multiple` per facet is only specified for two of them (Property Type =
single, Cuisine = multi). The other three need a call.

### Environment FacetTypes — **decision D7**

> "CLARIFIED 2026-08-05: same family as Category's Type/Cuisine-Type/Theme/
> Category nomenclature — **names TBD**."

Nothing can be seeded until D7 is answered. A reasonable default, pending the
decision: one `Setting` (or `Environment`) FacetType per CollectionType, e.g.
`property-setting`, `restaurant-setting`. Values from the tracker's examples:
`Beachfront`, `Mountain`, `Urban`.

### ⚠️ Decision D6 — Journey/Theme has nowhere to attach

`FacetType.applies_to_collection_type_id` points at `collection_types`. Journey
is a **SubcollectionType**. See [07](07-tags-facet.md) for the three options.
This blocks the `Theme` FacetType specifically; the other four are unaffected.

---

## Step 2 — FacetValues

| v1 field | v2 target | Disposition |
|---|---|---|
| `name` | `FacetValue.name` | Direct — *"The actual category value (e.g. 'Boutique Stay', 'Indian', 'Adventure')"* |
| `slug` | `FacetValue.slug` | Direct |
| `directory` | `FacetType.applies_to_collection_type_id` + `FacetType.name` | Transform |

Environment's row lists only `name` (*"e.g. 'Beachfront', 'Mountain', 'Urban'"*)
— no slug. Derive it with `slugify(name)` when v1 has none.

ℹ️ Unlike `tags_facet.py` (which always derives the slug), Category has a real
v1 `slug` field marked **Direct**. Carry it over, falling back to
`slugify(name)`.

`@@unique([facetTypeId, slug])` already handles in-run dedupe, exactly as it does
for tags. Duplicate names within a facet type merge; the same name under two
different facet types stays distinct — which is what makes `Type` (Properties)
and `Type` (Shopping) safely separate.

---

## Step 3 — FacetAssignments

> "CONFIRMED 2026-08-05 (Option A). RECONFIRMED 2026-08-12: still required on
> Collection even though trimmed out of the real Album schema paste — relation
> lives on the Category/FacetValue side."

| Source CollectionType | `owned_type` | `owned_id` resolves via |
|---|---|---|
| Properties | `collection` | `legacy_album_id_map` |
| Destination Expert | `collection` | *(dx-card migration — not yet built)* |
| Restaurants | `postcard` | `legacy_album_postcard_id_map` |
| Events | `postcard` | `legacy_album_postcard_id_map` |
| Shopping | `postcard` | `legacy_album_postcard_id_map` |
| Journeys | `subcollection` | `legacy_itinerary_id_map` — **needs `FacetOwnedType.subcollection`** |

This mirrors the album split exactly: albums of a dedicated type became
collections, albums of a non-dedicated type became postcards, and the assignment
follows the row wherever it landed. Both maps already exist. ✅

The Dx-card row confirms the same treatment: *"category / environment →
facet_value_id … Same Facet transform as Album."*

⚠️ **Direction of the v1 relation is unconfirmed.** The tracker says *"relation
lives on the Category/FacetValue side"*, meaning v1 Category rows point at
albums, not the reverse. So the script likely fetches `/api/categories` with
`{"populate": "albums"}` (or similar) rather than reading a `category` field off
each album. **Needs the live v1 field list to confirm** — the Album row does list
`category` and `environment` as album fields, so both directions may be
populated.

---

## Schema prerequisites

| Requirement | Source |
|---|---|
| `FacetOwnedType.subcollection` | [07](07-tags-facet.md) — for Journey/Theme |
| FacetType scoping to a SubcollectionType (**D6**) | [07](07-tags-facet.md) |
| Environment FacetType names (**D7**) | this file |
| `legacy_album_id_map`, `legacy_album_postcard_id_map` | ✅ `directory_album.py` |
| `legacy_itinerary_id_map` | ✅ `journey.py` |

**No new tables or columns** beyond the enum value and the D6 outcome —
Category and Environment were deliberately folded into the existing facet model:

> "This is the single mechanism for sub-type classification (the earlier
> Category/CollectionCategory entities were removed as duplicates)."
> — schema comment on `FacetAssignment`

---

## Proposed script shape

```
category_environment_facet.py
├── FACET_TYPES config          # (legacy directory slug, ct slug, facet name, slug, allows_multiple)
│   ├── category facets         # confirmed 2026-08-05
│   └── environment facets      # BLOCKED on D7
├── upsert_facet_types()        # -> {(kind, ct_slug): facet_type_id}
├── migrate_values(kind)        # /api/categories, /api/environments -> facet_values
│                               #   carry v1 slug; slugify(name) fallback
│                               #   dedupe via @@unique(facet_type_id, slug)
├── assign(kind)                # -> facet_assignments, owned_type by CollectionType
│                               #   collection | postcard | subcollection
├── save_maps()                 # legacy_category_id_map, legacy_environment_id_map
└── verify()                    # counts per facet type; orphan assignments; dup slugs
```

Idempotent on the same keys as `tags_facet.py`: values upsert on
`(facet_type_id, slug)`, assignments `ON CONFLICT DO NOTHING`.

---

## Open questions before writing it

1. **D7** — Environment FacetType names per CollectionType.
2. **D6** — how `FacetType` scopes to the Journey SubcollectionType.
3. Is Restaurants' `Cuisine/Type` one facet or two?
4. `allows_multiple` for Events `Category`, Shopping `Type`, Journey `Theme`.
5. Which side owns the v1 relation — Category→Album, or Album→Category?
6. Do Journeys have a v1 category/environment source at all, or is `Theme` a
   v2-only facet with no data to migrate?

---

## Summary of actions

| Action | Target |
|---|---|
| **NEW SCRIPT** | `scripts/category_environment_facet.py`, positioned after `postcard.py` |
| **ADD to** `migrate_data.py` | new `STEPS` entry |
| **ADD enum value** | `FacetOwnedType.subcollection` *(shared with [07](07-tags-facet.md))* |
| **DECISION D6** | FacetType → SubcollectionType scoping |
| **DECISION D7** | Environment FacetType names |
| **NO new tables** | Category/Environment fold into the existing facet model |
