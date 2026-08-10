"""Directory/Album migration — legacy Strapi `directories` -> `collection_types`
and `albums` -> `collections` (tracker rows #6 and #14, Collection half only).

Migration step 6 of the run order (run AFTER geo, media, company and users).

Scope decisions (2026-08-06):
- **Designer Tours** directory + its 59 albums are **skipped** — they become
  dx-card / Destination Expert data later (tracker rows #11/#13).
- **Journey subcollections are NOT created here** (deferred). The dual-price
  fix (`subcollections.price_starting_at`, migration
  `20260806060000_add_subcollection_price_starting_at`) is already in the
  schema for when that step runs.
- author / assigned_staff circles are NOT created here — that optional step
  lives only in `notebooks/directory_album_migration.ipynb` (section 6).

Directories are reconciled to the fixed v2 collection-type set (names/slugs
kept, legacy description + logo url carried over). Albums map to collections
with geo/company/media lookups by the same natural keys the earlier
migrations used. Albums with an empty slug get one generated from the name,
de-duplicated in-run (id-sorted so `foo-2` suffixes stay stable across
re-runs). Writes `legacy_album_id_map_dev.json` / `_prod.json` (legacy album
id -> new collection id, suffix from the DB name in DATABASE_URL) for the
postcards migration.

Idempotent — upsert on slug. Safe to re-run.

Usage:
    python scripts/directory_album.py
"""

import json
import os
import re
from pathlib import Path

import requests
import psycopg
from psycopg.types.json import Json
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

CMS_BASE_URL = os.environ["CMS_BASE_URL"].rstrip("/")
HEADERS = {"Authorization": f"Bearer {os.environ['CMS_API_TOKEN']}"}
DATABASE_URL = os.environ["DATABASE_URL"]

# map files are suffixed per environment, keyed off the DB name in DATABASE_URL
ENV_SUFFIX = {"development": "_dev", "production": "_prod"}.get(DATABASE_URL.rsplit("/", 1)[-1], "")

# legacy directory slug -> (name, slug, has_dedicated_collection, priority)
DIRECTORY_TO_CT = {
    "mindful-luxury-hotels": ("Properties",  "properties",  True,  1),  # Postcard StarPartner Stays
    "food-and-beverages":    ("Restaurants", "restaurants", False, 2),  # Food and Beverages
    "postcard-events":       ("Events",      "events",      False, 3),  # Postcard Events
    "postcard-shopping":     ("Shopping",    "shopping",    False, 4),  # Postcard Shopping
}
SKIP_DIRECTORY_SLUGS = {"mindful-luxury-tours"}  # Designer Tours -> dx-card migration later

VALID_STATUS = {"draft", "assigned", "submit", "rework", "live"}


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


def migrate_directories(conn):
    """Directory -> collection_types. Returns (DIR_ID_TO_CT, DEFAULT_CT_ID, SKIPPED_DIR_IDS)."""
    directories = fetch_all("/api/directories", {"populate": "logo"})
    print(f"fetched {len(directories)} directories")

    dir_id_to_ct_slug, skipped_dir_ids, unmapped_dirs = {}, set(), []
    with conn.cursor() as cur:
        for d in directories:
            a = attrs(d)
            if a.get("slug") in SKIP_DIRECTORY_SLUGS:
                skipped_dir_ids.add(d["id"])
                continue
            target = DIRECTORY_TO_CT.get(a.get("slug"))
            if not target:
                unmapped_dirs.append((d["id"], a.get("name"), a.get("slug")))
                continue
            name, slug, dedicated, priority = target

            logo, icon = rel(a.get("logo")), None
            if logo and logo.get("url"):
                icon = logo["url"].strip()
                if icon.startswith("/"):
                    icon = CMS_BASE_URL + icon

            cur.execute(
                """
                INSERT INTO collection_types
                    (name, slug, description, icon, has_dedicated_collection, priority)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (slug) DO UPDATE
                SET name = EXCLUDED.name,
                    description = EXCLUDED.description,
                    icon = EXCLUDED.icon,
                    has_dedicated_collection = EXCLUDED.has_dedicated_collection,
                    priority = EXCLUDED.priority
                """,
                (name, slug, (a.get("description") or "").strip() or None, icon, dedicated, priority),
            )
            dir_id_to_ct_slug[d["id"]] = slug
    conn.commit()

    with conn.cursor() as cur:
        cur.execute("SELECT slug, id FROM collection_types")
        ct_id_by_slug = dict(cur.fetchall())

    dir_id_to_ct = {did: ct_id_by_slug[s] for did, s in dir_id_to_ct_slug.items()}
    default_ct_id = ct_id_by_slug["properties"]  # fallback for albums with no directory

    print("collection_types         :", ct_id_by_slug)
    print("directory -> ct id       :", dir_id_to_ct)
    print("skipped directory ids    :", skipped_dir_ids)   # Designer Tours
    print("MANUAL REVIEW (unmapped) :", unmapped_dirs)     # should be empty
    return dir_id_to_ct, default_ct_id, skipped_dir_ids


