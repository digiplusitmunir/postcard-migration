"""Media migration — legacy Strapi upload `files` -> new `media` table.

Migration step 3 of the run order.

The tracker calls this an EXACT match ("no field changes"), and the new `media`
table now really is one: every field the upload plugin exposes has a column.

  legacy id       -> legacy_id  (UNIQUE — the permanent old->new mapping the
                                 tracker asks for, and this script's idempotency
                                 key; no separate map file is needed)
  url             -> url        (made absolute when the plugin returns a
                                 relative upload path)
  name            -> name
  alternativeText -> alt
  caption         -> caption    (no longer folded into alt)
  mime            -> mime_type
  ext / hash / size / provider / previewUrl / provider_metadata / width / height
                  -> same-named columns

Nothing is dropped. `formats` is not exposed by this endpoint and therefore has
no column.

Legacy duplicates are NOT collapsed: one legacy file = one media row, so every
legacy id keeps a mapping. Two rows may share a url; that is intentional and
harmless.

Idempotent — upsert on legacy_id. Safe to re-run.

Usage:
    python scripts/media.py
"""

import requests
from psycopg.types.json import Json

from _common import CMS_BASE_URL, HEADERS, MEDIA_COLUMNS, absolute_url, connect, media_values


def fetch_files():
    """The upload endpoint returns FLAT objects (no data/attributes envelope)
    and its pagination support varies by Strapi version, so guard against a
    server that ignores the pagination params and returns everything at once."""
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
    conn = connect()

    legacy_files = sorted(fetch_files(), key=lambda f: f["id"])
    print(f"fetched {len(legacy_files)} files")

    upserted = skipped_no_url = 0

    with conn.cursor() as cur:
        for f in legacy_files:
            if not absolute_url(f.get("url")):
                skipped_no_url += 1
                continue
            cur.execute(
                f"""
                INSERT INTO media ({MEDIA_COLUMNS})
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (legacy_id) DO UPDATE
                SET url               = EXCLUDED.url,
                    name              = EXCLUDED.name,
                    alt               = EXCLUDED.alt,
                    caption           = EXCLUDED.caption,
                    mime_type         = EXCLUDED.mime_type,
                    ext               = EXCLUDED.ext,
                    hash              = EXCLUDED.hash,
                    size              = EXCLUDED.size,
                    provider          = EXCLUDED.provider,
                    preview_url       = EXCLUDED.preview_url,
                    provider_metadata = EXCLUDED.provider_metadata,
                    width             = EXCLUDED.width,
                    height            = EXCLUDED.height
                """,
                media_values(f),
            )
            upserted += 1

    conn.commit()
    print(f"media upserted: {upserted}, skipped (no url): {skipped_no_url}")

    with conn.cursor() as cur:
        for label, q in [
            ("media total",        "SELECT COUNT(*) FROM media"),
            ("with legacy_id",     "SELECT COUNT(*) FROM media WHERE legacy_id IS NOT NULL"),
            ("with alt",           "SELECT COUNT(*) FROM media WHERE alt IS NOT NULL"),
            ("with caption",       "SELECT COUNT(*) FROM media WHERE caption IS NOT NULL"),
            ("with dimensions",    "SELECT COUNT(*) FROM media WHERE width IS NOT NULL"),
            ("distinct urls",      "SELECT COUNT(DISTINCT url) FROM media"),
        ]:
            cur.execute(q)
            print(f"{label:18}: {cur.fetchone()[0]}")
    conn.close()


if __name__ == "__main__":
    main()
