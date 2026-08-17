# 10 — `cityguide.py` (step 10)

Tables: `collection_clusters`, ~~`collection_cluster_entries`~~.

Tracker rows: **City-guide → CollectionCluster (RE-ANCHORED TO REGION
2026-08-05, not City)** and the `NEEDS SOURCE SCHEMA` block that resolves the
entry-table question.

**This script is built on the City tier and needs a structural rewrite**, not
field edits.

---

## `collection_clusters` — field mapping

| v1 field | v2 target | Disposition | Current | Action |
|---|---|---|---|---|
| `region` | `region_id` | Direct — *"CONFIRMED 2026-08-05: City Guide organized by Region, not City. cluster_type_id = 'City Guide'"* | matched via **`cities`** ⚠️ | **REWRITE** — match `regions` directly |
| `country` | `country_id` | Direct — *"CONFIRMED 2026-08-12: real v1 schema DOES carry country as its own direct relation alongside region — keep denormalized to match v1's own design"* | ✅ | **Keep** |
| `description` | `intro` | Direct — *"Canonical CollectionCluster schema field is 'intro', not 'description'"* | ✅ | **Keep** |
| `image` | `cover_media_id` | Direct — *"RESOLVED 2026-08-12: real schema confirms a single media field"* | ✅ | **Keep** |
| `follow_city_guides` | *(no action — reverse relation)* | Direct — *"satisfied via Circle(owned_type=collection_cluster)"* | dropped ✅ | **Now unblocked** — see [11](11-bookmark.md) |
| `communityLink` | `community_link` | Direct — *"CONFIRMED 2026-08-12: needed, EXTENSION beyond canonical doc — new field, string, carried straight over"* | ✅ | **Keep** |
| `slug` | `slug` | Direct | ✅ | **Keep** |
| `status` | `status` | Transform — *"v1 only has draft/published — map onto whatever the canonical CollectionCluster status enum turns out to be"* | `published → live`, else `draft` ✅ | **Keep** `ContentStatus` |

⚠️ **`name` has no v1 source.** The tracker does not list it. `cityguide.py`
derives it from the matched city's name, falling back to a title-cased slug.
Once the city matching is removed, derive from the matched **region** name
instead — same behaviour, one tier up.

---

## ⚠️ The rewrite: legacy `region` maps to `regions`, not `cities`

The script's core assumption (docstring, lines 9–14):

> "Legacy `region` maps to the new `cities` tier — v2 cities were synthesized
> 1:1 from legacy regions in the geo migration, so the guide's region name is
> matched against cities.name."

With **X1** that entire premise is gone — `geo_migration.py` no longer creates
placeholder cities, and `City` no longer exists.

### What gets deleted

| Delete | Lines |
|---|---|
| `cities_by_name` lookup | `load_lookups()` 121–124 |
| The city-match block + `city_missing` / `city_ambiguous` review lists | `migrate_city_guides()` 189–198, 251–252 |
| `city_id` from the INSERT | 220–223, 230 |
| `city_name` derivation of `name` | 208 |

### What replaces it

```python
# match legacy region name -> regions, scoped by the legacy country when present
cur.execute("SELECT LOWER(name), id, country_id, name FROM regions")
```

Then `region_id` = the match, `country_id` = legacy country by name (falling
back to the matched region's `country_id` — already the existing fallback via
`country_by_region`), and `name` = the matched region's name.

⚠️ Region names are unique per **country**, not globally. Match on
`(name, country_id)` when the legacy country is present; only fall back to
name-alone when it is not, and report ambiguity. The current city match has the
same latent bug.

---

## ⚠️ Decision D8 — `locality_id` on the cluster

The tracker confirms `region_id` and `country_id`. It says nothing about
`locality_id`, which the schema has and `cityguide.py` writes as literal NULL.

City Guide is region-anchored by definition; a locality-anchored cluster type has
not been described. **Recommend dropping `collection_clusters.locality_id`**
alongside `city_id`, and re-adding it only if a future cluster type needs it.

Low-risk either way — it is unpopulated.

---

## ⚠️ Decision D9 — `collection_cluster_entries` is fully derived

