"""City Guide migration — legacy Strapi `city_guides` -> new
`collection_clusters` under CollectionClusterType 'City Guide'.

Migration step 11 of the run order (needs geo and media in the DB; no per-env
map files consumed).

TRACKER REVISION R1 (2026-08-05) — City Guides re-anchor to REGION.
The previous version of this script matched the legacy `region` name against
the `cities` table, because geo_migration.py used to synthesize one placeholder
city per region. Both the placeholder cities and the City tier are gone, so the
guide's region now resolves directly against `regions`.

TRACKER REVISION R6 (2026-08-12) — cluster membership is DERIVED, not stored.
There is no `collection_cluster_entries` table any more. A cluster type declares
which collection types are eligible (`collection_type_ids`) and which column
binds content to a cluster instance (`match_field`, 'region_id' for City Guide);
rendering a guide page is a query, not a stored join. This script therefore only
migrates the guides themselves — the previous geo-derivation step is gone, along
with its stale-entry pruning problem (derived rows were inserted but never
deleted, so a narrowed scope left orphans behind for ever).

Field mapping (verified against the live API — 9 guides in prod)
  region        -> region_id      (matched by name, scoped by the legacy country)
  country       -> country_id     (kept denormalized, as v1 does)
  description   -> intro
  image         -> cover_media_id
  communityLink -> community_link
  slug          -> slug
  status        -> status         ('published' -> live, else draft)
  (none)        -> name           legacy has NO name field; derived from the
                                  matched region, else a title-cased slug

Dropped: follow_city_guides (migrated by scripts/follows.py into
circles(owned_type='collection_cluster')), timestamps.

Writes `legacy_cityguide_id_map{_dev,_prod}.json` for scripts/follows.py.

Idempotent — clusters upsert on slug. Safe to re-run.

Usage:
    python scripts/cityguide.py
"""

from collections import Counter

from _common import (MediaResolver, SlugAllocator, attrs, connect, fetch_all,
                     rel, save_map, slugify)


def load_lookups(conn):
    """City Guide cluster-type id (seeded), regions keyed by (name, country) and
    by name alone, countries by name."""
    with conn.cursor() as cur:
        cur.execute("SELECT id, match_field, collection_type_ids "
                    "FROM collection_cluster_types WHERE slug = 'city-guide'")
        row = cur.fetchone()
        if not row:
            raise SystemExit("collection_cluster_types has no 'city-guide' row — "
                             "run scripts/seed.py first")
        city_guide_type_id, match_field, scope_ids = row

        cur.execute("SELECT LOWER(name), country_id, id, name FROM regions")
        regions = cur.fetchall()
        cur.execute("SELECT LOWER(name), id FROM countries")
        country_by_name = dict(cur.fetchall())

    region_by_name_country = {(n, c): (i, disp) for n, c, i, disp in regions}
    region_by_name = {}
    for n, c, i, disp in regions:
        region_by_name.setdefault(n, []).append((i, c, disp))

    print(f"city-guide cluster_type id: {city_guide_type_id} "
          f"(match_field={match_field}, scopes {len(scope_ids or [])} collection types)")
    if not scope_ids:
        print("  WARNING: collection_type_ids is empty — a City Guide page would "
              "resolve to nothing. Re-run scripts/seed.py.")
    print(f"lookups: {len(region_by_name)} region names, {len(country_by_name)} countries")
    return city_guide_type_id, region_by_name_country, region_by_name, country_by_name


def migrate_city_guides(conn, city_guides):
    """city-guide -> collection_clusters. Returns {legacy id: new cluster id}."""
    (city_guide_type_id, region_by_name_country,
     region_by_name, country_by_name) = load_lookups(conn)
    media = MediaResolver(conn)
    slugs = SlugAllocator(fallback="city-guide")

    cityguide_map = {}
    no_region, region_missing, region_ambiguous, missing_country = [], [], [], []
    status_counts = Counter()

    with conn.cursor() as cur:
        for cg in city_guides:
            a = attrs(cg)

            # country first — it disambiguates the region match below
            country = rel(a.get("country"))
            country_id = country_by_name.get((country.get("name") or "").strip().lower()) if country else None
            if country and not country_id:
                missing_country.append((cg["id"], country.get("name")))

            # R1: legacy region -> regions (was: -> the placeholder cities tier).
            # Region names are unique per COUNTRY, so use the legacy country
            # when we have it and only fall back to a name-only match.
            region = rel(a.get("region"))
            region_id = region_name = None
            if not region:
                no_region.append((cg["id"], a.get("slug")))
            else:
                key = (region.get("name") or "").strip().lower()
                if country_id and (key, country_id) in region_by_name_country:
                    region_id, region_name = region_by_name_country[(key, country_id)]
                else:
                    matches = region_by_name.get(key, [])
                    if len(matches) == 1:
                        region_id, region_country, region_name = matches[0]
                        country_id = country_id or region_country
                    elif not matches:
                        region_missing.append((cg["id"], region.get("name")))
                    else:
                        region_ambiguous.append((cg["id"], region.get("name"), len(matches)))

            # legacy has NO name field -> derive from the matched region, else the slug
            name = region_name or (a.get("slug") or f"city-guide-{cg['id']}").replace("-", " ").title()

            slug = slugs.take((a.get("slug") or "").strip() or slugify(name))
            cover_id = media.resolve(cur, rel(a.get("image")))

            legacy_status = a.get("status")
            status = "live" if legacy_status == "published" else "draft"
            status_counts[f"{legacy_status} -> {status}"] += 1

            cur.execute(
                """
                INSERT INTO collection_clusters
                    (cluster_type_id, name, slug, intro, story, country_id, region_id,
                     managed_by_company_id, cover_media_id, community_link, status)
                VALUES (%s, %s, %s, %s, NULL, %s, %s, NULL, %s, %s, %s)
                ON CONFLICT (slug) DO UPDATE
                SET cluster_type_id = EXCLUDED.cluster_type_id,
                    name = EXCLUDED.name,
                    intro = EXCLUDED.intro,
                    country_id = EXCLUDED.country_id,
                    region_id = EXCLUDED.region_id,
                    cover_media_id = EXCLUDED.cover_media_id,
                    community_link = EXCLUDED.community_link,
                    status = EXCLUDED.status
                RETURNING id
                """,
                (city_guide_type_id, name, slug,
                 (a.get("description") or "").strip() or None,
                 country_id, region_id, cover_id,
                 (a.get("communityLink") or "").strip() or None,
                 status),
            )
            cityguide_map[cg["id"]] = cur.fetchone()[0]

    conn.commit()
    print(f"collection_clusters upserted: {len(cityguide_map)}")
    print(f"status (legacy -> v2): {dict(status_counts)}")
    print(f"media rows created by this step: {media.created}")
    print(f"MANUAL REVIEW no region ({len(no_region)}): {no_region}")
    print(f"MANUAL REVIEW region name matched no v2 region ({len(region_missing)}): {region_missing}")
    print(f"MANUAL REVIEW region name in >1 country ({len(region_ambiguous)}): {region_ambiguous}")
    print(f"MANUAL REVIEW country not found ({len(missing_country)}): {missing_country}")
    return cityguide_map


