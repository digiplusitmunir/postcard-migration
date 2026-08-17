# 03 — `media.py` (step 3)

Table: `media`.

Tracker row: **Upload - File → Media**, headed
*"confirmed 2026-08-05: exact match, no field changes"*.

The current `Media` model is explicitly a stub (schema header: *"Media and
Enquiry are referenced by the doc but not defined in it — minimal stub models
are included so relations resolve; extend as needed"*). It keeps 5 fields; the
tracker maps 12. **"Exact match" is not currently true.**

---

## Field mapping

| v1 field | v2 target | Disposition | Current schema | Action |
|---|---|---|---|---|
| `name` | `name` | Direct | ❌ missing | **ADD** `name` (String?) |
| `alternativeText` | `alt` | Direct | ✅ `alt` | **Keep** |
| `caption` | `caption` | Direct | ❌ missing (folded into `alt` as a fallback) | **ADD** `caption` (String?) |
| `url` | `url` | Direct — *"Preserve S3/CDN URL and provider metadata as-is"* | ✅ | **Keep** |
| `formats` | `formats` | Direct | ❌ missing | **ADD** `formats` (Json?) — Strapi's thumbnail/small/medium/large variants |
| `hash` | `hash` | Direct | ❌ missing | **ADD** `hash` (String?) |
| `ext` | `ext` | Direct | ❌ missing | **ADD** `ext` (String?) |
| `mime` | `mime_type` | Direct | ✅ | **Keep** |
| `size` | `size` | Direct | ❌ missing | **ADD** `size` (Decimal? — Strapi stores KB as a float) |
| `provider` | `provider` | Direct | ❌ missing | **ADD** `provider` (String?) |
| `id` (numeric) | `id` (UUID) | Transform — *"Build and retain a permanent old-numeric-ID → new-UUID mapping table"* | `BigInt` autoincrement | **DECISION D2** — see below |
| `width` / `height` | `width` / `height` | *(not in tracker, already migrated)* | ✅ | **Keep** |

Not in the tracker, currently dropped by `media.py`'s docstring: `folder`.
Leave dropped.

---

## Decision D2 — BigInt vs UUID

The tracker asks for a UUID primary key. That cascades to **8 relations across
6 tables**: `Collection.cover_media_id`, `Postcard.cover_media_id`,
`Subcollection.cover_media_id`, `CollectionCluster.cover_media_id`,
`User.profile_pic_id`, `User.cover_image_id`, `Company.icon_media_id`,
`Memory.gallery` (M2M) — plus the new `Country.flag_media_id` and
`Company.cover_image_media_id` this plan adds.

The tracker's stated *purpose* is a permanent legacy-id mapping, which a UUID
does not by itself provide — you still need the mapping table either way.

**Recommendation: keep `BigInt` and add `legacy_id`.**

| Action | Column | Reason |
|---|---|---|
| **ADD** | `legacy_id` (BigInt?, **unique**) | The permanent old-ID → new-ID mapping the tracker actually asks for, stored in-row instead of in a side table |

This also fixes a real weakness in the current script: idempotency keys on
`url`, and the docstring admits *"media.url has no unique constraint, so
idempotency is select-then-insert on url"*. `legacy_id` is a stronger key.

If UUID is a hard external requirement, it must be decided **before** any other
schema pass — it is the one change that cannot be layered on later cheaply.

---

## ⚠️ Behaviour change: legacy duplicates

`media.py` currently collapses legacy files that share a url into one row
(lines 74–76). With `legacy_id` as a unique column that is no longer possible —
two legacy ids cannot both own one row.

Options:
- **(a)** Keep url-collapsing; store only the *first* legacy id. Loses the
  mapping for collapsed duplicates.
- **(b)** Stop collapsing; one `media` row per legacy file. Duplicates the URL
  but preserves every mapping.

The tracker says *"exact match"* and asks for a **permanent** mapping, which
points at **(b)**. Confirm before implementing.

---

## Target model

```
model Media {
  id        BigInt   @id @default(autoincrement())
  legacyId  BigInt?  @unique @map("legacy_id")   // NEW — permanent v1 id mapping
  url       String
  name      String?                              // NEW
  alt       String?                              // = v1 alternativeText
  caption   String?                              // NEW — no longer folded into alt
  mimeType  String?  @map("mime_type")
  ext       String?                              // NEW
  hash      String?                              // NEW
  size      Decimal? @db.Decimal(12, 2)          // NEW — Strapi KB float
  provider  String?                              // NEW
  formats   Json?                                // NEW — thumbnail/small/medium/large
  width     Int?
  height    Int?
  // ... existing back-relations, plus:
  countryFlags       Country[] @relation("CountryFlag")        // NEW (see 02-geo)
  companyCoverImages Company[] @relation("CompanyCoverImage")  // NEW (see 04-company)
  @@map("media")
}
```

---

## Script impact

`media.py` is otherwise sound. Changes needed:

1. Carry the 7 new fields through the INSERT / UPDATE.
2. Stop folding `caption` into `alt` (line 78:
   `alt = f.get("alternativeText") or f.get("caption") or f.get("name")`) —
   each now has its own column. Keep `alt` as `alternativeText` only.
3. Key idempotency on `legacy_id` instead of `url`.
4. Resolve the duplicate-collapsing question above.

### Downstream — the shared `media_id_for` helper

Five scripts carry a near-identical find-or-create helper keyed on url
(`company.py`, `users.py`, `directory_album.py`, `postcard.py`, `journey.py`,
`cityguide.py`). Every one of them inserts with only
`(url, mime_type, alt, width, height)`.

Once the wider column set lands, those inserts create **impoverished** media
rows for any file `media.py` did not already fetch. Two fixes:

- **(a)** Extract the helper into a shared `scripts/_media.py` and widen it once.
- **(b)** Rely on `media.py` having already fetched every file, and treat the
  helper's insert path as an error condition rather than a fallback.

**(a)** is the lower-risk change and removes six copies of the same function.

---

## Summary of actions

| Action | Target |
|---|---|
| **ADD column** | `media.name`, `.caption`, `.formats`, `.hash`, `.ext`, `.size`, `.provider`, `.legacy_id` (unique) |
| **DECISION D2** | BigInt + `legacy_id` (recommended) vs UUID primary key |
| **CONFIRM** | Whether legacy duplicate urls still collapse into one row |
| **SCRIPT** | Split `alt` and `caption`; key on `legacy_id`; extract the shared `media_id_for` helper |
