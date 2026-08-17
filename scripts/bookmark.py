"""Bookmark migration — legacy Strapi `bookmarks` -> `circles`
(owned_type='postcard', relationship='bookmark').

Migration step 12 of the run order (run AFTER users.py and postcard.py — it
consumes both of their per-environment map files).

R4 (2026-08-12) confirms bookmarks and all six Follow-* tables are the same
action, distinguished only by owned_type. This script handles the `postcard`
case; scripts/follows.py handles the other six.

- `user` -> user_id, `postcard` -> owned_id, both via the per-env maps.
  Bookmarks whose user or postcard is not in its map (deleted users, Designer
  Tours postcards) are skipped -> manual review lists. The Designer Tours skips
  need a follow-up pass once dx-cards migrate.
- `createdAt` -> added_at (falls back to now() if legacy has none).
- Orphan bookmarks (no user or no postcard relation) are skipped -> printed.
- Legacy duplicate (user, postcard) pairs collapse into one row via the Circle
  unique key — id-sorted + DO NOTHING, so the earliest createdAt wins.
- Dropped: `updatedAt` (meaningless for a bookmark). Nothing else — legacy
  bookmarks carry no other fields.
- `sequence_date` / `source_enquiry_id` stay NULL — those belong to booked
  journeys, not bookmarks.
- No id map file written — nothing downstream references bookmark ids.

Idempotent — ON CONFLICT DO NOTHING on the Circle unique key. Safe to re-run.

Usage:
    python scripts/bookmark.py
"""

from _common import attrs, connect, fetch_all, load_map, rel


def migrate_bookmarks(conn, bookmarks, user_map, postcard_map):
    """bookmark -> circles (owned_type='postcard', relationship='bookmark')."""
    inserted = 0
    orphans, unmapped_users, unmapped_postcards = [], [], []

    with conn.cursor() as cur:
        for bm in bookmarks:
            a = attrs(bm)
            u, p = rel(a.get("user")), rel(a.get("postcard"))
            if not u or not p:
                orphans.append((bm["id"], "no user" if not u else "no postcard"))
                continue

            new_uid = user_map.get(u["id"])
            if not new_uid:  # user not migrated (deleted / skipped)
                unmapped_users.append((bm["id"], u["id"], u.get("username")))
                continue

            new_pid = postcard_map.get(p["id"])
            if not new_pid:  # postcard skipped upstream (Designer Tours)
                unmapped_postcards.append((bm["id"], p["id"], p.get("name")))
                continue

            cur.execute(
                """
                INSERT INTO circles (user_id, owned_type, owned_id, relationship, added_at)
                VALUES (%s, 'postcard', %s, 'bookmark', COALESCE(%s::timestamptz, now()))
                ON CONFLICT (user_id, owned_type, owned_id, relationship) DO NOTHING
                """,
                (new_uid, new_pid, a.get("createdAt")),
            )
            inserted += cur.rowcount

    conn.commit()
    collapsed = len(bookmarks) - inserted - len(orphans) - len(unmapped_users) - len(unmapped_postcards)
    print(f"bookmark circles inserted this run: {inserted}")
    print(f"(duplicates collapsed by the unique key: {collapsed})")
    print(f"skipped orphans ({len(orphans)}): {orphans[:20]}")
    print(f"MANUAL REVIEW legacy users not in map ({len(unmapped_users)}): {unmapped_users[:20]}")
    print(f"MANUAL REVIEW legacy postcards not in map ({len(unmapped_postcards)}): {unmapped_postcards[:20]}")


def verify(conn):
    with conn.cursor() as cur:
        for label, q in [
            ("circles total",            "SELECT COUNT(*) FROM circles"),
            ("postcard bookmarks",       "SELECT COUNT(*) FROM circles WHERE owned_type = 'postcard' AND relationship = 'bookmark'"),
            ("distinct users w/ bkmks",  "SELECT COUNT(DISTINCT user_id) FROM circles WHERE owned_type = 'postcard' AND relationship = 'bookmark'"),
            ("distinct postcards bkmkd", "SELECT COUNT(DISTINCT owned_id) FROM circles WHERE owned_type = 'postcard' AND relationship = 'bookmark'"),
            ("broken postcard refs (want 0)", "SELECT COUNT(*) FROM circles c WHERE c.owned_type = 'postcard' AND c.relationship = 'bookmark' AND NOT EXISTS (SELECT 1 FROM postcards p WHERE p.id = c.owned_id)"),
            ("added_at carried (not today)",  "SELECT COUNT(*) FROM circles WHERE owned_type = 'postcard' AND relationship = 'bookmark' AND added_at < now() - interval '1 day'"),
        ]:
            cur.execute(q)
            print(f"{label:30}: {cur.fetchone()[0]}")


def main():
    conn = connect()

    user_map = load_map("legacy_user_id_map")
    postcard_map = load_map("legacy_postcard_id_map")
    print(f"loaded {len(user_map)} user mappings, {len(postcard_map)} postcard mappings")

    bookmarks = sorted(fetch_all("/api/bookmarks", {"populate": "*"}), key=lambda x: x["id"])
    print(f"fetched {len(bookmarks)} bookmarks")

    migrate_bookmarks(conn, bookmarks, user_map, postcard_map)

    verify(conn)
    conn.close()


if __name__ == "__main__":
    main()
