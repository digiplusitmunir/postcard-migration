import os, re
from pathlib import Path

import requests
import psycopg
from dotenv import load_dotenv

ROOT = Path.cwd().parent if Path.cwd().name == "notebooks" else Path.cwd()
load_dotenv(ROOT / ".env")

CMS_BASE_URL = os.environ["CMS_BASE_URL"].rstrip("/")
HEADERS = {"Authorization": f"Bearer {os.environ['CMS_API_TOKEN']}"}
DATABASE_URL = os.environ["DATABASE_URL"]


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
    """Fetch every page of a Strapi collection endpoint."""
    items, page = [], 1
    while True:
        p = {"pagination[page]": page, "pagination[pageSize]": 100, **(params or {})}
        r = requests.get(f"{CMS_BASE_URL}{path}", headers=HEADERS, params=p, timeout=60)
        r.raise_for_status()
        body = r.json()
        items.extend(body["data"])
        pg = body.get("meta", {}).get("pagination", {})
        if page >= pg.get("pageCount", 1):
            return items
        page += 1


conn = psycopg.connect(DATABASE_URL)
print("connected to:", DATABASE_URL.rsplit("/", 1)[-1])

conn.rollback()  # clear any aborted transaction from a previous failed run

countries = fetch_all("/api/countries")
print(f"fetched {len(countries)} countries")

skipped = []
used_slugs = set()


def unique_slug(base):
    """Ensure slug uniqueness within this run (two names can slugify the same)."""
    base = base or "item"
    slug, n = base, 2
    while slug in used_slugs:
        slug = f"{base}-{n}"
        n += 1
    used_slugs.add(slug)
    return slug


with conn.cursor() as cur:
    for c in countries:
        a = attrs(c)
        name = (a.get("name") or "").strip()
        if not name:
            skipped.append(c["id"])
            continue
        slug = unique_slug(a.get("slug") or slugify(name))
        cur.execute(
            """
            INSERT INTO countries (name, slug) VALUES (%s, %s)
            ON CONFLICT (name) DO UPDATE SET slug = EXCLUDED.slug
            """,
            (name, slug),
        )
conn.commit()
print(f"upserted countries; skipped (no name): {skipped}")

conn.rollback()  # clear any aborted transaction from a previous failed run

regions = fetch_all("/api/regions", {"populate": "country"})
print(f"fetched {len(regions)} regions")

orphan_regions = []
with conn.cursor() as cur:
    for r in regions:
        a = attrs(r)
        name = (a.get("name") or "").strip()
        country = rel(a.get("country"))
        if not name or not country:
            orphan_regions.append((r["id"], name))
            continue
        cur.execute(
            """
            INSERT INTO regions (country_id, name, slug)
            SELECT id, %s, %s FROM countries WHERE name = %s
            ON CONFLICT (name, country_id) DO UPDATE SET slug = EXCLUDED.slug
            """,
            (name, slugify(name), (country.get("name") or "").strip()),
        )
conn.commit()
print(f"upserted regions; MANUAL REVIEW (no country): {orphan_regions}")


with conn.cursor() as cur:
    cur.execute(
        """
        INSERT INTO cities (region_id, name, slug)
        SELECT id, name, slug FROM regions
        ON CONFLICT (name, region_id) DO NOTHING
        """
    )
    print(f"placeholder cities created: {cur.rowcount}")
conn.commit()

conn.rollback()  # clear any aborted transaction from a previous failed run

localities = fetch_all("/api/localities", {"populate": "region"})
print(f"fetched {len(localities)} localities")

orphan_localities = []
with conn.cursor() as cur:
    for l in localities:
        a = attrs(l)
        name = (a.get("name") or "").strip()
        region = rel(a.get("region"))
        if not name or not region:
            orphan_localities.append((l["id"], name))
            continue
        # the region's placeholder city shares the region's name
        cur.execute(
            """
            INSERT INTO localities (city_id, name, slug)
            SELECT c.id, %s, %s
            FROM cities c JOIN regions r ON c.region_id = r.id
            WHERE r.name = %s AND c.name = r.name
            ON CONFLICT (name, city_id) DO UPDATE SET slug = EXCLUDED.slug
            """,
            (name, slugify(name), (region.get("name") or "").strip()),
        )
conn.commit()
print(f"upserted localities; MANUAL REVIEW (no region): {orphan_localities}")

with conn.cursor() as cur:
    for t in ("countries", "regions", "cities", "localities"):
        cur.execute(f"SELECT COUNT(*) FROM {t}")
        print(f"{t:12}: {cur.fetchone()[0]}")
conn.close()



