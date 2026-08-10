"""Company migration — legacy Strapi `companies` -> new `companies` table.

Migration 2b of the run order (run AFTER media.py so icons reuse its rows).

Legacy Company has name, website and an icon media. The icon is kept: its
file becomes/reuses a `media` row and is linked via companies.icon_media_id
(schema migration add-company-icon).

The new schema needs a unique slug (generated here, de-duplicated within the
run) and a status — set to 'active' since these are existing live companies
(the schema default 'pending' is for new self-signups). contact_email /
contact_phone stay NULL — nothing to map.

Companies are processed sorted by legacy id so generated slug suffixes
(acme-2) stay stable across re-runs. Idempotent — safe to re-run.

Usage:
    python scripts/company.py
"""

import os
import re
from pathlib import Path

import requests
import psycopg
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

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
    """Fetch every page of a Strapi collection endpoint (data/meta envelope)."""
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


def main():
    conn = psycopg.connect(DATABASE_URL)
    print("connected to:", DATABASE_URL.rsplit("/", 1)[-1])

    companies = sorted(fetch_all("/api/companies", {"populate": "icon"}), key=lambda c: c["id"])
    print(f"fetched {len(companies)} companies")

    skipped_companies = []
    used_slugs = set()

    def unique_slug(base):
        base = base or "company"
        slug, n = base, 2
        while slug in used_slugs:
            slug = f"{base}-{n}"
            n += 1
        used_slugs.add(slug)
        return slug

    with conn.cursor() as cur:
        for c in companies:
            a = attrs(c)
            name = (a.get("name") or "").strip()
            if not name:
                skipped_companies.append(c["id"])
                continue
            slug = unique_slug(slugify(name))

            # icon -> media row (reuses the row media.py created for the same url)
            icon, icon_media_id = rel(a.get("icon")), None
            if icon and icon.get("url"):
                url = icon["url"].strip()
                if url.startswith("/"):
                    url = CMS_BASE_URL + url
                cur.execute("SELECT id FROM media WHERE url = %s", (url,))
                row = cur.fetchone()
                if not row:
                    cur.execute(
                        """
                        INSERT INTO media (url, mime_type, alt, width, height)
                        VALUES (%s, %s, %s, %s, %s) RETURNING id
                        """,
                        (url, icon.get("mime"), icon.get("alternativeText") or icon.get("name"),
                         icon.get("width"), icon.get("height")),
                    )
                    row = cur.fetchone()
                icon_media_id = row[0]

            cur.execute(
                """
                INSERT INTO companies (name, slug, website, icon_media_id, status)
                VALUES (%s, %s, %s, %s, 'active')
                ON CONFLICT (slug) DO UPDATE
                SET name = EXCLUDED.name,
                    website = EXCLUDED.website,
                    icon_media_id = EXCLUDED.icon_media_id
                """,
                (name, slug, (a.get("website") or "").strip() or None, icon_media_id),
            )

    conn.commit()
    print(f"upserted companies; skipped (no name): {skipped_companies}")

    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM companies")
        print("companies total :", cur.fetchone()[0])
        cur.execute("SELECT COUNT(*) FROM companies WHERE icon_media_id IS NOT NULL")
        print("with icon       :", cur.fetchone()[0])
    conn.close()


if __name__ == "__main__":
    main()
