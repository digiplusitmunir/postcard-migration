"""Category + Environment facet migration — legacy Strapi `categories` and
`environments` -> `facet_types` / `facet_values` / `facet_assignments`.

Migration step 10 of the run order (run AFTER directory_album.py, postcard.py
and journey.py — assignments need collections AND postcards to exist).

Why one script for both
-----------------------
Category and Environment are structurally identical in v1: a name, a `directory`
relation that scopes it to one CollectionType, and `albums` / `dx_cards` back
relations. The tracker says as much ("Same binding rule as Category"). They
differ only in what the resulting FacetType is called, so they share every line
of logic here and differ only in the FACETS table below.

Nomenclature (the tracker left Environment "TBD" — resolved from the live data)
------------------------------------------------------------------------------
Inspecting the actual values makes the split obvious:

  Properties   Category    Eco-Lodge, Glamping, Heritage Hotel, Villas   -> "Type"
               Environment City, Farm, Nature, Jungle, Mountain, Desert  -> "Setting"
  Restaurants  Category    Awadhi cuisine, Seafood, Coffee, Desserts     -> "Cuisine"
               Environment Restaurant, Bar, Bakery, Cafe, Speakeasy      -> "Venue Type"
  Events       Category    Cocktail Tasting, Gin, Chef, Techno           -> "Category"
               Environment Supper Club, Chef Takeover, Wine Tasting      -> "Format"
  Shopping     Category    Sustainable, Handmade, Artisan, Jewellery     -> "Type"
               Environment Fashion, Home Decor, Footwear, Books          -> "Department"

This also settles the tracker's ambiguous "Restaurants -> 'Cuisine/Type'": it is
TWO facets, not one — Cuisine comes from Category, Type from Environment.

Sources per album (all three map into the Category-derived facet)
----------------------------------------------------------------
  album.category   single relation  (281 albums)
  album.cuisines   LIST relation    (525 albums, points at the same
                                     `categories` table — the multi-select
                                     cuisine picker for Food & Beverages)
  dx_card.category single relation  (37 dx-cards — migrated later, see below)

Because `cuisines` is a list, the Restaurants Cuisine facet is allows_multiple;
every other facet here is single-select.

Assignment target follows the album split
-----------------------------------------
  Properties albums          -> owned_type = 'collection' (legacy_album_id_map)
  Restaurants/Events/Shopping-> owned_type = 'postcard'    (legacy_album_postcard_id_map)

A Journey 'Theme' facet is described by the tracker but has NO legacy source
(property_itineraries carry no category/environment relation), so nothing is
seeded or assigned for it. The schema supports it when the CMS starts
collecting one: FacetType.applies_to_subcollection_type_id +
FacetOwnedType.subcollection.

Dx-cards are NOT handled here — they belong to the Destination Expert
migration, which does not exist yet. Their category/environment assignments
should be created there, reusing `legacy_category_id_map` /
`legacy_environment_id_map` written by this script.

Idempotent — facet types/values upsert on their slug keys, assignments
ON CONFLICT DO NOTHING. Safe to re-run.

Usage:
    python scripts/category_environment_facet.py
"""

from collections import Counter

from _common import (attrs, connect, fetch_all, load_map, rel, rel_many,
                     save_map, slugify)

# kind, legacy directory slug, collection_type slug, facet name, facet slug, allows_multiple
#
# allows_multiple is set from what the legacy data actually does, not from the
# field names. `album.cuisines` is a LIST relation to the SAME `categories`
# table as the single `album.category`, and it is NOT restricted to Food &
# Beverages — Shopping albums use it too (shopping-type averages 2.2 values per
# album). So every Category-derived facet is multi-select. Environment is a
# single relation everywhere and averages ~1.0 value per item, so those stay
# single-select.
FACETS = [
    ("category", "mindful-luxury-hotels", "properties",  "Type",       "property-type",         True),
    ("category", "food-and-beverages",    "restaurants", "Cuisine",    "restaurant-cuisine",    True),
    ("category", "postcard-events",       "events",      "Category",   "event-category",        True),
    ("category", "postcard-shopping",     "shopping",    "Type",       "shopping-type",         True),

    ("environment", "mindful-luxury-hotels", "properties",  "Setting",    "property-setting",      False),
    ("environment", "food-and-beverages",    "restaurants", "Venue Type", "restaurant-venue-type", False),
    ("environment", "postcard-events",       "events",      "Format",     "event-format",          False),
    ("environment", "postcard-shopping",     "shopping",    "Department", "shopping-department",   False),
]


