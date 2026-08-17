"""Journey migration — legacy Strapi `property_itineraries` -> new
`subcollections` (SubcollectionType 'Journey' under Properties), plus the
ordered `subcollection_postcards` join.

Migration step 9 of the run order (run AFTER directory_album.py and
postcard.py — it consumes both of their per-environment map files).

Field mapping (verified against the live API — 24 itineraries in prod)
----------------------------------------------------------------------
  title               -> name
  description         -> intro
  dayWiseItinerary    -> day_wise_itinerary   (NOT `story` — story stays free
                         for real editorial narrative)
  termsAndConditions  -> terms_and_conditions (NOT `tour_info` — same reason)
  coverImage          -> cover_media_id
  album               -> collection_id        (required in v2)
  slug                -> slug
  createdByUser       -> created_by_user_id   (R3: direct FK, not a Circle)
  status              -> status               (JourneyStatus, 1:1 — see below)
  postcards (M2M)     -> subcollection_postcards, sequence_order = legacy order
  country             -> dropped; a Journey inherits geo from its parent
                         Collection

Stay Details component (R5)
---------------------------
  price               -> price
  priceType           -> price_type ENUM ('per person'/'twin sharing' ->
                         per_person/twin_sharing)
  numberOfDays        -> number_of_days
  numberOfNights      -> number_of_nights
  best_time_to_visits -> best_months (JSON array of month names)
  (new)               -> number_of_rooms, guests_per_room — no legacy source

`price_type` is the important fix here. The previous version of this script
DISCARDED priceType and only printed the non-default rows for review, so all 10
'twin sharing' itineraries in prod were migrated as if priced per person — a
silent pricing error. The retracted `price_starting_at` column is gone: the
legacy schema has ONE price, and the second displayed price is calculated off
it at read time.

Status is now 1:1, not collapsed. The old STATUS_MAP folded
deckFreeze/onTrip/complete into 'live' and everything else into 'draft',
destroying the distinction between a frozen deck, a trip in progress and a
finished one. Prod has deckFreeze 11, draft 9, complete 4.

Notes
-----
- `managed_by_company_id` inherited from the parent collection.
- Itineraries with no album, or whose album is not a collection (Designer Tours,
  or a non-dedicated type whose album became a postcard), are skipped -> manual
  review lists.
- Postcards whose collection differs from the journey's violate the schema
  invariant -> skipped + flagged.
- `best_time_to_visits` is empty on every itinerary (the legacy Month collection
  has 0 rows), so best_months stays NULL. `createdByUser` is likewise unset on
  all 24 — the column exists for new v2 content.
- Writes `legacy_itinerary_id_map{_dev,_prod}.json` for the Enquiry/Circle work.

Idempotent — subcollections upsert on slug, join rows upsert on their PK.

Usage:
    python scripts/journey.py
"""

from collections import Counter

from psycopg.types.json import Json

from _common import (MediaResolver, SlugAllocator, attrs, connect, fetch_all,
                     load_map, rel, rel_many, save_map, slugify)

# legacy status -> JourneyStatus. 1:1; unknown/missing values fall back to draft.
STATUS_MAP = {
    "draft": "draft",
    "deckBuild": "deckBuild",
    "deckFreeze": "deckFreeze",
    "onTrip": "onTrip",
    "complete": "complete",
}

# legacy priceType -> PriceType enum
PRICE_TYPE_MAP = {
    "per person": "per_person",
    "twin sharing": "twin_sharing",
}


def load_lookups(conn):
    with conn.cursor() as cur:
        cur.execute("SELECT id FROM subcollection_types WHERE slug = 'journey'")
        row = cur.fetchone()
        if not row:
            raise SystemExit("subcollection_types has no 'journey' row — run scripts/seed.py first")
        journey_type_id = row[0]
        cur.execute("SELECT id, managed_by_company_id FROM collections")
        company_by_collection = dict(cur.fetchall())
    print(f"journey subcollection_type id: {journey_type_id}")
    print(f"lookups: {len(company_by_collection)} collections")
    return journey_type_id, company_by_collection


