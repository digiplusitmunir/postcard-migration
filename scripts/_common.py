"""Shared helpers for every migration script.

Extracted so the Strapi envelope handling, the paginated fetch and — most
importantly — the media find-or-create live in ONE place. Before this module
six scripts each carried their own `media_id_for` that inserted only
(url, mime_type, alt, width, height); with the widened `media` table those
copies would have created impoverished rows for any file `media.py` had not
already loaded.

Import from a sibling script:

    from _common import (CMS_BASE_URL, DATABASE_URL, ENV_SUFFIX, ROOT,
                         attrs, rel, rel_many, fetch_all, slugify,
                         connect, load_map, save_map, MediaResolver,
                         SlugAllocator)
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
ENV_SUFFIX = {"development": "_dev", "production": "_prod"}.get(
    DATABASE_URL.rsplit("/", 1)[-1], ""
)


# -----------------------------------------------------------------------------
# Strapi payload helpers
# -----------------------------------------------------------------------------

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


def fetch_all(path, params=None, timeout=120):
    """Fetch every page of a Strapi collection endpoint (data/meta envelope)."""
    items, page = [], 1
    while True:
        p = {"pagination[page]": page, "pagination[pageSize]": 100, "sort": "id",
             **(params or {})}
        r = requests.get(f"{CMS_BASE_URL}{path}", headers=HEADERS, params=p, timeout=timeout)
        r.raise_for_status()
        body = r.json()
        data = body["data"] if isinstance(body, dict) else body
        items.extend(data)
        pg = body.get("meta", {}).get("pagination", {}) if isinstance(body, dict) else {}
        if page >= pg.get("pageCount", 1):
            return items
        page += 1


def absolute_url(url):
    """Normalize an upload url the same way everywhere, so media rows are
    matched and never duplicated."""
    url = (url or "").strip()
    if not url:
        return None
    return CMS_BASE_URL + url if url.startswith("/") else url


# -----------------------------------------------------------------------------
# DB helpers
# -----------------------------------------------------------------------------

def connect():
    conn = psycopg.connect(DATABASE_URL)
    print("connected to:", DATABASE_URL.rsplit("/", 1)[-1])
    return conn


def load_map(name, required=True):
    """Read a legacy->new id map written by an earlier step."""
    path = ROOT / f"{name}{ENV_SUFFIX}.json"
    if not path.exists():
        if required:
            raise SystemExit(
                f"missing {path.name} — run the migration step that produces it first"
            )
        return {}
    return {int(k): int(v) for k, v in json.loads(path.read_text()).items()}


def save_map(name, mapping, label=None):
    out = ROOT / f"{name}{ENV_SUFFIX}.json"
    out.write_text(json.dumps({str(k): str(v) for k, v in mapping.items()}, indent=2))
    print(f"saved {len(mapping)} {label or name} mappings to {out}")
    return out


# -----------------------------------------------------------------------------
# Media
# -----------------------------------------------------------------------------

MEDIA_COLUMNS = (
    "legacy_id, url, name, alt, caption, mime_type, ext, hash, size, provider, "
    "preview_url, provider_metadata, width, height"
)


def media_values(f):
    """Map a populated Strapi upload-file object onto the `media` columns."""
    from psycopg.types.json import Json
    url = absolute_url(f.get("url"))
    meta = f.get("provider_metadata")
    return (
        f.get("id"),
        url,
        f.get("name"),
        f.get("alternativeText"),
        f.get("caption"),
        f.get("mime"),
        f.get("ext"),
        f.get("hash"),
        f.get("size"),
        f.get("provider"),
        f.get("previewUrl"),
        Json(meta) if meta else None,
        f.get("width"),
        f.get("height"),
    )


class MediaResolver:
    """Find-or-create a `media` row for a populated Strapi file.

    Resolution order: legacy id (the stable key written by media.py), then
    normalized url (covers files that arrived through a relation before
    media.py ever saw them). Caches both keys in-process.
    """

    def __init__(self, conn):
        with conn.cursor() as cur:
            cur.execute("SELECT legacy_id, id FROM media WHERE legacy_id IS NOT NULL")
            self.by_legacy = dict(cur.fetchall())
            cur.execute("SELECT url, id FROM media")
            self.by_url = dict(cur.fetchall())
        self.created = 0

    def resolve(self, cur, image, fallback_url=None):
        """Return a media id for `image` (a populated upload object), or None."""
        if not image and not fallback_url:
            return None
        image = image or {}
        legacy_id = image.get("id")
        if legacy_id is not None and legacy_id in self.by_legacy:
            return self.by_legacy[legacy_id]

        url = absolute_url(image.get("url") or fallback_url)
        if not url:
            return None
        if url in self.by_url:
            mid = self.by_url[url]
            if legacy_id is not None:
                self.by_legacy[legacy_id] = mid
            return mid

        payload = dict(image)
        payload["url"] = url
        cur.execute(
            f"INSERT INTO media ({MEDIA_COLUMNS}) "
            f"VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) "
            f"ON CONFLICT (legacy_id) DO UPDATE SET url = EXCLUDED.url "
            f"RETURNING id",
            media_values(payload),
        )
        mid = cur.fetchone()[0]
        self.by_url[url] = mid
        if legacy_id is not None:
            self.by_legacy[legacy_id] = mid
        self.created += 1
        return mid


# -----------------------------------------------------------------------------
# Slugs
# -----------------------------------------------------------------------------

class SlugAllocator:
    """Hand out unique slugs within one namespace.

    `reserved` are slugs owned by rows this run must not overwrite. Processing
    callers id-sorted keeps generated `foo-2` suffixes stable across re-runs.
    """

    def __init__(self, reserved=(), fallback="item"):
        self.used = set(reserved)
        self.fallback = fallback

    def take(self, base):
        base = base or self.fallback
        slug, n = base, 2
        while slug in self.used:
            slug = f"{base}-{n}"
            n += 1
        self.used.add(slug)
        return slug

    def keep(self, slug):
        """Re-claim a slug this row already owns (stable re-runs)."""
        self.used.add(slug)
        return slug
