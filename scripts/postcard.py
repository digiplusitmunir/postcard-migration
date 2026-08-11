"""Postcard migration — legacy Strapi `postcards` -> new `postcards`, plus
tags -> `facet_assignments` (owned_type = 'postcard') via the Experience
facet (tracker row #16).

Migration step 8 of the run order (run AFTER directory_album.py and
tags_facet.py — it consumes both of their per-environment map files).

Scope decisions (2026-08-07, album split added 2026-08-11):
- `album` -> `collection_id` via `legacy_album_id_map_dev/_prod.json`;
  `collection_type_id` copied from that collection. Postcards with
  no album migrate with collection_id = NULL, defaulted to Properties.
- Albums of a **non-dedicated** collection type (Restaurants/Events/
  Shopping) are themselves postcards now — they are in
  `legacy_album_postcard_id_map_dev/_prod.json`, not in the collection map.
  A legacy postcard hanging off such an album gets `collection_id = NULL`
  and inherits `collection_type_id` + geo from that album-derived postcard
  (0 such postcards in prod, 6 in dev — kept for completeness).
  Their slugs are also reserved so this script never upserts over an
  album-derived postcard row.
- Postcards whose album is in NEITHER map (Designer Tours) are skipped —
  they belong to the dx-card / Destination Expert migration (#11/#13).
- `collection_id` is kept for every postcard whose album became a
  collection — the linkage is preserved rather than thrown away; geo is
  ALSO set directly.
- geo: legacy postcard has only `country`. Resolved country = postcard's
  country (by name, how geo migrated) else the parent's. region_id /
  locality_id inherit from the parent only when the parent's country
  matches the resolved country. city_id stays NULL.
- `status`: legacy has none — isComplete -> live, else draft.
  published_at = legacy createdAt for live postcards (only timestamp kept).
- `slug`: majority empty in legacy -> generated from name, de-duplicated
  in-run (id-sorted, so `foo-2` suffixes stay stable across re-runs).
- `tags` -> facet_assignments via `legacy_tag_id_map_dev/_prod.json`.
- author circles are NOT created here — that optional step lives only in
  `notebooks/postcard_migration.ipynb` (section 6).
- Dropped: articleURL (empty everywhere), isFounderStory (no v2 home),
  album_themes (empty on postcards), timestamps (except published_at).
  Deferred to their own tracker rows: bookmarks (#18), memories (#19),
  property_itineraries (#31).
- Writes `legacy_postcard_id_map_dev/_prod.json` (legacy postcard id ->
  new id) for the bookmarks/memories migrations.

Idempotent — postcards upsert on slug, assignments ON CONFLICT DO NOTHING.
Safe to re-run.

Usage:
    python scripts/postcard.py
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


def rel_many(obj):
    """Unwrap a populated to-many relation into a list of flat dicts."""
    if isinstance(obj, dict) and "data" in obj:
        obj = obj["data"]
    return [attrs(x) for x in (obj or [])]


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


def load_map(name, required=True):
    path = ROOT / f"{name}{ENV_SUFFIX}.json"
    if not required and not path.exists():
        return {}
    return {int(k): int(v) for k, v in json.loads(path.read_text()).items()}


def load_lookups(conn, album_postcard_ids):
    """Collections give collection_type_id + inherited geo; album-derived
    postcards do the same for legacy postcards under a non-dedicated album,
    and their slugs are reserved so this script never overwrites them.
    Countries by name (how geo migrated); media by normalized url (same as
    scripts/media.py)."""
    with conn.cursor() as cur:
        cur.execute("SELECT id, collection_type_id, country_id, region_id, locality_id FROM collections")
        coll_info = {i: (ct, co, rg, lo) for i, ct, co, rg, lo in cur.fetchall()}
        cur.execute("SELECT LOWER(name), id FROM countries")
        country_by_name = dict(cur.fetchall())
        cur.execute("SELECT slug, id FROM collection_types")
        ct_id_by_slug = dict(cur.fetchall())
        cur.execute("SELECT url, id FROM media")
        media_by_url = dict(cur.fetchall())
        cur.execute(
            "SELECT id, collection_type_id, country_id, region_id, locality_id, slug "
            "FROM postcards WHERE id = ANY(%s)", (list(album_postcard_ids),))
        rows = cur.fetchall()
    pc_info = {i: (ct, co, rg, lo) for i, ct, co, rg, lo, _ in rows}
    reserved_slugs = {s for *_, s in rows}

    print(f"lookups: {len(coll_info)} collections, {len(country_by_name)} countries, "
          f"{len(ct_id_by_slug)} collection_types, {len(media_by_url)} media, "
          f"{len(pc_info)} album-derived postcards (slugs reserved)")
    return coll_info, pc_info, reserved_slugs, country_by_name, ct_id_by_slug, media_by_url


def migrate_postcards(conn, postcards, album_map, album_postcard_map):
    """Postcard -> postcards. Returns {legacy postcard id: new postcard id}."""
    (coll_info, pc_info, reserved_slugs, country_by_name,
     ct_id_by_slug, media_by_url) = load_lookups(conn, set(album_postcard_map.values()))
    default_ct_id = ct_id_by_slug["properties"]  # fallback for postcards with no album

    def media_id_for(image, cur):
        """Find-or-create a media row for a populated Strapi file."""
        if not image or not image.get("url"):
            return None
        url = image["url"].strip()
        if url.startswith("/"):
            url = CMS_BASE_URL + url
        if url in media_by_url:
            return media_by_url[url]
        cur.execute(
            "INSERT INTO media (url, mime_type, alt, width, height) VALUES (%s, %s, %s, %s, %s) RETURNING id",
            (url, image.get("mime"), image.get("alternativeText") or image.get("name"),
             image.get("width"), image.get("height")),
        )
        media_by_url[url] = cur.fetchone()[0]
        return media_by_url[url]

    # album-derived postcards (Restaurants/Events/Shopping) already own their
    # slugs — reserve them so an upsert here can never overwrite those rows
    used_slugs = set(reserved_slugs)

    def unique_slug(base):
        base = base or "postcard"
        slug, n = base, 2
        while slug in used_slugs:
            slug = f"{base}-{n}"
            n += 1
        used_slugs.add(slug)
        return slug

    postcard_map = {}   # legacy postcard id -> new postcard id

    skipped_no_name, skipped_unmigrated_album, no_album = [], [], []
    album_is_postcard, missing_country = [], []

    with conn.cursor() as cur:
        for pc in postcards:
            a = attrs(pc)
            name = (a.get("name") or "").strip()
            if not name:
                skipped_no_name.append(pc["id"])
                continue

            # album -> collection (+ its type and geo); an album of a
            # non-dedicated type is itself a postcard -> no collection to point at
            album = rel(a.get("album"))
            collection_id = ct_id = None
            c_country = c_region = c_locality = None
            if album:
                collection_id = album_map.get(album["id"])
                if collection_id:
                    ct_id, c_country, c_region, c_locality = coll_info[collection_id]
                elif album["id"] in album_postcard_map:
                    parent_pc_id = album_postcard_map[album["id"]]
                    ct_id, c_country, c_region, c_locality = pc_info[parent_pc_id]
                    album_is_postcard.append((pc["id"], name, album.get("name")))
                else:  # Designer Tours album -> dx-card migration later
                    skipped_unmigrated_album.append((pc["id"], name, album.get("name")))
                    continue
            else:
                no_album.append((pc["id"], name))
                ct_id = default_ct_id

            # geo: postcard country (by name) wins, else collection's; region/locality
            # inherit from the collection only when its country matches
            country = rel(a.get("country"))
            country_id = country_by_name.get((country.get("name") or "").strip().lower()) if country else None
            if country and not country_id:
                missing_country.append((pc["id"], country.get("name")))
            country_id = country_id or c_country
            region_id = c_region if (country_id and country_id == c_country) else None
            locality_id = c_locality if (country_id and country_id == c_country) else None

            slug = unique_slug((a.get("slug") or "").strip() or slugify(name))
            cover_id = media_id_for(rel(a.get("coverImage")), cur)
            status = "live" if a.get("isComplete") else "draft"
            published_at = a.get("createdAt") if status == "live" else None

            cur.execute(
                """
                INSERT INTO postcards
                    (name, intro, slug, story, collection_type_id, collection_id,
                     country_id, region_id, city_id, locality_id, copyright,
                     is_featured, priority, cover_media_id, status, published_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NULL, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (slug) DO UPDATE
                SET name = EXCLUDED.name,
                    intro = EXCLUDED.intro,
                    story = EXCLUDED.story,
                    collection_type_id = EXCLUDED.collection_type_id,
                    collection_id = EXCLUDED.collection_id,
                    country_id = EXCLUDED.country_id,
                    region_id = EXCLUDED.region_id,
                    locality_id = EXCLUDED.locality_id,
                    copyright = EXCLUDED.copyright,
                    is_featured = EXCLUDED.is_featured,
                    priority = EXCLUDED.priority,
                    cover_media_id = EXCLUDED.cover_media_id,
                    status = EXCLUDED.status,
                    published_at = EXCLUDED.published_at
                RETURNING id
                """,
                (name,
                 (a.get("intro") or "").strip() or None,
                 slug,
                 (a.get("story") or "").strip() or None,
                 ct_id, collection_id,
                 country_id, region_id, locality_id,
                 (a.get("copyright") or "").strip() or None,
                 bool(a.get("isFeatured")), a.get("priority") or 0,
                 cover_id, status, published_at),
            )
            postcard_map[pc["id"]] = cur.fetchone()[0]

    conn.commit()
    print(f"postcards upserted: {len(postcard_map)}")
    print(f"skipped (no name): {skipped_no_name}")
    print(f"skipped, album not migrated = Designer Tours ({len(skipped_unmigrated_album)}): {skipped_unmigrated_album[:10]}")
    print(f"no album -> defaulted to Properties, no collection ({len(no_album)}): {no_album[:20]}")
    print(f"album is itself a postcard (non-dedicated type) -> collection_id NULL, "
          f"type/geo inherited ({len(album_is_postcard)}): {album_is_postcard[:20]}")
    print(f"MANUAL REVIEW country not found ({len(missing_country)}): {missing_country[:20]}")
    return postcard_map


def assign_facets(conn, postcards, postcard_map, tag_map):
    """Each legacy postcard<->tag link -> one facet_assignments row pointing at
    the Experience facet_value from the tags migration."""
    assignments = 0
    unmapped_tags = []
    with conn.cursor() as cur:
        for pc in postcards:
            new_id = postcard_map.get(pc["id"])
            if not new_id:
                continue
            for t in rel_many(attrs(pc).get("tags")):
                fv_id = tag_map.get(t["id"])
                if not fv_id:
                    unmapped_tags.append((pc["id"], t["id"], t.get("name")))
                    continue
                cur.execute(
                    """
                    INSERT INTO facet_assignments (owned_type, owned_id, facet_value_id)
                    VALUES ('postcard', %s, %s)
                    ON CONFLICT (owned_type, owned_id, facet_value_id) DO NOTHING
                    """,
                    (new_id, fv_id),
                )
                assignments += cur.rowcount

    conn.commit()
    print(f"facet_assignments inserted this run: {assignments}")
    print(f"MANUAL REVIEW legacy tags not in map ({len(unmapped_tags)}): {unmapped_tags[:20]}")


def verify(conn):
    with conn.cursor() as cur:
        print(f"{'collection type':22} {'total':>7} {'w/ coll':>8} {'no coll':>8}")
        cur.execute("""
            SELECT ct.name, COUNT(p.id),
                   COUNT(p.collection_id),
                   COUNT(p.id) - COUNT(p.collection_id)
            FROM collection_types ct
            LEFT JOIN postcards p ON p.collection_type_id = ct.id
            GROUP BY ct.id, ct.name ORDER BY MIN(ct.priority)
        """)
        for name, n, with_coll, without in cur.fetchall():
            print(f"{name:22} {n:7} {with_coll:8} {without:8}")
        for label, q in [
            ("postcards total",     "SELECT COUNT(*) FROM postcards"),
            ("with collection",     "SELECT COUNT(*) FROM postcards WHERE collection_id IS NOT NULL"),
            ("album-derived",       "SELECT COUNT(*) FROM postcards WHERE website IS NOT NULL OR event_details IS NOT NULL"),
            ("bad: nonded w/ coll", """
                SELECT COUNT(*) FROM postcards p JOIN collection_types ct ON ct.id = p.collection_type_id
                WHERE ct.has_dedicated_collection = false AND p.collection_id IS NOT NULL"""),
            ("with cover media",    "SELECT COUNT(*) FROM postcards WHERE cover_media_id IS NOT NULL"),
            ("with country",        "SELECT COUNT(*) FROM postcards WHERE country_id IS NOT NULL"),
            ("status = live",       "SELECT COUNT(*) FROM postcards WHERE status = 'live'"),
            ("facet assignments",   "SELECT COUNT(*) FROM facet_assignments WHERE owned_type = 'postcard'"),
            ("postcards w/ facets", "SELECT COUNT(DISTINCT owned_id) FROM facet_assignments WHERE owned_type = 'postcard'"),
            ("dup slugs (want 0)",  "SELECT COUNT(*) FROM (SELECT slug FROM postcards GROUP BY slug HAVING COUNT(*) > 1) d"),
        ]:
            cur.execute(q)
            print(f"{label:20}: {cur.fetchone()[0]}")


def main():
    conn = psycopg.connect(DATABASE_URL)
    print("connected to:", DATABASE_URL.rsplit("/", 1)[-1])

    album_map = load_map("legacy_album_id_map")
    album_postcard_map = load_map("legacy_album_postcard_id_map", required=False)
    tag_map = load_map("legacy_tag_id_map")
    print(f"loaded {len(album_map)} album->collection mappings, "
          f"{len(album_postcard_map)} album->postcard mappings, "
          f"{len(tag_map)} tag mappings ({ENV_SUFFIX or 'no suffix'})")

    postcards = sorted(fetch_all("/api/postcards", {"populate": "*"}), key=lambda x: x["id"])
    print(f"fetched {len(postcards)} postcards")

    postcard_map = migrate_postcards(conn, postcards, album_map, album_postcard_map)
    assign_facets(conn, postcards, postcard_map, tag_map)

    out = ROOT / f"legacy_postcard_id_map{ENV_SUFFIX}.json"
    out.write_text(json.dumps({str(k): str(v) for k, v in postcard_map.items()}, indent=2))
    print(f"saved {len(postcard_map)} legacy->new postcard id mappings to {out}")

    verify(conn)
    conn.close()


if __name__ == "__main__":
    main()