def migrate_journeys(conn, itineraries, album_map, user_map):
    """property-itinerary -> subcollections. Returns
    ({legacy itinerary id: new subcollection id}, {legacy itinerary id: collection id})."""
    journey_type_id, company_by_collection = load_lookups(conn)
    media = MediaResolver(conn)
    slugs = SlugAllocator(fallback="journey")

    itinerary_map = {}   # legacy itinerary id -> new subcollection id
    collection_of = {}   # legacy itinerary id -> new collection id (for the join invariant)

    skipped_no_title, skipped_no_album, skipped_unmigrated_album = [], [], []
    unknown_price_type, unmapped_creators = [], set()
    status_counts, price_type_counts = Counter(), Counter()

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
            if not collection_id:
                # Designer Tours (-> dx-card migration later), or an album of a
                # non-dedicated type which is now a postcard — either way there
                # is no parent Collection to hang this Journey off
                skipped_unmigrated_album.append((it["id"], title, album.get("name")))
                continue

            # best_time_to_visits month rows -> best_months JSON (legacy order kept)
            months = [m.get("name") for m in rel_many(a.get("best_time_to_visits")) if m.get("name")]

            legacy_status = a.get("status")
            status = STATUS_MAP.get(legacy_status, "draft")
            status_counts[f"{legacy_status} -> {status}"] += 1

            raw_price_type = (a.get("priceType") or "").strip().lower() or None
            price_type = PRICE_TYPE_MAP.get(raw_price_type) if raw_price_type else None
            if raw_price_type and not price_type:
                unknown_price_type.append((it["id"], title, a.get("priceType")))
            price_type_counts[price_type] += 1

            creator = rel(a.get("createdByUser"))
            creator_id = None
            if creator:
                creator_id = user_map.get(creator["id"])
                if not creator_id:
                    unmapped_creators.add(creator["id"])

            slug = slugs.take((a.get("slug") or "").strip() or slugify(title))
            cover_id = media.resolve(cur, rel(a.get("coverImage")))

            cur.execute(
                """
                INSERT INTO subcollections
                    (subcollection_type_id, collection_id, name, intro, story, slug,
                     tour_info, day_wise_itinerary, terms_and_conditions,
                     price, price_type, number_of_nights, number_of_days,
                     number_of_rooms, guests_per_room, best_months,
                     cover_media_id, managed_by_company_id, created_by_user_id, status)
                VALUES (%s, %s, %s, %s, NULL, %s, NULL, %s, %s,
                        %s, %s, %s, %s, NULL, NULL, %s, %s, %s, %s, %s)
                ON CONFLICT (slug) DO UPDATE
                SET subcollection_type_id = EXCLUDED.subcollection_type_id,
                    collection_id = EXCLUDED.collection_id,
                    name = EXCLUDED.name,
                    intro = EXCLUDED.intro,
                    day_wise_itinerary = EXCLUDED.day_wise_itinerary,
                    terms_and_conditions = EXCLUDED.terms_and_conditions,
                    price = EXCLUDED.price,
                    price_type = EXCLUDED.price_type,
                    number_of_nights = EXCLUDED.number_of_nights,
                    number_of_days = EXCLUDED.number_of_days,
                    best_months = EXCLUDED.best_months,
                    cover_media_id = EXCLUDED.cover_media_id,
                    managed_by_company_id = EXCLUDED.managed_by_company_id,
                    created_by_user_id = EXCLUDED.created_by_user_id,
                    status = EXCLUDED.status
                RETURNING id
                """,
                (journey_type_id, collection_id, title,
                 (a.get("description") or "").strip() or None,
                 slug,
                 (a.get("dayWiseItinerary") or "").strip() or None,
                 (a.get("termsAndConditions") or "").strip() or None,
                 a.get("price"),
                 price_type,
                 a.get("numberOfNights"),
                 a.get("numberOfDays"),
                 Json(months) if months else None,
                 cover_id,
                 company_by_collection.get(collection_id),
                 creator_id,
                 status),
            )
            itinerary_map[it["id"]] = cur.fetchone()[0]
            collection_of[it["id"]] = collection_id

    conn.commit()
    print(f"subcollections upserted: {len(itinerary_map)}")
    print(f"status (legacy -> v2): {dict(status_counts)}")
    print(f"price_type: {dict(price_type_counts)}")
    print(f"media rows created by this step: {media.created}")
    print(f"skipped (no title): {skipped_no_title}")
    print(f"skipped (no album — a Journey needs a parent Property) ({len(skipped_no_album)}): {skipped_no_album}")
    print(f"skipped, album is not a collection = Designer Tours or a non-dedicated "
          f"type ({len(skipped_unmigrated_album)}): {skipped_unmigrated_album}")
    print(f"MANUAL REVIEW unmapped priceType values ({len(unknown_price_type)}): {unknown_price_type}")
    print(f"MANUAL REVIEW createdByUser not in user map ({len(unmapped_creators)}): {sorted(unmapped_creators)}")
    return itinerary_map, collection_of


