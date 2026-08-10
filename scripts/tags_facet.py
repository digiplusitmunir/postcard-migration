"""Tags facet migration — legacy Strapi `tags` -> FacetType 'Experience' +
`facet_values` (tracker row #2).

Migration step 7 of the run order. Independent of geo/media/company/users —
only needs the DB (schema deployed + seed.py run).

Scope decisions (2026-08-05, confirmed in tracker):
- All tags land under ONE facet type named **Experience** (`experience`),
  applies_to_collection_type_id = NULL (applies broadly),
  allows_multiple = TRUE (a postcard has many experiences).
- Owned by Postcard only — FacetAssignments use owned_type = 'postcard'.
  Property-level filtering rolls up from child postcards at query time; no
  direct Collection-level assignment (unlike Theme).
- FacetAssignments are NOT created here — postcards aren't migrated yet
  (tracker #16 depends on Album + Tag). This script saves
  `legacy_tag_id_map_dev.json` / `_prod.json` (legacy tag id -> facet_value
  id, suffix from the DB name in DATABASE_URL); the postcard migration
  creates the assignments from each postcard's `tags` relation.
- Duplicate tag names (8 pairs, e.g. `buddhist temple` x2) are merged: both
  legacy ids map to the same facet_value. Processing is id-sorted so the
  merge is stable across re-runs (lowest legacy id wins).
- `tag_group` has no home in the facet schema — the linkage is preserved to
  `legacy_tag_groups_dev.json` / `_prod.json` for tracker row #29
  (Tag-group) to decide on later; nothing is written to the DB for groups.
- Dropped: `follow_tags` (blocked Circle work, tracker #26),
  createdAt/updatedAt (Strapi housekeeping).
- The new `tags` TABLE is a different thing (curated postcard feature tags +
  persona tags, seeded by seed.py) — legacy tags do NOT go there.

The same logic lives in `notebooks/tags_facet_migration.ipynb` for
interactive runs. Idempotent — upserts on slug keys. Safe to re-run.

Usage:
    python scripts/tags_facet.py
"""

import json
import os
import re
from pathlib import Path

import requests
import psycopg
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

CMS_BASE_URL = os.environ["CMS_BASE_URL"].rstrip("/")
HEADERS = {"Authorization": f"Bearer {os.environ['CMS_API_TOKEN']}"}
DATABASE_URL = os.environ["DATABASE_URL"]

# map files are suffixed per environment, keyed off the DB name in DATABASE_URL
ENV_SUFFIX = {"development": "_dev", "production": "_prod"}.get(DATABASE_URL.rsplit("/", 1)[-1], "")


def slugify(text):
    return re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-") or None


def attrs(item):
    """Entry fields — Strapi v4 nests them under 'attributes', v5 is flat."""
    return item.get("attributes", item)


def rel(obj):
    """Unwrap a populated relation — v4: {'data': {'attributes': {...}}}, v5: flat dict."""
    if isinstance(obj, dict) and "data" in obj:
        obj = obj["data"]
    if not obj:
        return None
    return obj.get("attributes", obj)


def fetch_all(path, params=None):
    """Fetch every page of a Strapi collection endpoint (data/meta envelope)."""
    items, page = [], 1
    while True:
        p = {"pagination[page]": page, "pagination[pageSize]": 100, "sort": "id", **(params or {})}
        r = requests.get(f"{CMS_BASE_URL}{path}", headers=HEADERS, params=p, timeout=120)
        r.raise_for_status()
        body = r.json()
        items.extend(body["data"])
        pg = body.get("meta", {}).get("pagination", {})
        if page >= pg.get("pageCount", 1):
            return items
        page += 1


def upsert_experience_facet_type(conn):
    """One facet_types row, upserted on slug. Distinct from 'Experience Theme'
    (Theme is assigned at Collection level, Experience only at Postcard level)."""
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO facet_types (name, slug, applies_to_collection_type_id, allows_multiple)
            VALUES ('Experience', 'experience', NULL, TRUE)
            ON CONFLICT (slug) DO UPDATE
            SET name = EXCLUDED.name,
                applies_to_collection_type_id = EXCLUDED.applies_to_collection_type_id,
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
    print(f"merged duplicates ({len(merged)}): {merged}")   # expect 8
    print(f"skipped (no name): {skipped_no_name}")           # expect []
    return tag_to_facet_value


def save_maps(tags, groups, tag_to_facet_value):
    out = ROOT / f"legacy_tag_id_map{ENV_SUFFIX}.json"
    out.write_text(json.dumps({str(k): str(v) for k, v in tag_to_facet_value.items()}, indent=2))
    print(f"saved {len(tag_to_facet_value)} legacy->new tag id mappings to {out}")

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
        cur.execute("SELECT id, name, slug, applies_to_collection_type_id, allows_multiple FROM facet_types ORDER BY id")
        for row in cur.fetchall():
            print("facet_type:", row)
        for label, q in [
            ("experience values",   "SELECT COUNT(*) FROM facet_values WHERE facet_type_id = %s"),
            ("assignments (want 0)", "SELECT COUNT(*) FROM facet_assignments WHERE facet_value_id IN (SELECT id FROM facet_values WHERE facet_type_id = %s)"),
            ("dup slugs (want 0)",  "SELECT COUNT(*) FROM (SELECT slug FROM facet_values WHERE facet_type_id = %s GROUP BY slug HAVING COUNT(*) > 1) d"),
        ]:
            cur.execute(q, (ft_id,))
            print(f"{label:20}: {cur.fetchone()[0]}")


def main():
    conn = psycopg.connect(DATABASE_URL)
    print("connected to:", DATABASE_URL.rsplit("/", 1)[-1])

    tags = sorted(fetch_all("/api/tags", {"populate": "tag_group"}), key=lambda t: t["id"])
    print(f"fetched {len(tags)} tags")
    groups = fetch_all("/api/tag-groups")
    print(f"fetched {len(groups)} tag_groups:", [attrs(g).get("name") for g in groups])

    ft_id = upsert_experience_facet_type(conn)
    tag_to_facet_value = migrate_tags(conn, tags, ft_id)
    save_maps(tags, groups, tag_to_facet_value)

    verify(conn, ft_id)
    conn.close()


if __name__ == "__main__":
    main()
