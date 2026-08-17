# 09 — `journey.py` (step 9)

Tables: `subcollections`, `subcollection_postcards`.

Tracker rows: **Property-itinerary → Subcollection (SubcollectionType =
'Journey')** and the cross-cutting **Stay Details Component**.

Two things land here: the **retracted dual-price fix (R5)** and a set of field
renames the script currently routes into the wrong columns.

---

## `subcollections` — field mapping

| v1 field | v2 target | Disposition | Current script writes | Action |
|---|---|---|---|---|
| `title` | `Subcollection.name` | Transform — *"Canonical field is likely 'name', not 'title'"* | → `name` ✅ | **Keep** |
| `description` | `Subcollection.description` | Direct | → **`intro`** ⚠️ | **Decide** — tracker says `description`, schema has `intro`. See below |
| `coverImage` | `cover_media_id` | Direct | ✅ | **Keep** |
| `album` (relation) | `collection_id` | Direct — *"anchors Subcollection to Collection"* | ✅ | **Keep** |
| `postcards` (M2M) | `SubcollectionPostcard.postcard_id` | Direct — *"sequence_order = manually chosen display position"* | ✅ | **Keep** |
| `slug` | `Subcollection.slug` | Direct | ✅ | **Keep** |
| `createdByUser` | **`created_by_user_id`** | Transform — *"Direct FK, NOT Circle — same ownership correction as Album/Postcard"* | ❌ **not migrated** | **ADD** column (R3) |
| `status` (draft/deckBuild/deckFreeze/onTrip/complete) | `Subcollection.status` | Transform — *"CONFIRMED 2026-08-12: kept as its own separate Journey-workflow enum, no harmonization with Collection.status"* | collapsed to `ContentStatus` ⚠️ | **ADD** enum `JourneyStatus`. See below |
| `country` (relation) | *(no separate field — derived from `Collection.country_id`)* | Transform — *"country is taken from the parent property, not stored separately"* | dropped ✅ | **Keep dropped** |
| `dayWiseItinerary` | **`day_wise_itinerary`** | Transform — *"New field name, richtext preserved as-is"* | → **`story`** ⚠️ | **ADD** column, stop using `story` |
| `termsAndConditions` | **`terms_and_conditions`** | Transform — *"New field name, richtext preserved as-is"* | → **`tour_info`** ⚠️ | **ADD** column, stop using `tour_info` |
| `numberOfDays` / `numberOfNights` / `price` / `priceType` / `best_time_to_visits` | → **Stay Details component** | Transform | partly migrated | See R5 below |

---

## ⚠️ Three fields are being written into the wrong columns

`journey.py` maps legacy fields onto whatever v2 column looked closest:

| Legacy | Script writes to | Tracker says |
|---|---|---|
| `description` | `intro` | `description` |
| `dayWiseItinerary` | `story` | `day_wise_itinerary` |
| `termsAndConditions` | `tour_info` | `terms_and_conditions` |

This is not merely cosmetic: `story` and `tour_info` are *distinct* v2 concepts
(the schema documents both as richtext editorial fields), so a Journey currently
has no room for a real story or tour_info of its own.

**Recommendation:**
- **ADD** `day_wise_itinerary` (String?) and `terms_and_conditions` (String?).
- **Keep** `story` and `tour_info` as genuine v2 fields, unpopulated by v1.
- For `description` → `intro`: `intro` is the canonical name used consistently
  across `Collection`, `Postcard` and `CollectionCluster` (the City-guide row
  even corrects `description → intro` explicitly). **Keep `intro`** and treat
  the tracker's "description" as loose wording.

---

## ⚠️ R5 — Stay Details, and the retracted dual-price fix

> "CORRECTION 2026-08-12: real v1 pattern is ONE price field + a priceType enum
> ('per person'/'twin sharing') — NOT two separate price columns as the earlier
> (incorrect, pre-real-schema) Album draft assumed."

| Action | Column | Reason |
|---|---|---|
| **DROP** | `price_starting_at` | Reverts migration `20260806060000_add_subcollection_price_starting_at`. Built on the retracted assumption; `journey.py` already writes NULL to it |
| **DROP** | `guests_min` | Replaced by `number_of_rooms` + `guests_per_room`. `journey.py` writes NULL |
| **DROP** | `guests_max` | Same |
| **ADD** | `price_type` (enum `PriceType { per_person, twin_sharing }`) | **Currently discarded data** — see below |
| **ADD** | `number_of_rooms` (Int?) | New component field, no v1 source |
| **ADD** | `guests_per_room` (Int?) | New component field, no v1 source. *"Angel's original ask ('number of persons per room') lives here going forward"* |
| **KEEP** | `price`, `number_of_nights`, `number_of_days`, `best_months` | ✅ correct |

### `priceType` is real data being thrown away

```python
# journey.py:200-201
if (a.get("priceType") or "per person") != "per person":
    twin_sharing.append((it["id"], title, a.get("priceType"), a.get("price")))
```