def load_lookups(conn):
    """DB lookup maps built the same way earlier migrations keyed their rows."""
    with conn.cursor() as cur:
        cur.execute("SELECT LOWER(name), id FROM countries")
        country_by_name = dict(cur.fetchall())
        cur.execute("SELECT LOWER(name), country_id, id FROM regions")
        region_by_name_country = {(n, c): i for n, c, i in cur.fetchall()}
        cur.execute("SELECT LOWER(name), id FROM localities")
        locality_by_name = {}
        for n, i in cur.fetchall():
            locality_by_name.setdefault(n, []).append(i)
        cur.execute("SELECT LOWER(name), id FROM companies")
        company_by_name = dict(cur.fetchall())
        cur.execute("SELECT slug, id FROM companies")
        company_by_slug = dict(cur.fetchall())
        cur.execute("SELECT url, id FROM media")
        media_by_url = dict(cur.fetchall())

    print(f"lookups: {len(country_by_name)} countries, {len(region_by_name_country)} regions, "
          f"{len(locality_by_name)} locality names, {len(company_by_name)} companies, "
          f"{len(media_by_url)} media")
    return country_by_name, region_by_name_country, locality_by_name, \
        company_by_name, company_by_slug, media_by_url


def migrate_albums(conn, albums, dir_id_to_ct, default_ct_id, skipped_dir_ids):
    """Album -> collections. Returns {legacy album id: new collection id}."""
    (country_by_name, region_by_name_country, locality_by_name,
     company_by_name, company_by_slug, media_by_url) = load_lookups(conn)

    def media_id_for(image, cur):
        """Find-or-create a media row for a populated Strapi file (keyed by
        normalized url, same as scripts/media.py — rows are reused, never duplicated)."""
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
        base = base or "album"
        slug, n = base, 2
        while slug in used_slugs:
            slug = f"{base}-{n}"
            n += 1
        used_slugs.add(slug)
        return slug

    album_to_collection = {}       # legacy album id -> new collection id

    skipped_no_name, skipped_designer_tours, no_directory = [], [], []
    missing_country, missing_region, ambiguous_locality, unmatched_company = [], [], [], []

    with conn.cursor() as cur:
        for al in albums:
            a = attrs(al)
            name = (a.get("name") or "").strip()
            if not name:
                skipped_no_name.append(al["id"])
                continue

            # directory -> collection_type; Designer Tours albums are NOT migrated
            dirs = rel_many(a.get("directories"))
            if dirs and dirs[0]["id"] in skipped_dir_ids:
                skipped_designer_tours.append((al["id"], name))
                continue
            ct_id = dir_id_to_ct.get(dirs[0]["id"], default_ct_id) if dirs else default_ct_id
            if not dirs:
                no_directory.append((al["id"], name))

            slug = unique_slug((a.get("slug") or "").strip() or slugify(name))

            # geo: country by name, region by (name, country), locality by unique name
            country = rel(a.get("country"))
            country_id = country_by_name.get((country.get("name") or "").strip().lower()) if country else None
            if country and not country_id:
                missing_country.append((al["id"], country.get("name")))

            region, region_id = rel(a.get("region")), None
            if region and country_id:
                region_id = region_by_name_country.get(((region.get("name") or "").strip().lower(), country_id))
            if region and not region_id:
                missing_region.append((al["id"], region.get("name")))

            locality, locality_id = rel(a.get("locality")), None
            if locality:
                ids = locality_by_name.get((locality.get("name") or "").strip().lower(), [])
                if len(ids) == 1:
                    locality_id = ids[0]
                else:
                    ambiguous_locality.append((al["id"], locality.get("name"), len(ids)))

            # company relation by name, else legacy companySlug string by slug
            company, company_id = rel(a.get("company")), None
            if company:
                company_id = company_by_name.get((company.get("name") or "").strip().lower())
                if not company_id:
                    unmatched_company.append((al["id"], company.get("name")))
            elif (a.get("companySlug") or "").strip():
                cs = a["companySlug"].strip()
                company_id = company_by_slug.get(cs) or company_by_slug.get(slugify(cs))
                if not company_id:
                    unmatched_company.append((al["id"], cs))

            cover_id = media_id_for(rel(a.get("coverImage")), cur)

            location = {k: v for k, v in {
                "lat": a.get("lat"), "lng": a.get("long"),
                "google_place_id": a.get("placeId"), "location_link": a.get("locationLink"),
            }.items() if v not in (None, "")} or None

            seo = {k: v for k, v in (a.get("seo") or {}).items()
                   if k != "id" and v not in (None, "")} or None

            status = a.get("status") if a.get("status") in VALID_STATUS \
                else ("live" if a.get("isActive") else "draft")

            cur.execute(
                """
                INSERT INTO collections
                    (collection_type_id, name, intro, story, slug, cover_media_id, seo,
                     is_featured, priority, country_id, region_id, locality_id, location,
                     managed_by_company_id, website, media_kit, additional_info,
                     sustainability, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (slug) DO UPDATE
                SET collection_type_id = EXCLUDED.collection_type_id,
                    name = EXCLUDED.name,
                    intro = EXCLUDED.intro,
                    story = EXCLUDED.story,
                    cover_media_id = EXCLUDED.cover_media_id,
                    seo = EXCLUDED.seo,
                    is_featured = EXCLUDED.is_featured,
                    priority = EXCLUDED.priority,
                    country_id = EXCLUDED.country_id,
                    region_id = EXCLUDED.region_id,
                    locality_id = EXCLUDED.locality_id,
                    location = EXCLUDED.location,
                    managed_by_company_id = EXCLUDED.managed_by_company_id,
                    website = EXCLUDED.website,
                    media_kit = EXCLUDED.media_kit,
                    additional_info = EXCLUDED.additional_info,
                    sustainability = EXCLUDED.sustainability,
                    status = EXCLUDED.status
                RETURNING id
                """,
                (ct_id, name,
                 (a.get("intro") or "").strip() or None,
                 (a.get("story") or "").strip() or None,
                 slug, cover_id, Json(seo) if seo else None,
                 bool(a.get("isFeatured")), a.get("priority") or 0,
                 country_id, region_id, locality_id,
                 Json(location) if location else None,
                 company_id,
                 (a.get("website") or "").strip() or None,
                 (a.get("media_kit") or "").strip() or None,
                 (a.get("additionalInfo") or "").strip() or None,
                 (a.get("sustainability") or "").strip() or None,
                 status),
            )
            album_to_collection[al["id"]] = cur.fetchone()[0]

    conn.commit()
    print(f"collections upserted: {len(album_to_collection)}")
    print(f"skipped Designer Tours albums ({len(skipped_designer_tours)})")  # expect 59
    print(f"skipped (no name): {skipped_no_name}")
    print(f"no directory -> defaulted to Properties ({len(no_directory)}): {no_directory}")
    print(f"MANUAL REVIEW country not found ({len(missing_country)}): {missing_country[:20]}")
    print(f"MANUAL REVIEW region not found ({len(missing_region)}): {missing_region[:20]}")
    print(f"MANUAL REVIEW locality missing/ambiguous ({len(ambiguous_locality)}): {ambiguous_locality[:20]}")
    print(f"MANUAL REVIEW company unmatched ({len(unmatched_company)}): {unmatched_company[:20]}")
    return album_to_collection