The tracker's resolution of the entry-table question is unambiguous:

> "FULLY RESOLVED 2026-08-12 (architecture, not schema): **there is NO join/entry
> table to migrate here.** … Rendering a cluster page = query Collections WHERE
> collection_type_id IN (allowed types) AND [match field] = [cluster's value] —
> **fully derived, not curated.** No v1 source table needed for City Guide;
> CollectionClusterType's allowed-types + match-field config is new v2-only admin
> config, not migrated data."

That directly contradicts the schema's own comment on
`CollectionClusterEntry.priority`: *"curator-controlled display order"*.

`cityguide.py`'s `derive_entries()` (lines 291–346) currently **materializes**
that derived query into rows — precisely the work the tracker says is
unnecessary.

### Options

**(a) Delete the table.** Move derivation to the service layer, driven by
`collection_cluster_types.match_field` + `collection_type_ids` (see
[01](01-seed-types.md)).

- Deletes: model `CollectionClusterEntry`, enum `ClusterEntryType`,
  `CollectionCluster.entries`.
- Deletes from `cityguide.py`: `derive_entries()`, `print_cluster_type_scope()`,
  `OUT_OF_SCOPE_ENTRIES_SQL`, `DERIVE_ENTRIES`, and half of `verify()` —
  roughly 130 of 434 lines.
- **Aligns with the tracker.** Also removes a real maintenance hazard: derived
  rows are inserted `ON CONFLICT DO NOTHING` and **never deleted**, so the
  script already needs a manual "out-of-scope entries" pruning report to cope
  with its own staleness.

**(b) Keep the table as a curation *override* layer.** Derivation stays in the
service layer; the table holds only hand-pinned additions/re-orderings on top.

- Requires an `is_pinned` / `is_excluded` distinction to be meaningful.
- Not described anywhere in the tracker.

**Recommend (a).** It is what the tracker says, it deletes the staleness
problem rather than managing it, and the curation use-case can be re-added later
as an explicit override table if the CMS actually needs one.

If (a) is chosen, `directory_album.py`'s
`drop_stale_nondedicated_collections()` also loses its
`collection_cluster_entries` dependent check (lines 522–528).

---

## Target model changes

```
model CollectionCluster {
  ...
  cityId     BigInt? @map("city_id")      // DROP (X1)
  localityId BigInt? @map("locality_id")  // DROP (D8)
  entries    CollectionClusterEntry[]     // DROP (D9)
}

// model CollectionClusterEntry { ... }   // DELETE ENTIRELY (D9)
// enum  ClusterEntryType { ... }         // DELETE (D9)
```

`managed_by_company_id` stays — it is the anchor for the deferred **Partner
Affiliation** cluster type (`match_field = 'company_id'`).

---

## Script impact — summary

`cityguide.py` becomes substantially smaller:

| Change | Scale |
|---|---|
| Region matching replaces city matching | rewrite of `load_lookups()` + the match block |
| `name` derived from region | one line |
| Drop `city_id` / `locality_id` from the INSERT | column list |
| Delete the whole entry-derivation half of the script (D9) | ~130 lines |
| Add `follow_city_guides` → Circle, or leave to a dedicated script | see [11](11-bookmark.md) |
| Update the docstring — the "legacy region maps to the new cities tier" premise is retired | lines 9–14 |

The `legacy_cityguide_id_map{_dev,_prod}.json` output stays — the
follow-city-guide migration still needs it. ✅

---

## Summary of actions

| Action | Target |
|---|---|
| **DROP column** | `collection_clusters.city_id` |
| **DROP column** | `collection_clusters.locality_id` *(D8)* |
| **DELETE model** | `CollectionClusterEntry` + enum `ClusterEntryType` *(D9)* |
| **DECISION D8** | Keep or drop `locality_id` |
| **DECISION D9** | Delete the entry table vs. keep as a curation override |
| **SCRIPT** | Rewrite region matching; match on `(name, country_id)`; delete the derivation half |
| **DEPENDS ON** | `collection_cluster_types.match_field` from [01](01-seed-types.md) |
