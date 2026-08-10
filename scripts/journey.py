"""Journey migration — legacy Strapi `property_itineraries` -> new
`subcollections` (SubcollectionType 'Journey' under Properties), plus the
ordered `subcollection_postcards` join (tracker row #31).

Migration step 9 of the run order (run AFTER directory_album.py and
postcard.py — it consumes both of their per-environment map files).

Scope decisions (2026-08-10):
- `album` -> `collection_id` (required in v2) via `legacy_album_id_map`.
  Itineraries with no album or an unmigrated album (Designer Tours) are
  skipped -> manual review lists.
- Field map: title -> name, description -> intro, dayWiseItinerary -> story,
  termsAndConditions -> tour_info, price -> price,
  numberOfNights -> number_of_nights, numberOfDays -> number_of_days,
  coverImage -> cover_media_id (both columns added by migration
  `20260810060000_add_subcollection_cover_and_days`).
- `best_time_to_visits` month rows -> `best_months` JSON array of month
  names, legacy order kept.
- `status`: deckFreeze / onTrip / complete -> live;
  deckBuild / draft / empty -> draft.
- `managed_by_company_id` inherited from the parent collection.
- `postcards` m2m -> `subcollection_postcards`, sequence_order = position in
  the legacy relation order. Postcards not in the postcard map (Designer
  Tours) are flagged; postcards whose collection differs from the journey's
  violate the schema invariant -> skipped + flagged.
- author circles are NOT created here — that optional step lives only in
  `notebooks/journey_migration.ipynb` (section 6).
- Dropped: priceType ('per person'/'twin sharing' — no v2 home, non-default
  rows printed for review), country (subcollection inherits geo from its
  parent collection), timestamps.
- `price_starting_at`, `guests_min`/`guests_max` stay NULL — no legacy source.
- Writes `legacy_itinerary_id_map_dev/_prod.json` (legacy itinerary id ->
  new subcollection id) for the future Enquiry/Circle migrations.

Idempotent — subcollections upsert on slug, join rows upsert on their PK
(re-runs refresh sequence_order). Safe to re-run.

Usage:
    python scripts/journey.py
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

# deckFreeze/onTrip/complete -> live; deckBuild/draft/None -> draft
STATUS_MAP = {"deckFreeze": "live", "onTrip": "live", "complete": "live"}


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


def load_map(name):
    path = ROOT / f"{name}{ENV_SUFFIX}.json"
    return {int(k): int(v) for k, v in json.loads(path.read_text()).items()}


def load_lookups(conn):
    """Journey subcollection-type id (seeded), per-collection company for the
    managed_by inheritance, media by normalized url (same as scripts/media.py)."""
    with conn.cursor() as cur:
        cur.execute("SELECT id FROM subcollection_types WHERE slug = 'journey'")
        row = cur.fetchone()
        assert row, "subcollection_types has no 'journey' row — run scripts/seed.py first"
        journey_type_id = row[0]
        cur.execute("SELECT id, managed_by_company_id FROM collections")
        company_by_collection = dict(cur.fetchall())
        cur.execute("SELECT url, id FROM media")
        media_by_url = dict(cur.fetchall())

    print(f"journey subcollection_type id: {journey_type_id}")
    print(f"lookups: {len(company_by_collection)} collections, {len(media_by_url)} media")
    return journey_type_id, company_by_collection, media_by_url


def migrate_journeys(conn, itineraries, album_map):
    """property-itinerary -> subcollections. Returns
    ({legacy itinerary id: new subcollection id}, {legacy itinerary id: collection id})."""
    journey_type_id, company_by_collection, media_by_url = load_lookups(conn)

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
        base = base or "journey"
        slug, n = base, 2
        while slug in used_slugs:
            slug = f"{base}-{n}"
            n += 1
        used_slugs.add(slug)
        return slug

    itinerary_map = {}   # legacy itinerary id -> new subcollection id
    collection_of = {}   # legacy itinerary id -> new collection id (for the join invariant)

    skipped_no_title, skipped_no_album, skipped_unmigrated_album = [], [], []
    twin_sharing = []    # dropped priceType != 'per person' -> manual review
    status_counts = {}

    with conn.cursor() as cur:
        for it in itineraries:
            a = attrs(it)
            title = (a.get("title") or "").strip()
            if not title:
                skipped_no_title.append(it["id"])
                continue

            # album -> parent collection (required in v2)
            album = rel(a.get("album"))
            if not album:
                skipped_no_album.append((it["id"], title))
                continue
            collection_id = album_map.get(album["id"])
            if not collection_id:  # Designer Tours album -> dx-card migration later
                skipped_unmigrated_album.append((it["id"], title, album.get("name")))
                continue

            # best_time_to_visits month rows -> best_months JSON (legacy order kept)
            months = [m.get("name") for m in rel_many(a.get("best_time_to_visits")) if m.get("name")]

            legacy_status = a.get("status")
            status_counts[legacy_status] = status_counts.get(legacy_status, 0) + 1
            status = STATUS_MAP.get(legacy_status, "draft")

            if (a.get("priceType") or "per person") != "per person":
                twin_sharing.append((it["id"], title, a.get("priceType"), a.get("price")))

            slug = unique_slug((a.get("slug") or "").strip() or slugify(title))
            cover_id = media_id_for(rel(a.get("coverImage")), cur)

            cur.execute(
                """
                INSERT INTO subcollections
                    (subcollection_type_id, collection_id, name, intro, story, slug,
                     tour_info, price, price_starting_at, number_of_nights, number_of_days,
                     cover_media_id, guests_min, guests_max, best_months,
                     managed_by_company_id, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NULL, %s, %s, %s, NULL, NULL, %s, %s, %s)
                ON CONFLICT (slug) DO UPDATE
                SET subcollection_type_id = EXCLUDED.subcollection_type_id,
                    collection_id = EXCLUDED.collection_id,
                    name = EXCLUDED.name,
                    intro = EXCLUDED.intro,
                    story = EXCLUDED.story,
                    tour_info = EXCLUDED.tour_info,
                    price = EXCLUDED.price,
                    number_of_nights = EXCLUDED.number_of_nights,
                    number_of_days = EXCLUDED.number_of_days,
                    cover_media_id = EXCLUDED.cover_media_id,
                    best_months = EXCLUDED.best_months,
                    managed_by_company_id = EXCLUDED.managed_by_company_id,
                    status = EXCLUDED.status
                RETURNING id
                """,
                (journey_type_id, collection_id, title,
                 (a.get("description") or "").strip() or None,
                 (a.get("dayWiseItinerary") or "").strip() or None,
                 slug,
                 (a.get("termsAndConditions") or "").strip() or None,
                 a.get("price"),
                 a.get("numberOfNights"),
                 a.get("numberOfDays"),
                 cover_id,
                 Json(months) if months else None,
                 company_by_collection.get(collection_id),
                 status),
            )
            itinerary_map[it["id"]] = cur.fetchone()[0]
            collection_of[it["id"]] = collection_id

    conn.commit()
    print(f"subcollections upserted: {len(itinerary_map)}")
    print(f"legacy status counts (deckFreeze/onTrip/complete -> live): {status_counts}")
    print(f"skipped (no title): {skipped_no_title}")
    print(f"skipped (no album - journey needs a parent Property) ({len(skipped_no_album)}): {skipped_no_album}")
    print(f"skipped, album not migrated = Designer Tours ({len(skipped_unmigrated_album)}): {skipped_unmigrated_album}")
    print(f"MANUAL REVIEW priceType != 'per person' (dropped field) ({len(twin_sharing)}): {twin_sharing}")
    return itinerary_map, collection_of


def link_postcards(conn, itineraries, itinerary_map, collection_of, postcard_map):
    """postcards m2m -> subcollection_postcards. sequence_order = position in
    the legacy relation order (Day 1, Day 2, ...). Skips postcards violating
    the collection invariant; re-runs refresh the order."""
    with conn.cursor() as cur:
        cur.execute("SELECT id, collection_id FROM postcards")
        postcard_collection = dict(cur.fetchall())

    links = 0
    unmapped_postcards, cross_property = [], []

    with conn.cursor() as cur:
        for it in itineraries:
            sub_id = itinerary_map.get(it["id"])
            if not sub_id:
                continue
            coll_id = collection_of[it["id"]]
            order = 0
            for p in rel_many(attrs(it).get("postcards")):
                new_pid = postcard_map.get(p["id"])
                if not new_pid:  # postcard skipped in #16 (Designer Tours)
                    unmapped_postcards.append((it["id"], p["id"], p.get("name")))
                    continue
                if postcard_collection.get(new_pid) != coll_id:
                    cross_property.append((it["id"], p["id"], p.get("name")))
                    continue
                order += 1
                cur.execute(
                    """
                    INSERT INTO subcollection_postcards (subcollection_id, postcard_id, sequence_order)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (subcollection_id, postcard_id) DO UPDATE
                    SET sequence_order = EXCLUDED.sequence_order
                    """,
                    (sub_id, new_pid, order),
                )
                links += 1

    conn.commit()
    print(f"subcollection_postcards upserted: {links}")
    print(f"MANUAL REVIEW postcard not in map ({len(unmapped_postcards)}): {unmapped_postcards[:20]}")
    print(f"MANUAL REVIEW postcard belongs to a different collection than the journey "
          f"(invariant - skipped) ({len(cross_property)}): {cross_property[:20]}")


def verify(conn):
    with conn.cursor() as cur:
        for label, q in [
            ("subcollections total",     "SELECT COUNT(*) FROM subcollections"),
            ("journeys",                 "SELECT COUNT(*) FROM subcollections s JOIN subcollection_types t ON t.id = s.subcollection_type_id WHERE t.slug = 'journey'"),
            ("with price",               "SELECT COUNT(*) FROM subcollections WHERE price IS NOT NULL"),
            ("with nights",              "SELECT COUNT(*) FROM subcollections WHERE number_of_nights IS NOT NULL"),
            ("with days",                "SELECT COUNT(*) FROM subcollections WHERE number_of_days IS NOT NULL"),
            ("with cover media",         "SELECT COUNT(*) FROM subcollections WHERE cover_media_id IS NOT NULL"),
            ("with best_months",         "SELECT COUNT(*) FROM subcollections WHERE best_months IS NOT NULL"),
            ("with company",             "SELECT COUNT(*) FROM subcollections WHERE managed_by_company_id IS NOT NULL"),
            ("status = live",            "SELECT COUNT(*) FROM subcollections WHERE status = 'live'"),
            ("join rows",                "SELECT COUNT(*) FROM subcollection_postcards"),
            ("journeys w/ postcards",    "SELECT COUNT(DISTINCT subcollection_id) FROM subcollection_postcards"),
            ("empty journeys",           "SELECT COUNT(*) FROM subcollections s WHERE NOT EXISTS (SELECT 1 FROM subcollection_postcards sp WHERE sp.subcollection_id = s.id)"),
            ("dup slugs (want 0)",       "SELECT COUNT(*) FROM (SELECT slug FROM subcollections GROUP BY slug HAVING COUNT(*) > 1) d"),
            ("invariant viol. (want 0)", "SELECT COUNT(*) FROM subcollection_postcards sp JOIN subcollections s ON s.id = sp.subcollection_id JOIN postcards p ON p.id = sp.postcard_id WHERE p.collection_id IS DISTINCT FROM s.collection_id"),
        ]:
            cur.execute(q)
            print(f"{label:26}: {cur.fetchone()[0]}")


def main():
    conn = psycopg.connect(DATABASE_URL)
    print("connected to:", DATABASE_URL.rsplit("/", 1)[-1])

    album_map = load_map("legacy_album_id_map")
    postcard_map = load_map("legacy_postcard_id_map")
    print(f"loaded {len(album_map)} album mappings, {len(postcard_map)} postcard mappings ({ENV_SUFFIX or 'no suffix'})")

    itineraries = sorted(fetch_all("/api/property-itineraries", {"populate": "*"}), key=lambda x: x["id"])
    print(f"fetched {len(itineraries)} property-itineraries")

    itinerary_map, collection_of = migrate_journeys(conn, itineraries, album_map)
    link_postcards(conn, itineraries, itinerary_map, collection_of, postcard_map)

    out = ROOT / f"legacy_itinerary_id_map{ENV_SUFFIX}.json"
    out.write_text(json.dumps({str(k): str(v) for k, v in itinerary_map.items()}, indent=2))
    print(f"saved {len(itinerary_map)} legacy->new itinerary id mappings to {out}")

    verify(conn)
    conn.close()


if __name__ == "__main__":
    main()
