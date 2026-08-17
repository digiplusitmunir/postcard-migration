"""Follow migration — all six legacy Follow-* tables -> `circles`.

Migration step 13 of the run order (run AFTER users, directory_album, postcard,
tags_facet, company and cityguide — it consumes their per-environment map files).

TRACKER REVISION R4 (2026-08-12)
--------------------------------
    "Bookmark and ALL SIX Follow-* tables are the SAME action — collapse into
     this one relationship value, differentiated only by owned_type. No separate
     'follow' enum value exists."

So every row below becomes `relationship = 'bookmark'`; only `owned_type`
differs. `scripts/bookmark.py` handles the seventh table (bookmarks ->
owned_type='postcard') and is unchanged.

  legacy table         user field               target field  -> owned_type
  -------------------  -----------------------  ------------  -------------------
  follows              follower                 following     user
  follow-albums        follower                 album         collection/postcard
  follow-companies     follower                 company       company
  follow-tags          follower                 tag           facet_value
  follow-city-guides   users_permissions_user   city_guide    collection_cluster
  follow-affiliates    follower                 affiliation   collection_cluster

Two wrinkles worth knowing:

- **follow-albums is split.** Since the album split, a followed album is a
  `collection` for Properties but a `postcard` for Restaurants/Events/Shopping.
  This script checks the collection map first, then the album->postcard map, and
  sets owned_type accordingly.
- **follow-city-guides uses a different user field.** It is
  `users_permissions_user`, not `follower`, unlike every other Follow table.
- **follow-affiliates is deferred.** Affiliation is a real legacy entity
  (/api/affiliations) but Partner Affiliation clusters are not migrated yet, so
  there is no cluster id to point at. 84 rows exist (24 with an affiliation
  set); they are counted and reported, not written. Enable by seeding an
  'Affiliation' cluster type, migrating /api/affiliations into
  collection_clusters, and writing legacy_affiliation_id_map.

`createdAt` -> `added_at` (falls back to now()). Duplicate (user, target) pairs
collapse via the Circle unique key — id-sorted + DO NOTHING, so the earliest
createdAt wins. Rows whose user or target is not in its map (deleted users,
Designer Tours content) are skipped -> manual review lists.

Idempotent — ON CONFLICT DO NOTHING on the Circle unique key. Safe to re-run.

Usage:
    python scripts/follows.py
"""

from collections import Counter

from _common import attrs, connect, fetch_all, load_map, rel

# label, endpoint, user field, target field, owned_type, target map name
# owned_type = None means "resolved per row" (follow-albums)
SOURCES = [
    ("follow-user",       "/api/follows",            "follower",
     "following",   "user",               "legacy_user_id_map"),
    ("follow-album",      "/api/follow-albums",      "follower",
     "album",       None,                 None),
    ("follow-company",    "/api/follow-companies",   "follower",
     "company",     "company",            "legacy_company_id_map"),
    # legacy tags became Experience FACET VALUES, not rows in the v2 `tags`
    # table (which is the curated persona vocabulary), so owned_type is
    # 'facet_value' — using 'tag' here would point at the wrong table
    ("follow-tag",        "/api/follow-tags",        "follower",
     "tag",         "facet_value",        "legacy_tag_id_map"),
    ("follow-city-guide", "/api/follow-city-guides", "users_permissions_user",
     "city_guide",  "collection_cluster", "legacy_cityguide_id_map"),
]

# Not migrated yet — see the module docstring.
DEFERRED = [
    ("follow-affiliate", "/api/follow-affiliates", "follower", "affiliation"),
]


def insert_circle(cur, user_id, owned_type, owned_id, created_at):
    cur.execute(
        """
        INSERT INTO circles (user_id, owned_type, owned_id, relationship, added_at)
        VALUES (%s, %s, %s, 'bookmark', COALESCE(%s::timestamptz, now()))
        ON CONFLICT (user_id, owned_type, owned_id, relationship) DO NOTHING
        """,
        (user_id, owned_type, owned_id, created_at),
    )
    return cur.rowcount


