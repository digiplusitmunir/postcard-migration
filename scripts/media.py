"""Media migration — legacy Strapi upload `files` -> new `media` table.

Migration 2a of the run order (after geo, before company/user migration).

The upload plugin endpoint /api/upload/files returns FLAT objects (no
data/attributes envelope). Pagination support varies by Strapi version, so
the fetch loop guards against a server that ignores the pagination params.

Mapping: url (made absolute when relative) -> url, mime -> mime_type,
alternativeText (fallback caption, then name) -> alt, width/height as-is.
formats, hash, ext, size, caption, provider, folder are DROPPED.

media.url has no unique constraint, so idempotency is select-then-insert
on url. Safe to re-run.

Usage:
    python scripts/media.py
"""

import os
from pathlib import Path

import requests
import psycopg
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

CMS_BASE_URL = os.environ["CMS_BASE_URL"].rstrip("/")
HEADERS = {"Authorization": f"Bearer {os.environ['CMS_API_TOKEN']}"}
DATABASE_URL = os.environ["DATABASE_URL"]


def fetch_files():
    files, seen, start, limit = [], set(), 0, 100
    while True:
        r = requests.get(
            f"{CMS_BASE_URL}/api/upload/files",
            headers=HEADERS,
            params={"pagination[start]": start, "pagination[limit]": limit, "sort": "id"},
            timeout=60,
        )
        r.raise_for_status()
        body = r.json()
        batch = body["results"] if isinstance(body, dict) else body
        new = [f for f in batch if f["id"] not in seen]
        if not new:  # server ignored pagination (returned everything) or done
            return files
        files.extend(new)
        seen.update(f["id"] for f in new)
        if len(batch) < limit:
            return files
        start += limit


def main():
    conn = psycopg.connect(DATABASE_URL)
    print("connected to:", DATABASE_URL.rsplit("/", 1)[-1])

    legacy_files = fetch_files()
    print(f"fetched {len(legacy_files)} files")

    inserted = updated = skipped_no_url = 0
    seen_urls = set()

    with conn.cursor() as cur:
        for f in legacy_files:
            url = (f.get("url") or "").strip()
            if not url:
                skipped_no_url += 1
                continue
            if url.startswith("/"):  # relative upload path -> absolute
                url = CMS_BASE_URL + url
            if url in seen_urls:  # legacy duplicates collapse into one media row
                continue
            seen_urls.add(url)

            alt = f.get("alternativeText") or f.get("caption") or f.get("name") or None
            mime = f.get("mime")
            width, height = f.get("width"), f.get("height")

            cur.execute("SELECT id FROM media WHERE url = %s", (url,))
            row = cur.fetchone()
            if row:
                cur.execute(
                    """
                    UPDATE media SET mime_type = %s, alt = %s, width = %s, height = %s
                    WHERE id = %s
                    """,
                    (mime, alt, width, height, row[0]),
                )
                updated += 1
            else:
                cur.execute(
                    """
                    INSERT INTO media (url, mime_type, alt, width, height)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (url, mime, alt, width, height),
                )
                inserted += 1

    conn.commit()
    print(f"media inserted: {inserted}, updated: {updated}, skipped (no url): {skipped_no_url}")

    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM media")
        print("media total :", cur.fetchone()[0])
    conn.close()


if __name__ == "__main__":
    main()
