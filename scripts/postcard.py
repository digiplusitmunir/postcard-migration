"""Postcard migration — legacy Strapi `postcards` -> new `postcards`, plus
tags -> `facet_assignments` (owned_type = 'postcard') via the Experience facet.

Migration step 8 of the run order (run AFTER directory_album.py and
tags_facet.py — it consumes both of their per-environment map files).

Scope decisions
---------------
- `album` -> `collection_id` via `legacy_album_id_map`; `collection_type_id`
  copied from that collection. Postcards with no album migrate with
  collection_id = NULL, defaulted to Properties.
- Albums of a **non-dedicated** collection type (Restaurants/Events/Shopping)
  are themselves postcards now — they are in `legacy_album_postcard_id_map`.
  A legacy postcard hanging off such an album gets `collection_id = NULL` and
  inherits `collection_type_id` + geo from that album-derived postcard. Their
  slugs are reserved so this script never upserts over an album-derived row.
- Postcards whose album is in NEITHER map (Designer Tours) are skipped — they
  belong to the dx-card / Destination Expert migration.
- geo: legacy postcard has only `country`. Resolved country = postcard's country
  (by name) else the parent's. region_id / locality_id inherit from the parent
  only when the parent's country matches the resolved country. (R1: no city.)
- `user` -> `user_id` (R3: a direct FK, NOT a Circle with relationship=author).
  5490 of 6693 legacy postcards carry one.
- `status`: legacy has none — isComplete -> live, else draft.
  published_at = legacy createdAt for live postcards (only timestamp kept).
- `slug`: majority empty in legacy -> generated from name, de-duplicated in-run
  (id-sorted, so `foo-2` suffixes stay stable across re-runs).
- `tags` -> facet_assignments via `legacy_tag_id_map`. The legacy Postcard<->Tag
  M2M is NOT recreated — facets are the single classification mechanism.
- `copyright` (62 rows) and `isFounderStory` (6 rows) are migrated; both were
  previously flagged as having no v2 home.
- Dropped: articleURL (verified empty on all 6693 rows), album_themes (verified
  empty), timestamps except published_at. Handled elsewhere: bookmarks ->
  scripts/follows.py + bookmark.py, memories -> its own step,
  property_itineraries -> journey.py.
- Writes `legacy_postcard_id_map{_dev,_prod}.json` for the bookmark, follow,
  journey and memory migrations.

Idempotent — postcards upsert on slug, assignments ON CONFLICT DO NOTHING.

Usage:
    python scripts/postcard.py
"""

from _common import (MediaResolver, SlugAllocator, attrs, connect, fetch_all,
                     load_map, rel, rel_many, save_map, slugify)


def load_lookups(conn, album_postcard_ids):
    """Collections give collection_type_id + inherited geo; album-derived
    postcards do the same for legacy postcards under a non-dedicated album, and
    their slugs are reserved so this script never overwrites them."""
    with conn.cursor() as cur:
        cur.execute("SELECT id, collection_type_id, country_id, region_id, locality_id FROM collections")
        coll_info = {i: (ct, co, rg, lo) for i, ct, co, rg, lo in cur.fetchall()}
        cur.execute("SELECT LOWER(name), id FROM countries")
        country_by_name = dict(cur.fetchall())
        cur.execute("SELECT slug, id FROM collection_types")
        ct_id_by_slug = dict(cur.fetchall())
        cur.execute(
            "SELECT id, collection_type_id, country_id, region_id, locality_id, slug "
            "FROM postcards WHERE id = ANY(%s)", (list(album_postcard_ids),))
        rows = cur.fetchall()
    pc_info = {i: (ct, co, rg, lo) for i, ct, co, rg, lo, _ in rows}
    reserved_slugs = {s for *_, s in rows}

    print(f"lookups: {len(coll_info)} collections, {len(country_by_name)} countries, "
          f"{len(ct_id_by_slug)} collection_types, "
          f"{len(pc_info)} album-derived postcards (slugs reserved)")
    return coll_info, pc_info, reserved_slugs, country_by_name, ct_id_by_slug