def verify(conn):
    with conn.cursor() as cur:
        cur.execute("""
            SELECT ct.name, COUNT(c.id) FROM collection_types ct
            LEFT JOIN collections c ON c.collection_type_id = ct.id
            GROUP BY ct.id, ct.name ORDER BY MIN(ct.priority)
        """)
        for name, n in cur.fetchall():
            print(f"{name:22}: {n}")
        for label, q in [
            ("collections total",  "SELECT COUNT(*) FROM collections"),
            ("with cover media",   "SELECT COUNT(*) FROM collections WHERE cover_media_id IS NOT NULL"),
            ("with country",       "SELECT COUNT(*) FROM collections WHERE country_id IS NOT NULL"),
            ("with region",        "SELECT COUNT(*) FROM collections WHERE region_id IS NOT NULL"),
            ("with company",       "SELECT COUNT(*) FROM collections WHERE managed_by_company_id IS NOT NULL"),
            ("status = live",      "SELECT COUNT(*) FROM collections WHERE status = 'live'"),
            ("dup slugs (want 0)", "SELECT COUNT(*) FROM (SELECT slug FROM collections GROUP BY slug HAVING COUNT(*) > 1) d"),
        ]:
            cur.execute(q)
            print(f"{label:19}: {cur.fetchone()[0]}")


def main():
    conn = psycopg.connect(DATABASE_URL)
    print("connected to:", DATABASE_URL.rsplit("/", 1)[-1])

    dir_id_to_ct, default_ct_id, skipped_dir_ids = migrate_directories(conn)

    albums = sorted(fetch_all("/api/albums", {"populate": "*"}), key=lambda x: x["id"])
    print(f"fetched {len(albums)} albums")

    album_to_collection = migrate_albums(conn, albums, dir_id_to_ct, default_ct_id, skipped_dir_ids)

    out = ROOT / f"legacy_album_id_map{ENV_SUFFIX}.json"
    out.write_text(json.dumps({str(k): str(v) for k, v in album_to_collection.items()}, indent=2))
    print(f"saved {len(album_to_collection)} legacy->new album id mappings to {out}")

    verify(conn)
    conn.close()


if __name__ == "__main__":
    main()