def link_postcards(conn, itineraries, itinerary_map, collection_of, postcard_map):
    """postcards m2m -> subcollection_postcards. sequence_order = position in the
    legacy relation order (Day 1, Day 2, ...). Skips postcards violating the
    collection invariant; re-runs refresh the order."""
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
                if not new_pid:  # postcard skipped upstream (Designer Tours)
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
          f"(invariant — skipped) ({len(cross_property)}): {cross_property[:20]}")


def verify(conn):
    with conn.cursor() as cur:
        for label, q in [
            ("subcollections total",     "SELECT COUNT(*) FROM subcollections"),
            ("journeys",                 "SELECT COUNT(*) FROM subcollections s JOIN subcollection_types t ON t.id = s.subcollection_type_id WHERE t.slug = 'journey'"),
            ("with price",               "SELECT COUNT(*) FROM subcollections WHERE price IS NOT NULL"),
            ("  per_person",             "SELECT COUNT(*) FROM subcollections WHERE price_type = 'per_person'"),
            ("  twin_sharing",           "SELECT COUNT(*) FROM subcollections WHERE price_type = 'twin_sharing'"),
            ("with nights",              "SELECT COUNT(*) FROM subcollections WHERE number_of_nights IS NOT NULL"),
            ("with days",                "SELECT COUNT(*) FROM subcollections WHERE number_of_days IS NOT NULL"),
            ("with day_wise_itinerary",  "SELECT COUNT(*) FROM subcollections WHERE day_wise_itinerary IS NOT NULL"),
            ("with terms",               "SELECT COUNT(*) FROM subcollections WHERE terms_and_conditions IS NOT NULL"),
            ("with cover media",         "SELECT COUNT(*) FROM subcollections WHERE cover_media_id IS NOT NULL"),
            ("with best_months",         "SELECT COUNT(*) FROM subcollections WHERE best_months IS NOT NULL"),
            ("with company",             "SELECT COUNT(*) FROM subcollections WHERE managed_by_company_id IS NOT NULL"),
            ("join rows",                "SELECT COUNT(*) FROM subcollection_postcards"),
            ("journeys w/ postcards",    "SELECT COUNT(DISTINCT subcollection_id) FROM subcollection_postcards"),
            ("empty journeys",           "SELECT COUNT(*) FROM subcollections s WHERE NOT EXISTS (SELECT 1 FROM subcollection_postcards sp WHERE sp.subcollection_id = s.id)"),
            ("dup slugs (want 0)",       "SELECT COUNT(*) FROM (SELECT slug FROM subcollections GROUP BY slug HAVING COUNT(*) > 1) d"),
            ("invariant viol. (want 0)", "SELECT COUNT(*) FROM subcollection_postcards sp JOIN subcollections s ON s.id = sp.subcollection_id JOIN postcards p ON p.id = sp.postcard_id WHERE p.collection_id IS DISTINCT FROM s.collection_id"),
        ]:
            cur.execute(q)
            print(f"{label:26}: {cur.fetchone()[0]}")
        cur.execute("SELECT status, COUNT(*) FROM subcollections GROUP BY status ORDER BY 2 DESC")
        print("status:", dict(cur.fetchall()))


def main():
    conn = connect()

    album_map = load_map("legacy_album_id_map")
    postcard_map = load_map("legacy_postcard_id_map")
    user_map = load_map("legacy_user_id_map")
    print(f"loaded {len(album_map)} album, {len(postcard_map)} postcard, {len(user_map)} user mappings")

    itineraries = sorted(fetch_all("/api/property-itineraries", {"populate": "*"}),
                         key=lambda x: x["id"])
    print(f"fetched {len(itineraries)} property-itineraries")

    itinerary_map, collection_of = migrate_journeys(conn, itineraries, album_map, user_map)
    link_postcards(conn, itineraries, itinerary_map, collection_of, postcard_map)
    save_map("legacy_itinerary_id_map", itinerary_map, "itinerary -> subcollection")

    verify(conn)
    conn.close()


if __name__ == "__main__":
    main()
