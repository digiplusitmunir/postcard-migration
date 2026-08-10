# Tags Facet Migration

Everything about migrating legacy Strapi `tags` into the facet system —
**FacetType 'Experience' + facet_values** (tracker row **#2**). Executed by
`scripts/tags_facet.py` (step 7 of `scripts/migrate_data.py`); the same
logic lives in `notebooks/tags_facet_migration.ipynb` for interactive runs.

## How tags fit the facet system

The old schema had a dedicated table per classification concept (Tag,
Tag-group, Category, Environment, themes...). The new schema replaces all of
them with one generic three-level mechanism:

| Level | Table | Role | Here |
|---|---|---|---|
| dimension | `facet_types` | "what kind of classification" | one row: **Experience** |
| options | `facet_values` | allowed values in a dimension | one per legacy tag (`camel riding`, ...) |
| attachment | `facet_assignments` | polymorphic join onto a collection **or** postcard | **not created here** — postcard migration does it |

Scope decisions (2026-08-05, confirmed in tracker):

- All tags land under **one** facet type: name `Experience`, slug
  `experience`, `applies_to_collection_type_id = NULL` (applies broadly),
  `allows_multiple = TRUE`.
- **Owned by Postcard only** — assignments will use `owned_type='postcard'`.
  Property-level filtering rolls up from child postcards at query time; no
  direct Collection-level assignment (**unlike Theme**).
- Distinct from the `tags` **table** in the new schema (curated postcard
  feature tags + persona tags) — legacy tags do **not** go there.

## Field mapping — Tag

Legacy `api::tag.tag` (730 rows) → new `facet_values`.

| Legacy field | New home | Notes |
|---|---|---|
| `id` | → `legacy_tag_id_map_dev.json` / `_prod.json` | legacy tag id → facet_value id; the **postcard migration needs it** to create assignments from each postcard's `tags` relation. Suffix from the DB name in `DATABASE_URL` |
| `name` | `facet_values.name` | trimmed, otherwise as-is (legacy is lowercase); tags without a name are skipped → printed list |
| — (no slug in legacy) | `facet_values.slug` | **generated** by slugify(name), unique per facet type |
| `tag_group` | **not stored in DB** — preserved to `legacy_tag_groups_dev.json` / `_prod.json` | the facet schema has no grouping level between FacetType and FacetValue; the file keeps group definitions + per-tag membership for tracker **#29 (Tag-group)** to decide on later. 10 groups; 49 tags have none |
| `follow_tags` | — | **dropped** — blocked Circle work (tracker #26) |
| `createdAt/updatedAt` | — | dropped — Strapi housekeeping |

### Duplicate names are merged

8 tag names exist twice in legacy (`buddhist temple`, `tuk tuk ride`,
`helicopter ride`, `gandola ride`, `balinese culture`, `moroccan cuisine`,
`adventure park visit`, `open air cinema`). Each pair merges into **one**
facet_value; both legacy ids map to the shared row, so postcard assignments
from either copy land on the merged value. Processing is id-sorted, so the
merge is stable across re-runs (lowest legacy id wins).

## Idempotency

`facet_types` upserts on `slug`, `facet_values` on
`(facet_type_id, slug)`. Safe to re-run.

## What needs manual work — checklist

1. **Tag-group decision (tracker #29)** — group linkage lives only in
   `legacy_tag_groups_*.json`; when #29 resolves (groups → FacetTypes or
   FacetValues), that file is the input.
2. **Merged duplicates** — review the 8 printed merges; if any pair is
   actually two different concepts, split them by hand.
3. **Assignments** — created by the postcard migration
   (`owned_type='postcard'`) via the tag id map; verify counts there.

## Verification

The script ends with facet-type rows and counts. Expected: 730 legacy tags →
**722 facet_values** (8 merged), 730 map entries, `experience` with
`allows_multiple = TRUE`, 0 assignments (postcards not migrated yet),
0 duplicate slugs.

## Run order

```text
seed → ... → scripts/tags_facet.py → postcards migration
```

Only needs the schema + `seed.py` (independent of geo/media/company/users),
but must run **before** the postcards migration — tracker #16 (Postcard)
depends on Album + Tag, and the assignments are created there from
`legacy_tag_id_map_*.json`. Or just run `python scripts/migrate_data.py`,
which sequences everything and stops on the first failure.