def migrate_source(conn, label, endpoint, user_field, target_field, owned_type,
                   map_name, user_map, album_map, album_postcard_map):
    rows = sorted(fetch_all(endpoint, {"populate": "*"}), key=lambda x: x["id"])
    print(f"\n{label}: fetched {len(rows)} rows from {endpoint}")

    # follow-albums resolves its own owned_type per row
    target_map = load_map(map_name) if map_name else None

    inserted = Counter()
    orphans, unmapped_users, unmapped_targets = [], [], []

    with conn.cursor() as cur:
        for row in rows:
            a = attrs(row)
            u, t = rel(a.get(user_field)), rel(a.get(target_field))
            if not u or not t:
                orphans.append((row["id"], "no user" if not u else f"no {target_field}"))
                continue

            new_uid = user_map.get(u["id"])
            if not new_uid:
                unmapped_users.append((row["id"], u["id"], u.get("username")))
                continue

            if owned_type is None:      # follow-albums: collection or postcard?
                if t["id"] in album_map:
                    row_type, new_tid = "collection", album_map[t["id"]]
                elif t["id"] in album_postcard_map:
                    row_type, new_tid = "postcard", album_postcard_map[t["id"]]
                else:
                    unmapped_targets.append((row["id"], t["id"], t.get("name")))
                    continue
            else:
                row_type = owned_type
                new_tid = target_map.get(t["id"])
                if not new_tid:
                    unmapped_targets.append((row["id"], t["id"], t.get("name") or t.get("username")))
                    continue

            if insert_circle(cur, new_uid, row_type, new_tid, a.get("createdAt")):
                inserted[row_type] += 1

    conn.commit()
    total = sum(inserted.values())
    collapsed = len(rows) - total - len(orphans) - len(unmapped_users) - len(unmapped_targets)
    print(f"  circles inserted: {total} {dict(inserted)}")
    print(f"  duplicates collapsed by the unique key: {collapsed}")
    print(f"  skipped orphans ({len(orphans)}): {orphans[:10]}")
    print(f"  MANUAL REVIEW users not in map ({len(unmapped_users)}): {unmapped_users[:10]}")
    print(f"  MANUAL REVIEW targets not in map ({len(unmapped_targets)}): {unmapped_targets[:10]}")
    return total


def report_deferred():
    for label, endpoint, user_field, target_field in DEFERRED:
        rows = fetch_all(endpoint, {"populate": "*"})
        with_target = sum(1 for r in rows if rel(attrs(r).get(target_field)))
        print(f"\n{label}: DEFERRED — {len(rows)} rows ({with_target} with a "
              f"{target_field}). Partner Affiliation clusters are not migrated "
              f"yet, so there is no cluster id to point at. See the docstring.")


def verify(conn):
    with conn.cursor() as cur:
        print("\ncircles by owned_type (relationship = 'bookmark'):")
        cur.execute("""
            SELECT owned_type, COUNT(*), COUNT(DISTINCT user_id)
            FROM circles WHERE relationship = 'bookmark'
            GROUP BY owned_type ORDER BY 2 DESC
        """)
        for owned_type, n, users in cur.fetchall():
            print(f"  {owned_type:20}: {n:6} rows, {users} distinct users")

        for label, q in [
            ("circles total", "SELECT COUNT(*) FROM circles"),
            ("broken postcard refs (want 0)",
             "SELECT COUNT(*) FROM circles c WHERE c.owned_type = 'postcard' "
             "AND NOT EXISTS (SELECT 1 FROM postcards p WHERE p.id = c.owned_id)"),
            ("broken collection refs (want 0)",
             "SELECT COUNT(*) FROM circles c WHERE c.owned_type = 'collection' "
             "AND NOT EXISTS (SELECT 1 FROM collections x WHERE x.id = c.owned_id)"),
            ("broken company refs (want 0)",
             "SELECT COUNT(*) FROM circles c WHERE c.owned_type = 'company' "
             "AND NOT EXISTS (SELECT 1 FROM companies x WHERE x.id = c.owned_id)"),
            ("broken user refs (want 0)",
             "SELECT COUNT(*) FROM circles c WHERE c.owned_type = 'user' "
             "AND NOT EXISTS (SELECT 1 FROM users x WHERE x.id = c.owned_id)"),
            ("broken cluster refs (want 0)",
             "SELECT COUNT(*) FROM circles c WHERE c.owned_type = 'collection_cluster' "
             "AND NOT EXISTS (SELECT 1 FROM collection_clusters x WHERE x.id = c.owned_id)"),
            ("broken facet_value refs (want 0)",
             "SELECT COUNT(*) FROM circles c WHERE c.owned_type = 'facet_value' "
             "AND NOT EXISTS (SELECT 1 FROM facet_values x WHERE x.id = c.owned_id)"),
            ("self-follows (review)",
             "SELECT COUNT(*) FROM circles WHERE owned_type = 'user' AND owned_id = user_id"),
        ]:
            cur.execute(q)
            print(f"{label:34}: {cur.fetchone()[0]}")


def main():
    conn = connect()

    user_map = load_map("legacy_user_id_map")
    album_map = load_map("legacy_album_id_map")
    album_postcard_map = load_map("legacy_album_postcard_id_map", required=False)
    print(f"loaded {len(user_map)} user, {len(album_map)} album->collection, "
          f"{len(album_postcard_map)} album->postcard mappings")

    total = 0
    for label, endpoint, user_field, target_field, owned_type, map_name in SOURCES:
        total += migrate_source(conn, label, endpoint, user_field, target_field,
                                owned_type, map_name, user_map, album_map,
                                album_postcard_map)

    report_deferred()
    print(f"\ntotal follow circles inserted this run: {total}")
    verify(conn)
    conn.close()


if __name__ == "__main__":
    main()