The script *detects* twin-sharing rows and prints them for manual review, then
inserts nothing. Every twin-sharing price is currently migrated as if it were
per-person — a silent pricing error, not just a dropped field. `price_type` is
the highest-priority add in this file.

The tracker also confirms the second display price is **calculated at read
time** from `price` + `price_type` — so no second column is needed anywhere.

### `best_months`

> "oneToMany relation to a Month entity, not an embedded array — iterate the
> relation to populate best_months."

`journey.py` already does exactly this (line 194). ✅ No change.

---

## ⚠️ `JourneyStatus` — a separate enum, not `ContentStatus`

> "CONFIRMED 2026-08-12: kept as its own separate Journey-workflow enum, no
> harmonization with Collection.status."

`journey.py` currently collapses five legacy states into two:

```python
STATUS_MAP = {"deckFreeze": "live", "onTrip": "live", "complete": "live"}
# deckBuild / draft / None -> draft
```

That destroys the distinction between "frozen", "on trip" and "complete" —
states the tracker says must be preserved.

```
enum JourneyStatus {
  draft
  deckBuild
  deckFreeze
  onTrip
  complete
}
```

`subcollections.status` changes type from `ContentStatus` to `JourneyStatus`,
and `STATUS_MAP` becomes a pass-through.

⚠️ This is a **type change on an existing column** — needs a `USING` cast in the
generated SQL migration, or a drop-and-recreate if the table is re-migrated from
scratch.

---

## `subcollection_postcards`

Tracker: *"sequence_order = manually chosen display position, same pattern as
Album's postcards."*

| Column | Status |
|---|---|
| `subcollection_id`, `postcard_id`, `sequence_order` | ✅ correct |
| `@@id([subcollectionId, postcardId])`, `@@index([subcollectionId, sequenceOrder])` | ✅ correct |

**No schema change.**

The app-level invariant (`postcard.collection_id` must equal the parent
`subcollection.collection_id`) is already enforced by `link_postcards()`
(lines 280–282) and verified in `verify()`. ✅

---

## Journeys and facets (Theme)

The Category tracker row assigns **Journeys → 'Theme'**. That needs:
- `FacetOwnedType.subcollection` ([07](07-tags-facet.md)), and
- **decision D6** on how `FacetType` scopes to a SubcollectionType.

No v1 source is identified for Journey themes, so nothing is migrated here yet —
but the schema must accommodate it.

---

## Target model changes

```
model Subcollection {
  ...
  price              Decimal?      @db.Decimal(12, 2)
  priceStartingAt    Decimal?      @map("price_starting_at")   // DROP (R5)
  guestsMin          Int?          @map("guests_min")          // DROP (R5)
  guestsMax          Int?          @map("guests_max")          // DROP (R5)

  priceType          PriceType?    @map("price_type")          // ADD (R5)
  numberOfRooms      Int?          @map("number_of_rooms")     // ADD (R5)
  guestsPerRoom      Int?          @map("guests_per_room")     // ADD (R5)
  dayWiseItinerary   String?       @map("day_wise_itinerary")  // ADD
  termsAndConditions String?       @map("terms_and_conditions")// ADD
  createdByUserId    BigInt?       @map("created_by_user_id")  // ADD (R3)

  status             JourneyStatus @default(draft)             // TYPE CHANGE

  createdBy User? @relation("SubcollectionCreator", fields: [createdByUserId], references: [id])
}
```

---

## Script impact

| Change | Where |
|---|---|
| Write `price_type` instead of reporting it; delete the `twin_sharing` review list | lines 200–201, 253 |
| `STATUS_MAP` → pass-through of the five legacy values | line 66, 198 |
| `dayWiseItinerary` → `day_wise_itinerary` (not `story`) | line 232 |
| `termsAndConditions` → `terms_and_conditions` (not `tour_info`) | line 234 |
| Remove `price_starting_at` / `guests_min` / `guests_max` from the INSERT | line 213 |
| Add `createdByUser` → `created_by_user_id` via `legacy_user_id_map` (not currently loaded) | `migrate_journeys()` |
| Delete the notebook §6 author-circles step (R3) | `journey_migration.ipynb` — snippets only |
| Update the docstring: `priceType` is no longer "dropped" | lines 32–34 |

---

## Summary of actions

| Action | Target |
|---|---|
| **DROP column** | `subcollections.price_starting_at`, `.guests_min`, `.guests_max` |
| **ADD column** | `subcollections.price_type`, `.number_of_rooms`, `.guests_per_room`, `.day_wise_itinerary`, `.terms_and_conditions`, `.created_by_user_id` |
| **ADD enum** | `PriceType { per_person, twin_sharing }`, `JourneyStatus { draft, deckBuild, deckFreeze, onTrip, complete }` |
| **CHANGE type** | `subcollections.status` → `JourneyStatus` |
| **REVERT migration** | `20260806060000_add_subcollection_price_starting_at` |
| **NO CHANGE** | `subcollection_postcards` |
| **HIGHEST PRIORITY** | `price_type` — twin-sharing prices are currently migrated as per-person |
