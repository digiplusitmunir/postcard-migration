"""City Guide migration — legacy Strapi `city_guides` -> new
`collection_clusters` under CollectionClusterType 'City Guide' (tracker row
#17), plus geo-derived `collection_cluster_entries`.

Migration step 10 of the run order (needs geo, media and directory/album
data in the DB; no per-env map files consumed).

Scope decisions (2026-08-10):
- Legacy `region` maps to the new `cities` tier — v2 cities were synthesized
  1:1 from legacy regions in the geo migration, so the guide's region name
  is matched against cities.name. city_id = the match, region_id = that
  city's parent region, country_id = legacy country by name (falls back to
  the region's country). Ambiguous/missing city names -> manual review.
- Legacy has NO name field — `name` is derived from the matched city's name
  (guides without a region fall back to a title-cased slug).
- description -> intro; story stays NULL (no legacy source).
- image -> cover_media_id, communityLink -> community_link (both columns
  added by migration 20260810080000_add_cluster_cover_and_community_link).
- slug: legacy slug else slugify(name), de-duplicated in-run.
- status: 'published' -> live, else draft.
- Entries: legacy city-guides carry NO explicit content links (the legacy
  frontend listed content by region). When DERIVE_ENTRIES is True (default),
  every live collection in the guide's region becomes an entry
  (entry_type='collection', priority 0 — re-order in the CMS later).
  ON CONFLICT DO NOTHING: hand-curated additions survive re-runs, rows are
  only ever added, never removed. Set DERIVE_ENTRIES = False to curate
  entries by hand instead.
- Dropped: follow_city_guides (deferred -> tracker #24, blocked on the
  Circle 'follow' relationship value), timestamps.
- Writes `legacy_cityguide_id_map_dev/_prod.json` (legacy city-guide id ->
  new cluster id) for the follow-city-guide migration (#24).

Idempotent — clusters upsert on slug, entries insert ON CONFLICT DO NOTHING.
Safe to re-run.

Usage:
    python scripts/cityguide.py
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

# derive collection_cluster_entries from geo (live collections in the guide's
# region); set to False to keep clusters empty for hand-curation instead
DERIVE_ENTRIES = True


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


def load_lookups(conn):
    """City Guide cluster-type id (seeded), cities by lowercase name (legacy
    region -> v2 city), regions for the country fallback, countries by name,
    media by normalized url (same as scripts/media.py)."""
    with conn.cursor() as cur:
        cur.execute("SELECT id FROM collection_cluster_types WHERE slug = 'city-guide'")
        row = cur.fetchone()
        assert row, "collection_cluster_types has no 'city-guide' row — run scripts/seed.py first"
        city_guide_type_id = row[0]

        cur.execute("SELECT LOWER(name), id, region_id, name FROM cities")
        cities_by_name = {}
        for lname, cid, rid, name in cur.fetchall():
            cities_by_name.setdefault(lname, []).append((cid, rid, name))

        cur.execute("SELECT id, country_id FROM regions")
        country_by_region = dict(cur.fetchall())

        cur.execute("SELECT LOWER(name), id FROM countries")
        country_by_name = dict(cur.fetchall())

        cur.execute("SELECT url, id FROM media")
        media_by_url = dict(cur.fetchall())

    print(f"city-guide cluster_type id: {city_guide_type_id}")
    print(f"lookups: {len(cities_by_name)} city names, {len(country_by_region)} regions, "
          f"{len(country_by_name)} countries, {len(media_by_url)} media")
    return city_guide_type_id, cities_by_name, country_by_region, country_by_name, media_by_url


def migrate_city_guides(conn, city_guides):
    """city-guide -> collection_clusters. Returns
    ({legacy city-guide id: new cluster id}, {legacy city-guide id: region_id})."""
    (city_guide_type_id, cities_by_name, country_by_region,
     country_by_name, media_by_url) = load_lookups(conn)

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

    used_slugs = set()

    def unique_slug(base):
        base = base or "city-guide"
        slug, n = base, 2
        while slug in used_slugs:
            slug = f"{base}-{n}"
            n += 1
        used_slugs.add(slug)
        return slug

    cityguide_map = {}   # legacy city-guide id -> new cluster id
    region_of = {}       # legacy city-guide id -> region_id (for the derived-entries step)

    no_region, city_missing, city_ambiguous, missing_country = [], [], [], []
    status_counts = {}

    with conn.cursor() as cur:
        for cg in city_guides:
            a = attrs(cg)

            # legacy region -> v2 city (cities were synthesized 1:1 from regions)
            region = rel(a.get("region"))
            city_id = region_id = None
            city_name = None
            if not region:
                no_region.append((cg["id"], a.get("slug")))
            else:
                matches = cities_by_name.get((region.get("name") or "").strip().lower(), [])
                if len(matches) == 1:
                    city_id, region_id, city_name = matches[0]
                elif not matches:
                    city_missing.append((cg["id"], region.get("name")))
                else:
                    city_ambiguous.append((cg["id"], region.get("name"), len(matches)))

            # country: legacy relation by name, else the matched region's country
            country = rel(a.get("country"))
            country_id = country_by_name.get((country.get("name") or "").strip().lower()) if country else None
            if country and not country_id:
                missing_country.append((cg["id"], country.get("name")))
            country_id = country_id or (country_by_region.get(region_id) if region_id else None)

            # legacy has NO name field -> derive from the matched city, else the slug
            name = city_name or (a.get("slug") or f"city-guide-{cg['id']}").replace("-", " ").title()

            slug = unique_slug((a.get("slug") or "").strip() or slugify(name))
            cover_id = media_id_for(rel(a.get("image")), cur)

            legacy_status = a.get("status")
            status_counts[legacy_status] = status_counts.get(legacy_status, 0) + 1
            status = "live" if legacy_status == "published" else "draft"

            cur.execute(
                """
                INSERT INTO collection_clusters
                    (cluster_type_id, name, slug, intro, story, country_id, region_id,
                     city_id, locality_id, managed_by_company_id, cover_media_id,
                     community_link, status)
                VALUES (%s, %s, %s, %s, NULL, %s, %s, %s, NULL, NULL, %s, %s, %s)
                ON CONFLICT (slug) DO UPDATE
                SET cluster_type_id = EXCLUDED.cluster_type_id,
                    name = EXCLUDED.name,
                    intro = EXCLUDED.intro,
                    country_id = EXCLUDED.country_id,
                    region_id = EXCLUDED.region_id,
                    city_id = EXCLUDED.city_id,
                    cover_media_id = EXCLUDED.cover_media_id,
                    community_link = EXCLUDED.community_link,
                    status = EXCLUDED.status
                RETURNING id
                """,
                (city_guide_type_id, name, slug,
                 (a.get("description") or "").strip() or None,
                 country_id, region_id, city_id,
                 cover_id,
                 (a.get("communityLink") or "").strip() or None,
                 status),
            )
            cityguide_map[cg["id"]] = cur.fetchone()[0]
            if region_id:
                region_of[cg["id"]] = region_id

    conn.commit()
    print(f"collection_clusters upserted: {len(cityguide_map)}")
    print(f"legacy status counts (published -> live): {status_counts}")
    print(f"MANUAL REVIEW no region ({len(no_region)}): {no_region}")
    print(f"MANUAL REVIEW region name matched no v2 city ({len(city_missing)}): {city_missing}")
    print(f"MANUAL REVIEW region name matched multiple v2 cities ({len(city_ambiguous)}): {city_ambiguous}")
    print(f"MANUAL REVIEW country not found ({len(missing_country)}): {missing_country}")
    return cityguide_map, region_of


def derive_entries(conn, cityguide_map, region_of):
    """Geo-derived entries: every live collection in the guide's region ->
    one collection_cluster_entries row (entry_type='collection', priority 0)."""
    entries = 0
    with conn.cursor() as cur:
        for cg_id, cluster_id in cityguide_map.items():
            region_id = region_of.get(cg_id)
            if not region_id:
                continue
            cur.execute(
                """
                INSERT INTO collection_cluster_entries (cluster_id, entry_type, entry_id, priority)
                SELECT %s, 'collection', c.id, 0
                FROM collections c
                WHERE c.region_id = %s AND c.status = 'live'
                ON CONFLICT (cluster_id, entry_type, entry_id) DO NOTHING
                """,
                (cluster_id, region_id),
            )
            entries += cur.rowcount

    conn.commit()
    print(f"collection_cluster_entries inserted this run: {entries}")


def verify(conn):
    with conn.cursor() as cur:
        for label, q in [
            ("clusters total",      "SELECT COUNT(*) FROM collection_clusters"),
            ("city guides",         "SELECT COUNT(*) FROM collection_clusters cc JOIN collection_cluster_types t ON t.id = cc.cluster_type_id WHERE t.slug = 'city-guide'"),
            ("with city",           "SELECT COUNT(*) FROM collection_clusters WHERE city_id IS NOT NULL"),
            ("with region",         "SELECT COUNT(*) FROM collection_clusters WHERE region_id IS NOT NULL"),
            ("with country",        "SELECT COUNT(*) FROM collection_clusters WHERE country_id IS NOT NULL"),
            ("with cover media",    "SELECT COUNT(*) FROM collection_clusters WHERE cover_media_id IS NOT NULL"),
            ("with community link", "SELECT COUNT(*) FROM collection_clusters WHERE community_link IS NOT NULL"),
            ("status = live",       "SELECT COUNT(*) FROM collection_clusters WHERE status = 'live'"),
            ("entries total",       "SELECT COUNT(*) FROM collection_cluster_entries"),
            ("clusters w/ entries", "SELECT COUNT(DISTINCT cluster_id) FROM collection_cluster_entries"),
            ("dup slugs (want 0)",  "SELECT COUNT(*) FROM (SELECT slug FROM collection_clusters GROUP BY slug HAVING COUNT(*) > 1) d"),
        ]:
            cur.execute(q)
            print(f"{label:22}: {cur.fetchone()[0]}")

        cur.execute("""
            SELECT cc.name, cc.status, COUNT(e.id) AS entries
            FROM collection_clusters cc
            JOIN collection_cluster_types t ON t.id = cc.cluster_type_id AND t.slug = 'city-guide'
            LEFT JOIN collection_cluster_entries e ON e.cluster_id = cc.id
            GROUP BY cc.id, cc.name, cc.status ORDER BY entries DESC, cc.name
        """)
        print("\ncity guides (derived entries, if enabled):")
        for name, status, n in cur.fetchall():
            print(f"  {name:30} [{status:5}]: {n}")


def main():
    conn = psycopg.connect(DATABASE_URL)
    print("connected to:", DATABASE_URL.rsplit("/", 1)[-1])

    city_guides = sorted(fetch_all("/api/city-guides", {"populate": "*"}), key=lambda x: x["id"])
    print(f"fetched {len(city_guides)} city-guides")

    cityguide_map, region_of = migrate_city_guides(conn, city_guides)

    if DERIVE_ENTRIES:
        derive_entries(conn, cityguide_map, region_of)
    else:
        print("DERIVE_ENTRIES = False — skipping geo-derived entries (hand-curation)")

    out = ROOT / f"legacy_cityguide_id_map{ENV_SUFFIX}.json"
    out.write_text(json.dumps({str(k): str(v) for k, v in cityguide_map.items()}, indent=2))
    print(f"saved {len(cityguide_map)} legacy->new city-guide id mappings to {out}")

    verify(conn)
    conn.close()


if __name__ == "__main__":
    main()
