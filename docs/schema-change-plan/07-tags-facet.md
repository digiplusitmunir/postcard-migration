# 07 — `tags_facet.py` (step 7)

Tables: `facet_types`, `facet_values`.

Tracker row: **Tag → FacetType 'Experience' + FacetAssignment
(owned_type=postcard)**.

This script is the closest to correct in the pipeline. One structural gap
(**D6**) and one enum addition.

---

## Field mapping

| v1 field | v2 target | Disposition | Action |
|---|---|---|---|
| `name` | `FacetValue.name` (under FacetType `Experience`) | Transform — *"EXTENSION beyond canonical doc (confirmed intentional, 2026-08-05)"* | **Keep** ✅ |
| `tag_group` | FacetType (if grouped), else default `Experience` FacetType | Transform — *"Matches the Tag-group decision — per-group call"* | **Deferred** — see below |
| *(scope)* | `FacetAssignment` (`owned_type = postcard`) | Transform — *"Confirmed 2026-08-05: owned by Postcard, not Collection directly"* | **Keep** ✅ — created in [08](08-postcard.md) |
| *(resolved)* | Property/Collection tag filter → **via rollup**, no direct assignment | Transform — *"CONFIRMED 2026-08-05: Property rolls up from child Postcards, same pattern flat_properties uses. Differs from Theme, which IS assigned directly on Collection"* | **Keep** ✅ — no Collection-level assignment |

**No schema change required by this row.** The script's scope decisions match
the tracker exactly.

---

## `facet_types` — schema gaps

### ⚠️ Decision D6 — FacetType cannot scope to a SubcollectionType

The Category tracker row requires:

> "CONFIRMED 2026-08-05: Properties → 'Type', Restaurants → 'Cuisine/Type',
> **Journeys (Subcollection) → 'Theme'**, Events → 'Category', Shopping → 'Type'."

`FacetType` only has `applies_to_collection_type_id`. A Journey is a
**SubcollectionType**, not a CollectionType, so the 'Theme' facet has nowhere to
attach.

Options:

- **(a)** **ADD** `applies_to_subcollection_type_id` (BigInt?, FK →
  `subcollection_types.id`). Simple, explicit, both columns nullable.
- **(b)** Make the scope polymorphic: `applies_to_type` enum
  (`collection` / `subcollection`) + `applies_to_id`. Consistent with the other
  polymorphic joins in the schema, but loses the FK.
- **(c)** Treat Journey as scoped to `Properties` (its parent CollectionType)
  and disambiguate by `FacetType.slug` alone. No schema change, but 'Theme' and
  'Type' would both claim Properties — workable, since they are distinct facet
  types.

**(a)** is the lowest-risk. **(c)** is defensible and free; it depends on
whether the UI needs to distinguish "facets of a Journey" from "facets of a
Property" structurally.

### `allows_multiple`

Already present and correctly used (`Experience` → `TRUE`). The tracker's
Category row implies per-facet values: *"single-select (Property Type) vs
multi-select (Cuisine)"*. **No change.**

---

## `facet_values`

| Column | Status |
|---|---|
| `facet_type_id`, `name`, `slug` | ✅ correct |
| `@@unique([facetTypeId, slug])` | ✅ correct — this is what lets the script merge the 8 duplicate tag names |

**No schema change.**

ℹ️ The Category tracker row maps `slug` → `FacetValue.slug` as **Direct**, while
`tags_facet.py` *derives* the slug from the name (`slugify(name)`) rather than
carrying v1's own slug. Fine for Tags (v1 tags may not have a slug), but the new
Category/Environment script should carry v1's slug where one exists — see
[12](12-category-environment-facet.md).

---

## `facet_assignments` — enum widening

Required by the Category row's Journeys→Theme mapping:

```
enum FacetOwnedType {
  collection
  postcard
  subcollection   // ADD — Journeys carry a 'Theme' facet
}
```

**ADD `subcollection`.** Not needed by `tags_facet.py` itself (Experience is
postcard-only), but by [12](12-category-environment-facet.md).

---

## `tag_group` — still deferred

Tracker row **Tag-group → FacetType or FacetValue**:
*"Confirmed to map to FacetType or FacetValue, live v1 field list not yet
pulled."* → still `NEEDS SOURCE SCHEMA`.

`tags_facet.py` handles this correctly: it writes nothing to the DB and
preserves the linkage to `legacy_tag_groups{_dev,_prod}.json` for a later
decision. **No action now.**

⚠️ If tag groups later become FacetTypes, every `Experience` facet value would
be re-parented — a data migration, not a schema change. Worth resolving before
production load rather than after.

---

## Fields explicitly dropped by the script (confirmed against the tracker)

| Dropped | Justification |
|---|---|
| `follow_tags` | → `Circle` (`owned_type = tag`, `relationship = bookmark`) per R4. **Now unblocked** — see [11](11-bookmark.md). The script's docstring still calls this "blocked Circle work, tracker #26"; that is stale |
| `createdAt` / `updatedAt` | Strapi housekeeping |

---

## Summary of actions

| Action | Target |
|---|---|
| **ADD enum value** | `FacetOwnedType.subcollection` |
| **DECISION D6** | How `FacetType` scopes to a SubcollectionType (add column / polymorphic / none) |
| **NO CHANGE** | `facet_values`, `tags_facet.py`'s core logic |
| **STALE DOC** | The script docstring calls `follow_tags` "blocked" — R4 unblocks it |
| **DEFERRED** | Tag-group → FacetType/FacetValue, pending v1 field list |
