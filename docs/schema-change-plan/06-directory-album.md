# 06 — `directory_album.py` (step 6)

Tables: `collection_types`, `collections`, `postcards` (the non-dedicated split).

Tracker rows: **Directory → CollectionType** (covered in [01](01-seed-types.md))
and **Album → Collection**.

This is where the ownership revision (**R3**) bites hardest, and where the
tracker's "real v1 Album schema" note retires four columns the script currently
migrates.

---

## `collections` — field mapping

| v1 field | v2 target | Disposition | Current | Action |
|---|---|---|---|---|
| `name` | `Collection.name` | Direct | ✅ | **Keep** |
| `intro` | `Collection.intro` | Direct | ✅ | **Keep** |
| `story` | `Collection.story` | Direct | ✅ | **Keep** |
| `coverImage` | `Collection.cover_media_id` | Direct — *"Resolve via Media ID-mapping table"* | ✅ | **Keep** |
| `isFeatured` | `Collection.is_featured` | Direct | ✅ | **Keep** |
| `slug` | `Collection.slug` | Direct | ✅ | **Keep** |
| `country` / `region` / `locality` | `country_id` / `region_id` / `locality_id` | Transform — *"REVISED 2026-08-05: City tier removed — 3 geo FKs (was 4). CONFIRMED 2026-08-12: matches real v1 Album schema exactly"* | 4 FKs | **DROP** `city_id` (X1) |
| `directories` (M2M) | `collection_type_id` (single FK) | Transform — *"a property belongs to exactly ONE CollectionType — v1's M2M is transformed down to a single value"* | ✅ single FK | **Keep** — but see the dedupe note below |
| `website` | `Collection.website` | Direct | ✅ | **Keep** |
| `signature` | `Collection.signature` | Direct — *"Confirm exact target field name — not explicitly in canonical doc"* | ❌ **missing** | **ADD** `signature` (String?) |
| `user` | `Collection.owner_user_id` | Transform — *"CORRECTED 2026-08-12: direct FK, NOT Circle. This is who the property belongs to"* | ❌ **missing** | **ADD** `owner_user_id` (R3) |
| `assignTo` | `Collection.assigned_to_user_id` | Transform — *"CORRECTED 2026-08-12: direct FK, NOT Circle. This is who works on/edits the content"* | ❌ **missing** | **ADD** `assigned_to_user_id` (R3) |
| `postcards` | *(no action — reverse relation)* | Direct | ✅ | **Keep** — satisfied via `Postcard.collection_id` |
| `galleryCollection` | `Collection.gallery` (component, repeatable) | Transform — *"gallery of categorized image groups (e.g. rooms/exterior/amenities), not a flat list. Component shape: repeatable groups, each with a category label + images"* | ❌ **missing** | **ADD** `gallery` (Json?) |
| `seo` | SEO (reusable component) | Transform — *"reusable component, attachable wherever dynamic SEO is needed (not Collection-only)"* | ✅ `seo Json?` | **Keep** |
| `category` | `FacetAssignment.facet_value_id` | Transform | ❌ not migrated | **NEW SCRIPT** — see [12](12-category-environment-facet.md) |
| `environment` | `FacetAssignment.facet_value_id` | Transform | ❌ not migrated | **NEW SCRIPT** — see [12](12-category-environment-facet.md) |
| `album_themes` / `cuisines` | *(not migrated)* | **Archived** — *"CONFIRMED 2026-08-12: dropped — not real v1 Album fields, artifacts of an earlier incorrect assumption"* | — | **No action** |
| `company` / `status` / `priority` / `media_kit` / `additionalInfo` / `sustainability` | *(not migrated)* | **Archived** — *"CONFIRMED 2026-08-12: not in the real v1 Album schema — ignored, archived as-is"* | ✅ **all six migrated today** | **DECISION D5** — see below |

---

## ⚠️ Decision D5 — the six "archived" fields

`directory_album.py` currently reads and writes all six (lines 409–419 for
company, 326–328 for status, and 462–464 for media_kit / additionalInfo /
sustainability). The tracker says none of them exist in the real v1 Album schema.

They split into two groups:

**Group 1 — v2-functional, no v1 source. KEEP the column, stop migrating.**

| Column | Why keep |
|---|---|
| `status` | The 5-value editorial workflow (`draft/assigned/submit/rework/live`) is core v2. Without a v1 source, everything lands at the `draft` default — or `live`, if the current `isActive` fallback is retained as a deliberate choice |
| `priority` | Display order, curator-set in v2 |
| `managed_by_company_id` | Canonical-doc field; the Company row keeps it, only flags that v1 Album has no source ([04](04-company.md)) |

**Group 2 — no v1 source AND no v2 consumer. DROP the column.**