def upsert_facet_types(conn):
    """Returns {(kind, legacy directory slug): facet_type_id}."""
    with conn.cursor() as cur:
        cur.execute("SELECT slug, id FROM collection_types")
        ct_by_slug = dict(cur.fetchall())

    missing = {ct for *_, ct, _, _, _ in
               [(k, d, c, n, s, m) for k, d, c, n, s, m in FACETS] if ct not in ct_by_slug}
    if missing:
        raise SystemExit(f"collection_types missing {sorted(missing)} — run scripts/seed.py "
                         f"and scripts/directory_album.py first")

    out = {}
    with conn.cursor() as cur:
        for kind, dir_slug, ct_slug, name, slug, multiple in FACETS:
            cur.execute(
                """
                INSERT INTO facet_types (name, slug, applies_to_collection_type_id,
                                         applies_to_subcollection_type_id, allows_multiple)
                VALUES (%s, %s, %s, NULL, %s)
                ON CONFLICT (slug) DO UPDATE
                SET name = EXCLUDED.name,
                    applies_to_collection_type_id = EXCLUDED.applies_to_collection_type_id,
                    allows_multiple = EXCLUDED.allows_multiple
                RETURNING id
                """,
                (name, slug, ct_by_slug[ct_slug], multiple),
            )
            out[(kind, dir_slug)] = cur.fetchone()[0]
    conn.commit()
    print(f"facet_types upserted: {len(out)}")
    for (kind, dir_slug), ft_id in sorted(out.items()):
        print(f"  {kind:11} {dir_slug:22} -> facet_type {ft_id}")
    return out


def migrate_values(conn, kind, endpoint, facet_type_ids):
    """categories / environments -> facet_values. Returns {legacy id: facet_value id}."""
    rows = sorted(fetch_all(endpoint, {"populate": "directory"}), key=lambda r: r["id"])
    print(f"\nfetched {len(rows)} {kind} rows from {endpoint}")

    value_map = {}                 # legacy id -> facet_value id
    seen = {}                      # (facet_type_id, slug) -> facet_value id
    merged, no_directory, unmapped_directory, no_name = [], [], Counter(), []

    with conn.cursor() as cur:
        for r in rows:
            a = attrs(r)
            name = (a.get("name") or "").strip()
            if not name:
                no_name.append(r["id"])
                continue

            directory = rel(a.get("directory"))
            if not directory:
                no_directory.append((r["id"], name))
                continue
            dir_slug = (directory.get("slug") or "").strip()
            ft_id = facet_type_ids.get((kind, dir_slug))
            if not ft_id:
                # e.g. a Designer Tours category — that directory has no v2
                # collection type, so its values have nowhere to live
                unmapped_directory[dir_slug] += 1
                continue

            # legacy slug is Direct per the tracker, but is null on 456/470
            # categories and absent entirely on environments -> derive
            slug = (a.get("slug") or "").strip() or slugify(name)
            if not slug:
                no_name.append(r["id"])
                continue

            key = (ft_id, slug)
            if key in seen:  # duplicate name within one facet -> merge
                value_map[r["id"]] = seen[key]
                merged.append((r["id"], name))
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
            seen[key] = fv_id
            value_map[r["id"]] = fv_id

    conn.commit()
    print(f"  facet_values upserted: {len(seen)}; legacy {kind} mapped: {len(value_map)}")
    print(f"  merged duplicate names ({len(merged)}): {merged[:15]}")
    print(f"  skipped (no name/slug): {no_name}")
    print(f"  skipped (no directory) ({len(no_directory)}): {no_directory[:10]}")
    print(f"  skipped (directory has no v2 collection type): {dict(unmapped_directory) or 'none'}")
    return value_map


def assign(conn, albums, category_map, environment_map, album_map, album_postcard_map):
    """Album category / cuisines / environment -> facet_assignments.

    owned_type follows the album split: Properties albums became collections,
    Restaurants/Events/Shopping albums became postcards.
    """
    inserted = Counter()
    unmapped_values, unmigrated_albums = [], []

    with conn.cursor() as cur:
        for al in albums:
            a = attrs(al)
            if al["id"] in album_map:
                owned_type, owned_id = "collection", album_map[al["id"]]
            elif al["id"] in album_postcard_map:
                owned_type, owned_id = "postcard", album_postcard_map[al["id"]]
            else:
                unmigrated_albums.append(al["id"])   # Designer Tours / no name
                continue

            # (source label, legacy value dicts, legacy id -> facet_value map)
            sources = [
                ("category",    [rel(a.get("category"))] if a.get("category") else [], category_map),
                ("cuisines",    rel_many(a.get("cuisines")),                            category_map),
                ("environment", [rel(a.get("environment"))] if a.get("environment") else [], environment_map),
            ]

            for label, values, value_map in sources:
                for v in values:
                    if not v:
                        continue
                    fv_id = value_map.get(v["id"])
                    if not fv_id:
                        unmapped_values.append((al["id"], label, v["id"], v.get("name")))
                        continue
                    cur.execute(
                        """
                        INSERT INTO facet_assignments (owned_type, owned_id, facet_value_id)
                        VALUES (%s, %s, %s)
                        ON CONFLICT (owned_type, owned_id, facet_value_id) DO NOTHING
                        """,
                        (owned_type, owned_id, fv_id),
                    )
                    if cur.rowcount:
                        inserted[f"{label} -> {owned_type}"] += 1

    conn.commit()
    print(f"\nfacet_assignments inserted this run: {sum(inserted.values())}")
    for k, n in sorted(inserted.items()):
        print(f"  {k:28}: {n}")
    print(f"albums not in either id map (Designer Tours etc.): {len(unmigrated_albums)}")
    print(f"MANUAL REVIEW legacy values not in map ({len(unmapped_values)}): {unmapped_values[:20]}")