def migrate_postcards(conn, postcards, album_map, album_postcard_map, user_map):
    """Postcard -> postcards. Returns {legacy postcard id: new postcard id}."""
    (coll_info, pc_info, reserved_slugs, country_by_name,
     ct_id_by_slug) = load_lookups(conn, set(album_postcard_map.values()))
    default_ct_id = ct_id_by_slug["properties"]  # fallback for postcards with no album
    media = MediaResolver(conn)

    # album-derived postcards (Restaurants/Events/Shopping) already own their
    # slugs — reserve them so an upsert here can never overwrite those rows
    slugs = SlugAllocator(reserved_slugs, fallback="postcard")

    postcard_map = {}   # legacy postcard id -> new postcard id

    skipped_no_name, skipped_unmigrated_album, no_album = [], [], []
    album_is_postcard, missing_country, unmapped_authors = [], [], set()
    with_author = 0

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

            # R3: author is a direct FK
            author = rel(a.get("user"))
            author_id = None
            if author:
                author_id = user_map.get(author["id"])
                if author_id:
                    with_author += 1
                else:
                    unmapped_authors.add(author["id"])

            slug = slugs.take((a.get("slug") or "").strip() or slugify(name))
            cover_id = media.resolve(cur, rel(a.get("coverImage")))
            status = "live" if a.get("isComplete") else "draft"
            published_at = a.get("createdAt") if status == "live" else None

            cur.execute(
                """
                INSERT INTO postcards
                    (name, intro, slug, story, collection_type_id, collection_id,
                     user_id, country_id, region_id, locality_id, copyright,
                     is_founder_story, is_featured, priority, cover_media_id,
                     status, published_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (slug) DO UPDATE
                SET name = EXCLUDED.name,
                    intro = EXCLUDED.intro,
                    story = EXCLUDED.story,
                    collection_type_id = EXCLUDED.collection_type_id,
                    collection_id = EXCLUDED.collection_id,
                    user_id = EXCLUDED.user_id,
                    country_id = EXCLUDED.country_id,
                    region_id = EXCLUDED.region_id,
                    locality_id = EXCLUDED.locality_id,
                    copyright = EXCLUDED.copyright,
                    is_founder_story = EXCLUDED.is_founder_story,
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
                 ct_id, collection_id, author_id,
                 country_id, region_id, locality_id,
                 (a.get("copyright") or "").strip() or None,
                 bool(a.get("isFounderStory")),
                 bool(a.get("isFeatured")), a.get("priority") or 0,
                 cover_id, status, published_at),
            )
            postcard_map[pc["id"]] = cur.fetchone()[0]

    conn.commit()
    print(f"postcards upserted: {len(postcard_map)}")
    print(f"with author (R3 direct FK): {with_author}")
    print(f"media rows created by this step: {media.created}")
    print(f"skipped (no name): {skipped_no_name}")
    print(f"skipped, album not migrated = Designer Tours ({len(skipped_unmigrated_album)})")
    print(f"no album -> defaulted to Properties, no collection ({len(no_album)})")
    print(f"album is itself a postcard (non-dedicated type) ({len(album_is_postcard)})")
    print(f"MANUAL REVIEW country not found ({len(missing_country)}): {missing_country[:20]}")
    print(f"MANUAL REVIEW legacy authors not in user map ({len(unmapped_authors)}): {sorted(unmapped_authors)[:20]}")
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
            SELECT ct.name, COUNT(p.id), COUNT(p.collection_id),
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
            ("with author",         "SELECT COUNT(*) FROM postcards WHERE user_id IS NOT NULL"),
            ("with copyright",      "SELECT COUNT(*) FROM postcards WHERE copyright IS NOT NULL"),
            ("founder stories",     "SELECT COUNT(*) FROM postcards WHERE is_founder_story"),
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
            print(f"{label:22}: {cur.fetchone()[0]}")


def main():
    conn = connect()

    album_map = load_map("legacy_album_id_map")
    album_postcard_map = load_map("legacy_album_postcard_id_map", required=False)
    tag_map = load_map("legacy_tag_id_map")
    user_map = load_map("legacy_user_id_map")
    print(f"loaded {len(album_map)} album->collection, {len(album_postcard_map)} album->postcard, "
          f"{len(tag_map)} tag, {len(user_map)} user mappings")

    postcards = sorted(fetch_all("/api/postcards", {"populate": "*"}), key=lambda x: x["id"])
    print(f"fetched {len(postcards)} postcards")

    postcard_map = migrate_postcards(conn, postcards, album_map, album_postcard_map, user_map)
    assign_facets(conn, postcards, postcard_map, tag_map)
    save_map("legacy_postcard_id_map", postcard_map, "postcard -> postcard")

    verify(conn)
    conn.close()


if __name__ == "__main__":
    main()