| Column | Why drop |
|---|---|
| `media_kit` | Not in the canonical doc, not in real v1 Album, no v2 feature attached |
| `additional_info` | Same |
| `sustainability` | Same |

Recommended: **drop Group 2, keep Group 1 and stop populating it from v1.**
If the pasted Album schema was partial rather than complete, this reverses —
hence the decision flag.

The script's `isActive → live` fallback (line 326) is doing real work today; if
`status` has genuinely no v1 source, decide explicitly whether every migrated
collection starts at `draft`.

---

## ⚠️ The `directories` M2M dedupe rule is still unwritten

> "Migration needs a dedupe/pick-primary rule for any v1 rows with more than one
> directory set."

`directory_album.py` line 295 silently takes `dirs[0]`:

```python
ct_id = dir_id_to_ct.get(dirs[0]["id"], default_ct_id) if dirs else default_ct_id
```

That is an implicit "first wins" with no logging of multi-directory albums. The
tracker asks for an explicit rule. Minimum fix: count and report albums with
`len(dirs) > 1` so the pick can be reviewed.

---

## `postcards` (the album split)

Not a tracker row — this is a 2026-08-11 implementation decision recorded in the
script: albums under a **non-dedicated** collection type
(Restaurants / Events / Shopping) become postcards, not collections, because
those types have no Collection layer.

This is consistent with the tracker, which routes Restaurants/Events/Shopping
facet assignments to `owned_type = postcard`.

| Action | Note |
|---|---|
| **DROP** `postcards.city_id` from the INSERT | X1 |
| **ADD** `postcards.user_id` write | R3 — from the album's `user` |
| **Keep** the `dropped_on_postcard` manual-review list | It reports `media_kit`, `additionalInfo`, `sustainability`, `seo`, `companySlug`, `company` — three of which D5 retires anyway |

⚠️ `postcards` has **no `seo` column** while `collections` does. An album that
becomes a postcard loses its `seo` silently (it is reported, not migrated). The
tracker calls SEO a *"reusable component, attachable wherever dynamic SEO is
needed (not Collection-only)"* — which argues for **adding `postcards.seo`
(Json?)**. Flagging as a gap.

---

## Target model changes

```
model Collection {
  ...
  cityId             BigInt?  @map("city_id")            // DROP (X1)
  mediaKit           String?  @map("media_kit")          // DROP (D5, group 2)
  additionalInfo     String?  @map("additional_info")    // DROP (D5, group 2)
  sustainability     String?                             // DROP (D5, group 2)

  signature          String?                             // ADD
  gallery            Json?                               // ADD — repeatable {category, images[]}
  ownerUserId        BigInt?  @map("owner_user_id")      // ADD (R3)
  assignedToUserId   BigInt?  @map("assigned_to_user_id")// ADD (R3)

  owner      User? @relation("CollectionOwner",    fields: [ownerUserId],      references: [id])
  assignedTo User? @relation("CollectionAssignee", fields: [assignedToUserId], references: [id])
  @@index([collectionTypeId])
  @@index([countryId, regionId, localityId])              // city_id removed from the index
}
```

`User` needs two back-relations: `ownedCollections`, `assignedCollections`.

---

## Script impact

| Change | Where |
|---|---|
| Remove `city_id` from both INSERT column lists | `migrate_albums()` |
| Add `signature` → new column | `migrate_albums()` collection branch |
| Add `galleryCollection` → `gallery` Json (needs `populate` widening) | `migrate_albums()` |
| Add `user` → `owner_user_id`, `assignTo` → `assigned_to_user_id` via `legacy_user_id_map` | both branches |
| Remove `media_kit` / `additional_info` / `sustainability` writes (D5) | collection branch |
| Decide the `status` source (D5) | line 326 |
| Log multi-directory albums before picking `dirs[0]` | line 295 |
| `companies` lookup `LOWER(name)` → `LOWER(title)` | `load_lookups()` line 199 |
| Delete the notebook's §6 author/assigned_staff **circles** step | `directory_album_migration.ipynb` — snippets only, per repo rule |

⚠️ `directory_album.py` does not currently load `legacy_user_id_map` at all. It
must, for R3.

---

## Summary of actions

| Action | Target |
|---|---|
| **DROP column** | `collections.city_id` |
| **DROP column** | `collections.media_kit`, `.additional_info`, `.sustainability` *(D5)* |
| **ADD column** | `collections.signature`, `.gallery`, `.owner_user_id`, `.assigned_to_user_id` |
| **ADD relation** | `User.ownedCollections`, `User.assignedCollections` |
| **CONSIDER** | `postcards.seo` *(gap — album→postcard loses seo)* |
| **DECISION D5** | Fate of `status` / `priority` / `managed_by_company_id` + the three Group-2 columns |
| **SCRIPT** | Explicit multi-directory dedupe rule; load the user id map; drop the circles step |
