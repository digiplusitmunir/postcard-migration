# 13 — Tables in the tracker with no migration script yet

Everything below has a tracker row (or an explicit `NEEDS SOURCE SCHEMA`
placeholder) but no entry in `migrate_data.py`'s `STEPS`. Schema changes are
listed so they can land in the same pass; script work is out of scope for now.

---

## `memories` — **Memory → Memory**

| v1 field | v2 target | Disposition | Current | Action |
|---|---|---|---|---|
| `name` / `intro` / `slug` | same | Direct | ✅ | **Keep** |
| `date` | `memory_date` | Direct — *"Nullable, distinct from created_at"* | ✅ | **Keep** |
| `postcard` | `postcard_id` | Direct — *"Nullable — null = standalone memory"* | ✅ | **Keep** |
| `album` / `dx_card` | *(no direct field)* | **Flag** — *"postcard_id is the only content anchor"* | — | **Not migrated.** Memories anchored to an album/dx-card lose their anchor — quantify before load |
| `user` | `user_id` | Direct — *"Already a direct FK — consistent with the Album/Postcard ownership correction"* | ✅ | **Keep** |
| `gallery` | `gallery` | Direct — *"1:N/M2N → Media"* | ✅ M2M | **Keep** |
| `region` / `country` | `region_id` / `country_id` — ***"no city_id, tier removed"*** | Direct | 4 geo FKs | **DROP** `city_id` (X1) |
| `internalUrl` / `signature` | *(no direct field)* | **Flag** | — | **Decision:** add or confirm retired |
| `externalUrl` | `external_url` | Direct | ✅ | **Keep** |
| `shareType` | `share_type` | Direct — *"Canonical enum: private/public/selected"* | ✅ | **Keep** |
| `tagged_users` | `tagged_user_ids` | Direct — *"M2M → User"* | ✅ M2M | **Keep** |

⚠️ `Collection.signature` is being **added** ([06](06-directory-album.md)) while
`Memory.signature` is flagged with no target. Same v1 concept, two different
dispositions — worth reconciling.

**Schema actions:** DROP `memories.city_id`. Decide `internal_url` / `signature`.

---

## `user_events` — **Event → UserEvent**

| v1 field | v2 target | Disposition | Current | Action |
|---|---|---|---|---|
| `event_master` (relation) | `event_type` (enum) | Transform — *"CONFIRMED 2026-08-12: relation collapses to a plain enum — Event-master lookup table not recreated in v2"* | ✅ `UserEventType` | **Keep**. ⚠️ Verify the 7 enum values cover every legacy event_master row |
| `user` | `user_id` | Direct | ✅ | **Keep** |
| `meta` | `metadata` | Direct — *"JSON preserved as-is"* | ✅ | **Keep** |
| `ipAddress` / `ipCountry` / `url` | *(not migrated)* | **Archived** — *"CONFIRMED 2026-08-12: ignored"* | — | **No action** |
| `album` / `postcard` / `following` | `subject_type` + `subject_id` (polymorphic) | Transform — *"v1 models the subject as separate exclusive oneToOne relations instead of a generic pair — migration must detect which one is populated and set subject_type accordingly (collection/postcard/user). 'podcast' CONFIRMED 2026-08-12: ignored, dead feature"* | ✅ `EventSubjectType` | **Keep** — enum already has `collection`, `postcard`, `user` |
| `searchData` | `search_query` | Transform — *"JSON preserved as-is — canonical field name may imply plain string, confirm shape"* | `String?` | **DECISION D11** — see below |

### ⚠️ Decision D11 — `search_query` type

v1 `searchData` is **JSON**; `UserEvent.search_query` is **String?**. Either:
- change the column to `Json?` and preserve the payload, or
- extract the query string and drop the rest.

The tracker says "JSON preserved as-is", which points at `Json?`.

**Schema actions:** possible type change on `user_events.search_query`.

---

## `enquiries` — **(no v1 source) → Enquiry**

New v2-only entity. The current model is a stub and does **not** match the
tracker.

| Tracker field | Disposition | Current | Action |
|---|---|---|---|
| `user_id` | New — who is enquiring | ✅ | **Keep** |
| `subject_type` (enum: subcollection / collection / postcard) + `subject_id` | Transform — *"CONFIRMED 2026-08-12: polymorphic, same pattern as Circle/FacetAssignment/UserEvent — today only Journeys take enquiries, but Properties and Events are expected to need them too. Building this polymorphic from day one avoids a schema change when that happens"* | `subcollection_id` FK ⚠️ | **DROP** `subcollection_id`; **ADD** `subject_type` + `subject_id` |
| `travel_dates` (`start_date` / `end_date`) | New | ❌ | **ADD** both |
| `number_of_travelers` | New | ❌ | **ADD** |
| `message` | New — free text from the form | ✅ | **Keep** |
| `status` (new / in_progress / responded / closed) | New — concierge workflow | `String @default("pending")` ⚠️ | **CHANGE** to enum `EnquiryStatus` |
| `assigned_to_user_id` | *"CONFIRMED 2026-08-12: direct FK (concierge staff), NOT Circle — same ownership pattern as Album/Postcard"* | ❌ | **ADD** (R3) |
| `created_at` | New | ✅ | **Keep** |