def verify(conn):
    with conn.cursor() as cur:
        print("\nfacet types and their value / assignment counts:")
        cur.execute("""
            SELECT ft.slug, ft.name, ct.name, ft.allows_multiple,
                   COUNT(DISTINCT fv.id),
                   COUNT(fa.id)
            FROM facet_types ft
            LEFT JOIN collection_types ct ON ct.id = ft.applies_to_collection_type_id
            LEFT JOIN facet_values fv ON fv.facet_type_id = ft.id
            LEFT JOIN facet_assignments fa ON fa.facet_value_id = fv.id
            GROUP BY ft.id, ft.slug, ft.name, ct.name, ft.allows_multiple
            ORDER BY ft.slug
        """)
        print(f"  {'slug':24} {'facet':12} {'scope':13} {'multi':6} {'values':>7} {'assign':>7}")
        for slug, name, ct, multi, nv, na in cur.fetchall():
            print(f"  {slug:24} {name:12} {(ct or '-'):13} {str(multi):6} {nv:7} {na:7}")

        for label, q in [
            ("assignments total",        "SELECT COUNT(*) FROM facet_assignments"),
            ("  on collections",         "SELECT COUNT(*) FROM facet_assignments WHERE owned_type = 'collection'"),
            ("  on postcards",           "SELECT COUNT(*) FROM facet_assignments WHERE owned_type = 'postcard'"),
            ("  on subcollections",      "SELECT COUNT(*) FROM facet_assignments WHERE owned_type = 'subcollection'"),
            ("orphan collection refs (want 0)",
             "SELECT COUNT(*) FROM facet_assignments fa WHERE fa.owned_type = 'collection' "
             "AND NOT EXISTS (SELECT 1 FROM collections c WHERE c.id = fa.owned_id)"),
            ("orphan postcard refs (want 0)",
             "SELECT COUNT(*) FROM facet_assignments fa WHERE fa.owned_type = 'postcard' "
             "AND NOT EXISTS (SELECT 1 FROM postcards p WHERE p.id = fa.owned_id)"),
            ("single-select violations (review)",
             """SELECT COUNT(*) FROM (
                  SELECT fa.owned_type, fa.owned_id, fv.facet_type_id
                  FROM facet_assignments fa
                  JOIN facet_values fv ON fv.id = fa.facet_value_id
                  JOIN facet_types ft ON ft.id = fv.facet_type_id AND ft.allows_multiple = false
                  GROUP BY 1, 2, 3 HAVING COUNT(*) > 1) d"""),
        ]:
            cur.execute(q)
            print(f"{label:36}: {cur.fetchone()[0]}")


def main():
    conn = connect()

    album_map = load_map("legacy_album_id_map")
    album_postcard_map = load_map("legacy_album_postcard_id_map", required=False)
    print(f"loaded {len(album_map)} album->collection, {len(album_postcard_map)} album->postcard mappings")

    facet_type_ids = upsert_facet_types(conn)
    category_map = migrate_values(conn, "category", "/api/categories", facet_type_ids)
    environment_map = migrate_values(conn, "environment", "/api/environments", facet_type_ids)

    save_map("legacy_category_id_map", category_map, "category -> facet_value")
    save_map("legacy_environment_id_map", environment_map, "environment -> facet_value")

    albums = sorted(fetch_all("/api/albums", {"populate": "category,cuisines,environment"}),
                    key=lambda x: x["id"])
    print(f"\nfetched {len(albums)} albums for assignment")
    assign(conn, albums, category_map, environment_map, album_map, album_postcard_map)

    verify(conn)
    conn.close()


if __name__ == "__main__":
    main()
