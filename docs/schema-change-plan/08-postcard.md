# 08 — `postcard.py` (step 8)

Tables: `postcards`, `facet_assignments`.

Tracker row: **Postcard → Postcard**.

---

## Field mapping

| v1 field | v2 target | Disposition | Current | Action |
|---|---|---|---|---|
| `name` / `intro` / `slug` / `story` | same | Direct | ✅ | **Keep** |
| `album` | `collection_id` | Direct — *"collection_type_id is ALWAYS populated even when collection_id is null"* | ✅ | **Keep** |
| `country` | `country_id` | Transform — *"Only set directly if collection_id is null; otherwise inherited from Collection. **No city_id (tier removed)**"* | 4 geo FKs | **DROP** `city_id` (X1) |
| `user` | **`user_id`** | Transform — *"CORRECTED 2026-08-12: direct FK, NOT Circle (relationship=author) — same correction as Album"* | ❌ **missing** | **ADD** `user_id` (R3) |
| `coverImage` | `cover_media_id` | Direct | ✅ | **Keep** |
| `isFeatured` / `priority` | `is_featured` / `priority` | Direct | ✅ | **Keep** |
| `tags` | `FacetAssignment` (`owned_type=postcard`, via `Experience`) | Transform — *extension, confirmed intentional* | ✅ | **Keep** |
| `copyright` / `articleURL` | *(no direct field)* | **Flag** — *"copyright has no listed field in canonical Postcard schema either"* | `copyright` exists ✅ | See below |
| `isComplete` / `isFounderStory` | *(no direct field)* | **Flag** — *"Workflow/flag fields with no obvious v2 slot"* | — | See below |
| `bookmarks` | `Circle` (`relationship=bookmark`) | Direct — *"Superseded by Circle rows, not a Postcard field"* | ✅ | **Keep** — [11](11-bookmark.md) |
| `album_themes` | `FacetAssignment.facet_value_id` (`owned_type=postcard`) | Transform | ❌ not migrated | See below |
| `memories` | `Memory.postcard_id` (inverse) | Direct — *"nullable, Postcard is the only content anchor"* | ✅ | **Keep** |

---

## The four `Flag` fields

| v1 field | Current handling | Recommendation |
|---|---|---|
| `copyright` | **Migrated** into `postcards.copyright` | The tracker flags it as having no canonical field, but the column exists and carries real data. **Keep** — treat as a confirmed extension and update the tracker |
| `articleURL` | Dropped ("empty everywhere") | **Keep dropped.** Verify it is still empty in prod before final load |
| `isComplete` | Repurposed as the **status** source: `live` if `isComplete` else `draft` | **Keep** — a reasonable transform. Not a v2 column, so nothing to add |
| `isFounderStory` | Dropped ("no v2 home") | **Decision:** either add `postcards.is_founder_story` (Boolean) or confirm the feature is retired. Currently lost silently |

---

## ⚠️ `album_themes` — mapped by the tracker, not migrated by the script

The Postcard row maps `album_themes → FacetAssignment.facet_value_id
(owned_type=postcard)`. `postcard.py`'s docstring drops it as *"empty on
postcards"*.

Meanwhile the **Album** row says `album_themes` is
*"CONFIRMED 2026-08-12: dropped — not real v1 Album fields, artifacts of an
earlier incorrect assumption"*.

The two rows contradict each other. Given the Album row is the later, explicitly
confirmed one, **treat `album_themes` as retired on both** — but confirm, since
the Postcard row still lists it as a live Transform.

---

## `city_id` removal (X1)

`postcard.py` already passes literal `NULL` for `city_id` (line 235). Removing
the column is a clean no-op for this script; only the column list changes.

The composite index `@@index([countryId, regionId, cityId, localityId])` becomes
`@@index([countryId, regionId, localityId])`.

---

## ⚠️ Decision D10 — the `Postcard ↔ Tag` M2M

```
tags Tag[] @relation("PostcardTags")   // in model Postcard
```

Nothing populates it. Legacy tags become **`Experience` facet values**, and
`postcard.py` correctly writes `facet_assignments` instead. The `Tag` table's
only real consumer is `UserPersonaTag`.

**Recommend dropping the M2M** — it is a second, parallel classification path
that the tracker explicitly says was replaced (*"This is the single mechanism
for sub-type classification (the earlier Category/CollectionCategory entities
were removed as duplicates)"*, schema comment on `FacetAssignment`).

Keeping it invites exactly the duplicate-classification problem the facet model
was designed to remove.

---

## `facet_assignments`

`assign_facets()` (lines 276–303) is correct as written — one row per legacy
postcard↔tag link, `ON CONFLICT DO NOTHING`.

Two additions once [12](12-category-environment-facet.md) exists:

- Category and Environment assignments for postcards of a **non-dedicated** type
  (Restaurants / Events / Shopping) — those come from the **Album** record, since
  those albums *are* postcards. That work belongs in the new script, not here.
- The enum gains `subcollection` ([07](07-tags-facet.md)) — no impact on this script.

---

## Target model changes

```
model Postcard {
  ...
  cityId       BigInt? @map("city_id")    // DROP (X1)
  userId       BigInt? @map("user_id")    // ADD (R3) — the author
  // isFounderStory Boolean @default(false)  // decide: add or confirm retired
  // seo Json?                               // gap from 06 — album→postcard loses seo

  user User? @relation("PostcardAuthor", fields: [userId], references: [id])
  tags Tag[] @relation("PostcardTags")   // DROP (D10)

  @@index([countryId, regionId, localityId])
}
```

`User` needs a `authoredPostcards Postcard[] @relation("PostcardAuthor")`
back-relation. `Tag.postcards` is deleted with the M2M.

---

## Script impact

| Change | Where |
|---|---|
| Remove `city_id` from the INSERT column list | `migrate_postcards()` line 235 |
| Add `user` → `user_id` via `legacy_user_id_map` | `migrate_postcards()` — the map is **not currently loaded** |
| Simplify the geo-inheritance block — `c_city` never existed, so no change | lines 216–222 ✅ |
| Confirm `album_themes` is retired | docstring |
| Decide `isFounderStory` | docstring |
| Delete the notebook §6 author-circles step (R3) | `postcard_migration.ipynb` — snippets only |

⚠️ Like `directory_album.py`, this script does not load
`legacy_user_id_map{_dev,_prod}.json`. R3 requires it.

---

## Summary of actions

| Action | Target |
|---|---|
| **DROP column** | `postcards.city_id` |
| **ADD column** | `postcards.user_id` (author FK) |
| **DROP relation** | `Postcard.tags` M2M *(D10)* + `Tag.postcards` |
| **ADD relation** | `User.authoredPostcards` |
| **CONSIDER** | `postcards.is_founder_story`, `postcards.seo` |
| **CONFIRM** | `album_themes` retired (Postcard row vs Album row conflict); `articleURL` still empty; `copyright` kept as an extension |
| **SCRIPT** | Load the user id map; drop the circles step |