⚠️ Dropping `subcollection_id` removes the `Subcollection.enquiries` relation.
`Circle.source_enquiry_id` (used when `relationship = booked`) is unaffected.

```
model Enquiry {
  id                BigInt             @id @default(autoincrement())
  userId            BigInt             @map("user_id")
  subjectType       EnquirySubjectType @map("subject_type")   // ADD
  subjectId         BigInt             @map("subject_id")     // ADD
  startDate         DateTime?          @map("start_date") @db.Date   // ADD
  endDate           DateTime?          @map("end_date")   @db.Date   // ADD
  numberOfTravelers Int?               @map("number_of_travelers")   // ADD
  message           String?
  status            EnquiryStatus      @default(new)          // TYPE CHANGE
  assignedToUserId  BigInt?            @map("assigned_to_user_id")   // ADD (R3)
  createdAt         DateTime           @default(now()) @map("created_at")
  updatedAt         DateTime           @updatedAt @map("updated_at")
  ...
  @@index([subjectType, subjectId])
}

enum EnquiryStatus      { new in_progress responded closed }
enum EnquirySubjectType { subcollection collection postcard }
```

---

## `TravelDiaryEntry` — **(no v1 source)**

> "New v2-only entity — no v1 source, also absent from the canonical doc.
> Blocked on Enquiry's schema being written first — now that Enquiry is designed,
> revisit this next."

**Unblocked** once Enquiry lands. No schema exists yet. `NEEDS SOURCE SCHEMA`.

ℹ️ The Bookmark row mentions *"profile-page 'saved items' queries (e.g. Travel
Diary)"* filtering `Circle` by `(user_id, owned_type)` — so Travel Diary may be a
**view over Circle** rather than its own table. Worth settling before adding a
model.

---

## Destination Expert / Dx-card / Travelogue

The whole Designer Tours branch is skipped by `directory_album.py`
(`SKIP_DIRECTORY_SLUGS = {"mindful-luxury-tours"}`, 59 albums) and by
`postcard.py`. These three tracker rows are its destination.

### `Destination-expert → Collection (Destination Expert)`

| v1 field | v2 target | Disposition |
|---|---|---|
| `name` / `title` / `tagLine` | `name` / `intro` | Transform — *"CONFIRMED 2026-08-12: tagLine folds into intro, no separate field"* |
| `coverImage` | `cover_media_id` | Direct |
| `country` / `region` | `country_id` / `region_id` | Direct |
| `status` | `status` | Transform — *"v1 only has draft/published — map onto the canonical 5-value Collection.status set"* |
| `quotes` / `founderMessage` / `dxSections` | *(no structured target)* | **Archived** — *"CONFIRMED 2026-08-12: archived as-is, not migrated"* |

**No schema change** — `Collection` already covers it, and `seed.py` already
seeds `Destination Expert` with `has_dedicated_collection = true`. ✅

### `Dx-card → Postcard (under Destination Expert)`

| v1 field | v2 target | Disposition |
|---|---|---|
| `name` / `story` / `intro` | same | Direct |
| `coverImage` | `cover_media_id` | Direct |
| `country` / `region` | `country_id` / `region_id` | Direct |
| `tag_group` / `tags` | `FacetAssignment` (`owned_type=postcard`, via `Experience`) | Transform |
| `category` / `environment` | `facet_value_id` | Transform — *"Same Facet transform as Album"* → [12](12-category-environment-facet.md) |

**No schema change** — `Postcard` already covers it.

### `Travelogue → Subcollection (under Destination Expert)`

> "Confirmed to become a Subcollection under Destination Expert, live v1 field
> list not yet pulled." → `NEEDS SOURCE SCHEMA`.

Needs a second `SubcollectionType` seeded (alongside `Journey`) once its fields
are known — see [01](01-seed-types.md).

⚠️ `Subcollection.status` becomes `JourneyStatus` under [09](09-journey.md). If a
Travelogue does not follow the Journey workflow, that enum is mis-named and
mis-scoped. Flagging as a forward risk.

---

## `Users-Permissions-Role` — lookup only

> "Not migrated as its own table — lookup only, used in the Users-Permissions-User
> step."

**No action.** `users.py` already resolves the role through
`/api/user-types`. ✅

---

## `Tag-group → FacetType or FacetValue`

`NEEDS SOURCE SCHEMA`. `tags_facet.py` preserves the linkage to
`legacy_tag_groups{_dev,_prod}.json` and writes nothing. See
[07](07-tags-facet.md).

---

## Summary of schema actions from this file

| Action | Target |
|---|---|
| **DROP column** | `memories.city_id` |
| **DROP column** | `enquiries.subcollection_id` |
| **ADD column** | `enquiries.subject_type`, `.subject_id`, `.start_date`, `.end_date`, `.number_of_travelers`, `.assigned_to_user_id` |
| **CHANGE type** | `enquiries.status` → enum `EnquiryStatus` |
| **ADD enum** | `EnquiryStatus`, `EnquirySubjectType` |
| **DECISION D11** | `user_events.search_query` — String vs Json |
| **DECIDE** | `memories.internal_url` / `.signature` — add or confirm retired |
| **VERIFY** | `UserEventType` covers every legacy `event_master` value |
| **NO CHANGE** | Destination Expert, Dx-card (Collection/Postcard already suffice) |
| **BLOCKED** | Travelogue, TravelDiaryEntry, Tag-group — need source schemas |