def preview_derived_membership(conn):
    """R6: show what each cluster would resolve to, without storing anything.

    This is the exact query the service layer runs to render a cluster page —
    reproduced here as a migration sanity check, NOT as a write.
    """
    with conn.cursor() as cur:
        cur.execute("""
            SELECT cct.slug, cct.match_field,
                   COALESCE(array_length(cct.collection_type_ids, 1), 0),
                   string_agg(ct.name, ', ' ORDER BY s.ord)
            FROM collection_cluster_types cct
            LEFT JOIN unnest(cct.collection_type_ids) WITH ORDINALITY AS s(ct_id, ord) ON TRUE
            LEFT JOIN collection_types ct ON ct.id = s.ct_id
            GROUP BY cct.id, cct.slug, cct.match_field, cct.collection_type_ids
            ORDER BY cct.priority, cct.slug
        """)
        print("\ncluster types (derivation config):")
        for slug, match_field, n, names in cur.fetchall():
            print(f"  {slug:16} match on {match_field:12} over {n} type(s): {names or 'NOTHING'}")

        # City Guide: match_field = region_id. Restaurants/Events/Shopping live
        # in `postcards` (no Collection layer); Properties would live in
        # `collections`. Both are counted so the config is verifiable.
        cur.execute("""
            SELECT cc.name, cc.status,
                   (SELECT COUNT(*) FROM collections c
                     WHERE c.collection_type_id = ANY(cct.collection_type_ids)
                       AND c.region_id = cc.region_id AND c.status = 'live'),
                   (SELECT COUNT(*) FROM postcards p
                     WHERE p.collection_type_id = ANY(cct.collection_type_ids)
                       AND p.region_id = cc.region_id AND p.status = 'live'
                       AND p.collection_id IS NULL)
            FROM collection_clusters cc
            JOIN collection_cluster_types cct ON cct.id = cc.cluster_type_id
            WHERE cct.slug = 'city-guide'
            ORDER BY 4 DESC, cc.name
        """)
        print("\ncity guides — DERIVED membership (collections / postcards), nothing stored:")
        for name, status, n_coll, n_pc in cur.fetchall():
            print(f"  {name:30} [{status:5}]: {n_coll} / {n_pc}")


def verify(conn):
    with conn.cursor() as cur:
        for label, q in [
            ("clusters total",      "SELECT COUNT(*) FROM collection_clusters"),
            ("city guides",         "SELECT COUNT(*) FROM collection_clusters cc JOIN collection_cluster_types t ON t.id = cc.cluster_type_id WHERE t.slug = 'city-guide'"),
            ("with region",         "SELECT COUNT(*) FROM collection_clusters WHERE region_id IS NOT NULL"),
            ("with country",        "SELECT COUNT(*) FROM collection_clusters WHERE country_id IS NOT NULL"),
            ("with cover media",    "SELECT COUNT(*) FROM collection_clusters WHERE cover_media_id IS NOT NULL"),
            ("with community link", "SELECT COUNT(*) FROM collection_clusters WHERE community_link IS NOT NULL"),
            ("status = live",       "SELECT COUNT(*) FROM collection_clusters WHERE status = 'live'"),
            ("dup slugs (want 0)",  "SELECT COUNT(*) FROM (SELECT slug FROM collection_clusters GROUP BY slug HAVING COUNT(*) > 1) d"),
            ("no region (review)",  "SELECT COUNT(*) FROM collection_clusters WHERE region_id IS NULL"),
        ]:
            cur.execute(q)
            print(f"{label:22}: {cur.fetchone()[0]}")


def main():
    conn = connect()

    city_guides = sorted(fetch_all("/api/city-guides", {"populate": "*"}), key=lambda x: x["id"])
    print(f"fetched {len(city_guides)} city-guides")

    cityguide_map = migrate_city_guides(conn, city_guides)
    save_map("legacy_cityguide_id_map", cityguide_map, "city-guide -> cluster")

    verify(conn)
    preview_derived_membership(conn)
    conn.close()


if __name__ == "__main__":
    main()
