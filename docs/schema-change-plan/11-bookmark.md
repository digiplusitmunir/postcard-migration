# 11 — `bookmark.py` (step 11)

Table: `circles`.

Tracker rows: **Bookmark → Circle (bookmark)** plus the six **Follow-\*** rows,
all resolved by **R4**.

Good news: the schema is almost right and the script is correct. The work here is
**one index** and **six more migration passes**.

---

## `circles` — field mapping

| v1 field | v2 target | Disposition | Current | Action |
|---|---|---|---|---|
| `user` / `postcard` | `user_id` / `owned_id` (`owned_type=postcard`) | Direct — *"relationship='bookmark'. Matches canonical Circle enum exactly"* | ✅ | **Keep** |
| `createdAt` | `added_at` | *(script decision)* | ✅ | **Keep** |
| `updatedAt` | *(not migrated)* | Dropped — *"meaningless for a bookmark"* | ✅ | **Keep dropped** |

---

## R4 — all seven v1 tables collapse into one relationship value

> "CONFIRMED 2026-08-12: Bookmark and ALL SIX Follow-* tables are the SAME
> action — collapse into this one relationship value, differentiated only by
> owned_type. **No separate 'follow' enum value exists.**"

| v1 table | `owned_type` | `relationship` | Migrated today |
|---|---|---|---|
| `bookmarks` | `postcard` | `bookmark` | ✅ `bookmark.py` |
| `follows` (user→user) | `user` | `bookmark` | ❌ |
| `follow_albums` | `collection` | `bookmark` | ❌ |
| `follow_companies` | `company` | `bookmark` | ❌ |
| `follow_tags` | `tag` | `bookmark` | ❌ |
| `follow_city_guides` | `collection_cluster` | `bookmark` | ❌ |
| `follow_affiliates` | `collection_cluster` | `bookmark` | ❌ |

`CircleOwnedType` already contains all seven targets. **No enum change needed
for R4** — this is the one revision the schema accidentally already supports.

⚠️ `follow_city_guides` and `follow_affiliates` both map to
`collection_cluster`. They are disambiguated by the target cluster's own
`cluster_type_id`, so nothing is lost — but note the `@@unique([userId,
ownedType, ownedId, relationship])` key means a user cannot follow the same
cluster "twice" in different senses. That is correct behaviour, not a bug.

### Six new migration passes

Each is a near-copy of `bookmark.py` with a different `owned_type` and a
different id map:

| Script | Needs map | Produced by |
|---|---|---|
| `follow_user.py` | `legacy_user_id_map` | `users.py` ✅ |
| `follow_album.py` | `legacy_user_id_map`, `legacy_album_id_map` | `directory_album.py` ✅ |
| `follow_company.py` | `legacy_user_id_map`, **company map** | ❌ **`company.py` writes no id map** |
| `follow_tag.py` | `legacy_user_id_map`, `legacy_tag_id_map` | `tags_facet.py` ✅ |
| `follow_cityguide.py` | `legacy_user_id_map`, `legacy_cityguide_id_map` | `cityguide.py` ✅ |
| `follow_affiliate.py` | `legacy_user_id_map`, affiliate/cluster map | ❌ Affiliation is **Deferred - Backup** |

⚠️ **Gap: `company.py` produces no `legacy_company_id_map`.** It keys companies
by slugified name, which `users.py` and `directory_album.py` then re-match by
name — fragile, and insufficient for `follow_companies`. Recommend adding a map
file to `company.py` in the same pass, consistent with every other script.

**Recommended shape:** rather than six near-identical scripts, one
`follows.py` parameterised over a table of
`(endpoint, target_relation_field, owned_type, id_map_name)`. It keeps the
"they are all the same action" decision visible in the code.

⚠️ `follow_affiliates` is blocked — Affiliation sits in the tracker's
*Deferred - Backup* tab and no `CollectionCluster` rows of that type exist yet.

---

## ⚠️ R3 — `CircleRelationship` loses three values

> "OWNERSHIP CHANGE 2026-08-12: Circle is reserved for follow/bookmark
> engagement only — ownership/assignment (user/assignTo) fields are direct FKs,
> not Circle."

```
enum CircleRelationship {
  author           // DELETE -> Postcard.user_id, Subcollection.created_by_user_id
  assigned_staff   // DELETE -> Collection.assigned_to_user_id
  owner            // DELETE -> Collection.owner_user_id
  bookmark         // keep
  booked           // keep
}
```

The optional notebook sections that write `author` / `assigned_staff` circles
(`directory_album_migration.ipynb` §6, `postcard_migration.ipynb` §6,
`journey_migration.ipynb` §6) must be **removed**, not adapted — per the repo
rule, as paste-able cell snippets rather than direct `.ipynb` edits.

`booked` stays: it is member engagement, and `Circle.sequence_date` /
`source_enquiry_id` exist for it.

---

## ⚠️ The required index is missing

> "QUERY PATTERN LOCKED 2026-08-12: profile-page 'saved items' queries (e.g.
> Travel Diary) filter Circle by (user_id, owned_type) — needs a composite index
> on Circle(user_id, owned_type) to stay fast."

Current indexes:

```
@@index([userId, relationship, ownedType])   // relationship sits in the middle
@@index([ownedType, ownedId])
```

A B-tree on `(user_id, relationship, owned_type)` **cannot** serve a
`WHERE user_id = ? AND owned_type = ?` predicate efficiently — the middle column
is unconstrained, so it degrades to a scan of the user's rows.

**ADD** `@@index([userId, ownedType])`.

Once R4 collapses everything to `relationship = 'bookmark'`, the existing
three-column index has near-zero selectivity on its middle column anyway.
Consider whether it still earns its keep.

The tracker adds a note worth carrying into the query layer:

> "Further filters (country/region/interest) join to the target entity — note
> `Postcard.country_id` is only reliable when `collection_id` is null, otherwise
> fall back to the parent `Collection.country_id` (same for region)."

---

## Target model changes

```
model Circle {
  ...
  relationship CircleRelationship   // enum loses author/assigned_staff/owner
  @@unique([userId, ownedType, ownedId, relationship])
  @@index([userId, relationship, ownedType])   // reconsider (low selectivity post-R4)
  @@index([userId, ownedType])                 // ADD — locked query pattern
  @@index([ownedType, ownedId])
}
```

---

## Script impact

`bookmark.py` itself needs **no changes** — it is already correct under R4.

| Change | Where |
|---|---|
| Add `legacy_company_id_map` output | `company.py` |
| New `follows.py` (or six scripts) for the six Follow-* tables | new |
| Add the new step(s) to `STEPS` | `migrate_data.py` |
| Remove author/assigned_staff circle sections | three notebooks — snippets only |
| Stale docstrings calling follow work "blocked on the Circle 'follow' relationship value" | `tags_facet.py` line 25, `cityguide.py` line 34 |

---

## Summary of actions

| Action | Target |
|---|---|
| **ADD index** | `circles @@index([userId, ownedType])` |
| **DROP enum values** | `CircleRelationship.author`, `.assigned_staff`, `.owner` *(R3)* |
| **NO CHANGE** | `CircleOwnedType` — already has all seven targets |
| **NO CHANGE** | `bookmark.py` |
| **NEW SCRIPT** | `follows.py` — six Follow-* tables → `relationship='bookmark'` |
| **GAP** | `company.py` produces no legacy id map |
| **BLOCKED** | `follow_affiliates` — Affiliation is Deferred - Backup |
