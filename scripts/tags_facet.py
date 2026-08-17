"""Tags facet migration — legacy Strapi `tags` -> FacetType 'Experience' +
`facet_values`.

Migration step 7 of the run order. Independent of geo/media/company/users —
only needs the DB (schema deployed + seed.py run).

Scope decisions (2026-08-05, confirmed in the tracker):
- All tags land under ONE facet type named **Experience** (`experience`),
  scoped to nothing (applies broadly), allows_multiple = TRUE (a postcard has
  many experiences).
- Owned by Postcard only — FacetAssignments use owned_type = 'postcard'.
  Property-level filtering rolls up from child postcards at query time; there is
  no direct Collection-level assignment for Experience.
- FacetAssignments are NOT created here — postcards aren't migrated yet. This
  script saves `legacy_tag_id_map{_dev,_prod}.json` (legacy tag id ->
  facet_value id); scripts/postcard.py creates the assignments from each
  postcard's `tags` relation.
- Duplicate tag names are merged: both legacy ids map to the same facet_value.
  Processing is id-sorted so the merge is stable across re-runs (lowest legacy
  id wins).
- `tag_group` has no home in the facet schema yet (679 of 728 legacy tags carry
  one, across 10 groups). The linkage is preserved to
  `legacy_tag_groups{_dev,_prod}.json` for the Tag-group tracker row to decide
  on later; nothing is written to the DB for groups.
- The new `tags` TABLE is a different thing — a curated persona-interest
  vocabulary seeded by seed.py and joined through user_persona_tags. Legacy
  content tags do NOT go there, and the old Postcard<->Tag M2M was removed as a
  duplicate classification path.
- Dropped: createdAt/updatedAt (Strapi housekeeping). `follow_tags` is NOT
  dropped — it migrates to circles(owned_type='tag') in scripts/follows.py.

Idempotent — upserts on slug keys. Safe to re-run.

Usage:
    python scripts/tags_facet.py
"""

import json

from _common import (ENV_SUFFIX, ROOT, attrs, connect, fetch_all, rel,
                     save_map, slugify)


def upsert_experience_facet_type(conn):
    """One facet_types row, upserted on slug."""
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO facet_types (name, slug, applies_to_collection_type_id,
                                     applies_to_subcollection_type_id, allows_multiple)
            VALUES ('Experience', 'experience', NULL, NULL, TRUE)
            ON CONFLICT (slug) DO UPDATE
            SET name = EXCLUDED.name,
                applies_to_collection_type_id = EXCLUDED.applies_to_collection_type_id,
                applies_to_subcollection_type_id = EXCLUDED.applies_to_subcollection_type_id,
                allows_multiple = EXCLUDED.allows_multiple
            RETURNING id
            """
        )
        ft_id = cur.fetchone()[0]
    conn.commit()
    print("facet_type 'Experience' id:", ft_id)
    return ft_id


def migrate_tags(conn, tags, ft_id):
    """Tag -> facet_values (dedupe by slug). Returns {legacy tag id: facet_value id}."""
    tag_to_facet_value = {}   # legacy tag id -> facet_value id
    fv_id_by_slug = {}        # slug -> facet_value id (dedupe within the run)
    merged, skipped_no_name = [], []

    with conn.cursor() as cur:
        for t in tags:
            a = attrs(t)
            name = (a.get("name") or "").strip()
            if not name:
                skipped_no_name.append(t["id"])
                continue
            slug = slugify(name)

            if slug in fv_id_by_slug:  # duplicate tag name -> merge onto existing value
                tag_to_facet_value[t["id"]] = fv_id_by_slug[slug]
                merged.append((t["id"], name))
                continue

            cur.execute(
                """
                INSERT INTO facet_values (facet_type_id, name, slug)
                VALUES (%s, %s, %s)
                ON CONFLICT (facet_type_id, slug) DO UPDATE
                SET name = EXCLUDED.name
                RETURNING id
                """,
                (ft_id, name, slug),
            )
            fv_id = cur.fetchone()[0]
            fv_id_by_slug[slug] = fv_id
            tag_to_facet_value[t["id"]] = fv_id

    conn.commit()
    print(f"facet_values upserted: {len(fv_id_by_slug)}")
    print(f"legacy tags mapped   : {len(tag_to_facet_value)}")
    print(f"merged duplicates ({len(merged)}): {merged}")
    print(f"skipped (no name): {skipped_no_name}")
    return tag_to_facet_value


def save_group_linkage(tags, groups):
    groups_out = ROOT / f"legacy_tag_groups{ENV_SUFFIX}.json"
    groups_out.write_text(json.dumps({
        "tag_groups": [
            {"id": g["id"], "name": attrs(g).get("name"), "priority": attrs(g).get("priority")}
            for g in groups
        ],
        "tag_to_group": {
            str(t["id"]): (rel(attrs(t).get("tag_group")) or {}).get("name")
            for t in tags
        },
    }, indent=2))
    print(f"saved tag-group linkage for {len(tags)} tags to {groups_out}")


def verify(conn, ft_id):
    with conn.cursor() as cur:
        cur.execute("SELECT id, name, slug, allows_multiple FROM facet_types ORDER BY id")
        for row in cur.fetchall():
            print("facet_type:", row)
        for label, q in [
            ("experience values",    "SELECT COUNT(*) FROM facet_values WHERE facet_type_id = %s"),
            ("assignments (want 0)", "SELECT COUNT(*) FROM facet_assignments WHERE facet_value_id IN (SELECT id FROM facet_values WHERE facet_type_id = %s)"),
            ("dup slugs (want 0)",   "SELECT COUNT(*) FROM (SELECT slug FROM facet_values WHERE facet_type_id = %s GROUP BY slug HAVING COUNT(*) > 1) d"),
        ]:
            cur.execute(q, (ft_id,))
            print(f"{label:22}: {cur.fetchone()[0]}")


def main():
    conn = connect()

    tags = sorted(fetch_all("/api/tags", {"populate": "tag_group"}), key=lambda t: t["id"])
    print(f"fetched {len(tags)} tags")
    groups = fetch_all("/api/tag-groups")
    print(f"fetched {len(groups)} tag_groups:", [attrs(g).get("name") for g in groups])

    ft_id = upsert_experience_facet_type(conn)
    tag_to_facet_value = migrate_tags(conn, tags, ft_id)
    save_map("legacy_tag_id_map", tag_to_facet_value, "tag -> facet_value")
    save_group_linkage(tags, groups)

    verify(conn, ft_id)
    conn.close()


if __name__ == "__main__":
    main()
