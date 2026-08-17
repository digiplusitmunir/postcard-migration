"""Directory/Album migration — legacy `directories` -> `collection_types` and
`albums` -> `collections` OR `postcards`.

Migration step 6 of the run order (run AFTER geo, media, company and users).

Split rule
----------
Albums only become collections for collection types that have a real Collection
layer (`has_dedicated_collection = true`, i.e. Properties). Albums under
Restaurants / Events / Shopping have no Collection to live in — they ARE the
content, so they migrate straight into `postcards` with `collection_id = NULL`.
Prod: 2067 Properties albums, 673 R/E/S albums, 59 Designer Tours (skipped —
they belong to the dx-card / Destination Expert migration), 35 with no directory.

Field mapping (verified against the live API)
---------------------------------------------
  name / intro / story / slug          -> same
  coverImage                           -> cover_media_id
  isFeatured / priority                -> is_featured / priority
  country / region / locality          -> country_id / region_id / locality_id
                                          (R1: no city tier, 3 FKs not 4)
  directories (M2M)                    -> collection_type_id (single FK)
  website / signature                  -> website / signature
  user                                 -> owner_user_id       (R3: direct FK)
  assignTo                             -> assigned_to_user_id (R3: direct FK)
  galleryCollection                    -> gallery (Json)
  seo                                  -> seo (Json)
  sustainability                       -> about               (renamed)
  company / companySlug                -> managed_by_company_id
  status (else isActive)               -> status
  lat / long / placeId / locationLink  -> location (Json component)
  date                                 -> event_details.start_date (Events)

The migration tracker claimed media_kit / additionalInfo / sustainability /
status / priority / company were "not in the real v1 Album schema". They ARE —
verified on the live API: media_kit 1461, additionalInfo 1406, sustainability
47, status 1728, priority 2833, company 324, signature 946.

Of those, `media_kit` and `additionalInfo` are DROPPED by product decision
(2026-08-17) — the app no longer uses them, and the v2 schema has no column for
either. `sustainability` is kept but renamed to `about`: the field holds the
property's general "about" copy rather than a sustainability-only block.
status / priority / company are kept and migrated as-is.

Genuinely dropped (verified empty on every album): album_themes (0),
fixedDates (0), placeId (0), locationLink (0). Archived, not migrated:
news_article (287, editorial press links — no v2 home), on_boarding (2826,
internal partner-onboarding workflow), bestMonth (3), avgPricePerPerson /
pricesStartingAt / numberOfNights / numberOfGuests* / bestTimetoTravel /
tourInfo (Journey fields that belong to property_itineraries, not Album),
cuisines (525 — migrated instead by category_environment_facet.py).

Writes two per-environment map files for the downstream migrations:
- `legacy_album_id_map{_dev,_prod}.json`          legacy album id -> collection id
- `legacy_album_postcard_id_map{_dev,_prod}.json` legacy album id -> postcard id

Idempotent — upsert on slug. Safe to re-run.

Usage:
    python scripts/directory_album.py
"""

from collections import Counter

from psycopg.types.json import Json

from _common import (MediaResolver, SlugAllocator, absolute_url, attrs, connect,
                     fetch_all, load_map, rel, rel_many, save_map, slugify)

# legacy directory slug -> (name, slug, has_dedicated_collection, priority)
# has_dedicated_collection = False means albums of this type become POSTCARDS
DIRECTORY_TO_CT = {
    "mindful-luxury-hotels": ("Properties",  "properties",  True,  1),  # Postcard StarPartner Stays
    "food-and-beverages":    ("Restaurants", "restaurants", False, 2),  # Food and Beverages
    "postcard-events":       ("Events",      "events",      False, 3),  # Postcard Events
    "postcard-shopping":     ("Shopping",    "shopping",    False, 4),  # Postcard Shopping
}
SKIP_DIRECTORY_SLUGS = {"mindful-luxury-tours"}  # Designer Tours -> dx-card migration later

VALID_STATUS = {"draft", "assigned", "submit", "rework", "live"}


def migrate_directories(conn):
    """Directory -> collection_types.

    Returns (DIR_ID_TO_CT, DEFAULT_CT_ID, SKIPPED_DIR_IDS, DEDICATED_CT_IDS).
    """
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

            logo = rel(a.get("logo"))
            icon = absolute_url(logo.get("url")) if logo else None

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

    # read has_dedicated_collection back from the DB so the album split follows
    # the stored flag (seed.py owns types this migration never touches, e.g.
    # Destination Expert) rather than only the DIRECTORY_TO_CT literal
    with conn.cursor() as cur:
        cur.execute("SELECT slug, id, has_dedicated_collection FROM collection_types")
        rows = cur.fetchall()
    ct_id_by_slug = {s: i for s, i, _ in rows}
    dedicated_ct_ids = {i for _, i, ded in rows if ded}

    dir_id_to_ct = {did: ct_id_by_slug[s] for did, s in dir_id_to_ct_slug.items()}
    default_ct_id = ct_id_by_slug["properties"]  # fallback for albums with no directory

    print("collection_types         :", ct_id_by_slug)
    print("directory -> ct id       :", dir_id_to_ct)
    print("dedicated ct ids         :", dedicated_ct_ids, "(others -> albums become postcards)")
    print("skipped directory ids    :", skipped_dir_ids)   # Designer Tours
    print("MANUAL REVIEW (unmapped) :", unmapped_dirs)     # should be empty
    return dir_id_to_ct, default_ct_id, skipped_dir_ids, dedicated_ct_ids


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
        cur.execute("SELECT LOWER(title), id FROM companies")
        company_by_name = dict(cur.fetchall())
        cur.execute("SELECT slug, id FROM companies")
        company_by_slug = dict(cur.fetchall())

    print(f"lookups: {len(country_by_name)} countries, {len(region_by_name_country)} regions, "
          f"{len(locality_by_name)} locality names, {len(company_by_name)} companies")
    return (country_by_name, region_by_name_country, locality_by_name,
            company_by_name, company_by_slug)


def reserved_postcard_slugs(conn, prev_album_postcard_map):
    """Postcard slugs owned by rows this migration must NOT overwrite.

    `postcards` is shared with scripts/postcard.py (legacy postcards, step 9),
    and both upsert on slug. Every existing postcard slug is reserved except the
    ones belonging to album-derived postcards from a previous run of THIS
    script — those are ours to reuse, which keeps generated slugs stable.
    """
    ours = set(prev_album_postcard_map.values())
    with conn.cursor() as cur:
        cur.execute("SELECT id, slug FROM postcards")
        rows = cur.fetchall()
    slug_by_id = {i: s for i, s in rows}
    reserved = {s for i, s in rows if i not in ours}
    return reserved, slug_by_id


def clean_json(value, drop_keys=("id",)):
    """Strapi components carry their own `id`; strip it and empty values."""
    if isinstance(value, dict):
        out = {k: v for k, v in value.items() if k not in drop_keys and v not in (None, "")}
        return out or None
    if isinstance(value, list):
        out = [clean_json(v, drop_keys) for v in value]
        out = [v for v in out if v]
        return out or None
    return value


def migrate_albums(conn, albums, dir_id_to_ct, default_ct_id, skipped_dir_ids,
                   dedicated_ct_ids, user_map):
    """Album -> collections (dedicated types) or postcards (non-dedicated types).

    Returns ({legacy album id: collection id}, {legacy album id: postcard id}).
    """
    (country_by_name, region_by_name_country, locality_by_name,
     company_by_name, company_by_slug) = load_lookups(conn)
    media = MediaResolver(conn)

    prev_album_postcard_map = load_map("legacy_album_postcard_id_map", required=False)
    reserved_pc_slugs, pc_slug_by_id = reserved_postcard_slugs(conn, prev_album_postcard_map)
    print(f"postcard slugs reserved by non-album rows: {len(reserved_pc_slugs)} "
          f"({len(prev_album_postcard_map)} album-derived postcards from a previous run)")

    # collections.slug and postcards.slug are separate unique namespaces
    coll_slugs = SlugAllocator(fallback="album")
    pc_slugs = SlugAllocator(reserved_pc_slugs, fallback="postcard")

    album_to_collection = {}       # legacy album id -> new collection id
    album_to_postcard = {}         # legacy album id -> new postcard id

    skipped_no_name, skipped_designer_tours, no_directory = [], [], []
    missing_country, missing_region, ambiguous_locality, unmatched_company = [], [], [], []
    multi_directory, unmapped_owner = [], set()
    dropped_on_postcard = []       # album fields with no postcards column
    status_counts = Counter()

    def user_id_for(u, album_id):
        """Legacy user relation -> new users.id via the step-5 map (R3)."""
        if not u:
            return None
        new_id = user_map.get(u["id"])
        if not new_id:
            unmapped_owner.add(u["id"])
        return new_id

    with conn.cursor() as cur:
        for al in albums:
            a = attrs(al)
            name = (a.get("name") or "").strip()
            if not name:
                skipped_no_name.append(al["id"])
                continue

            # directory -> collection_type; Designer Tours albums are NOT migrated
            dirs = rel_many(a.get("directories"))
            if len(dirs) > 1:
                # tracker asks for an explicit dedupe rule; prod has 0 such rows,
                # so "lowest legacy directory id wins" is recorded, not silent
                multi_directory.append((al["id"], name, [d["id"] for d in dirs]))
                dirs = sorted(dirs, key=lambda d: d["id"])
            if dirs and dirs[0]["id"] in skipped_dir_ids:
                skipped_designer_tours.append((al["id"], name))
                continue
            ct_id = dir_id_to_ct.get(dirs[0]["id"], default_ct_id) if dirs else default_ct_id
            if not dirs:
                no_directory.append((al["id"], name))

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

            cover_id = media.resolve(cur, rel(a.get("coverImage")))

            # Location component — legacy only ever populates lat/long. The rest
            # of the component (address, route, postal_code, google_place_id...)
            # comes from the Gmap Address Enrichment workstream.
            location = {k: v for k, v in {
                "lat": a.get("lat"), "lng": a.get("long"),
                "google_place_id": a.get("placeId"),
            }.items() if v not in (None, "")} or None

            # legacy status already uses the v2 vocabulary (live/assigned/rework/draft)
            status = a.get("status") if a.get("status") in VALID_STATUS \
                else ("live" if a.get("isActive") else "draft")
            status_counts[status] += 1

            website = (a.get("website") or "").strip() or None
            signature = (a.get("signature") or "").strip() or None
            seo = clean_json(a.get("seo"))
            gallery = clean_json(a.get("galleryCollection"))
            owner_id = user_id_for(rel(a.get("user")), al["id"])
            assigned_id = user_id_for(rel(a.get("assignTo")), al["id"])

            # -------------------------------------------------------------
            # non-dedicated collection type -> the album IS a postcard
            # -------------------------------------------------------------
            if ct_id not in dedicated_ct_ids:
                base = (a.get("slug") or "").strip() or slugify(name)
                # reuse the slug this album already owns, so re-runs don't drift
                prev_slug = pc_slug_by_id.get(prev_album_postcard_map.get(al["id"]))
                slug = pc_slugs.keep(prev_slug) if prev_slug else pc_slugs.take(base)

                # Events: legacy `date` is the single event day (91/91 in prod)
                event_date = a.get("date")
                event_date = event_date.strip() if isinstance(event_date, str) else event_date
                event_details = {"start_date": event_date} if event_date else None

                # `about` is collection-only (0 non-dedicated albums carry a
                # sustainability value, but report rather than lose silently).
                # media_kit / additionalInfo are dropped platform-wide by
                # product decision, so they are not reported as orphans here.
                if (a.get("sustainability") or "").strip():
                    dropped_on_postcard.append((al["id"], name, "sustainability/about"))

                cur.execute(
                    """
                    INSERT INTO postcards
                        (name, intro, slug, story, collection_type_id, collection_id,
                         user_id, country_id, region_id, locality_id, location, seo,
                         event_details, website, signature, is_featured, priority,
                         cover_media_id, status, published_at)
                    VALUES (%s, %s, %s, %s, %s, NULL, %s, %s, %s, %s, %s, %s, %s, %s,
                            %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (slug) DO UPDATE
                    SET name = EXCLUDED.name,
                        intro = EXCLUDED.intro,
                        story = EXCLUDED.story,
                        collection_type_id = EXCLUDED.collection_type_id,
                        collection_id = NULL,
                        user_id = EXCLUDED.user_id,
                        country_id = EXCLUDED.country_id,
                        region_id = EXCLUDED.region_id,
                        locality_id = EXCLUDED.locality_id,
                        location = EXCLUDED.location,
                        seo = EXCLUDED.seo,
                        event_details = EXCLUDED.event_details,
                        website = EXCLUDED.website,
                        signature = EXCLUDED.signature,
                        is_featured = EXCLUDED.is_featured,
                        priority = EXCLUDED.priority,
                        cover_media_id = EXCLUDED.cover_media_id,
                        status = EXCLUDED.status,
                        published_at = EXCLUDED.published_at
                    RETURNING id
                    """,
                    (name,
                     (a.get("intro") or "").strip() or None,
                     slug,
                     (a.get("story") or "").strip() or None,
                     ct_id,
                     owner_id,
                     country_id, region_id, locality_id,
                     Json(location) if location else None,
                     Json(seo) if seo else None,
                     Json(event_details) if event_details else None,
                     website, signature,
                     bool(a.get("isFeatured")), a.get("priority") or 0,
                     cover_id, status,
                     a.get("createdAt") if status == "live" else None),
                )
                album_to_postcard[al["id"]] = cur.fetchone()[0]
                continue

            # -------------------------------------------------------------
            # dedicated collection type -> collection (Properties)
            # -------------------------------------------------------------
            slug = coll_slugs.take((a.get("slug") or "").strip() or slugify(name))

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

            cur.execute(
                """
                INSERT INTO collections
                    (collection_type_id, name, intro, story, slug, cover_media_id, seo,
                     gallery, is_featured, priority, country_id, region_id, locality_id,
                     location, managed_by_company_id, owner_user_id, assigned_to_user_id,
                     website, signature, about, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s)
                ON CONFLICT (slug) DO UPDATE
                SET collection_type_id = EXCLUDED.collection_type_id,
                    name = EXCLUDED.name,
                    intro = EXCLUDED.intro,
                    story = EXCLUDED.story,
                    cover_media_id = EXCLUDED.cover_media_id,
                    seo = EXCLUDED.seo,
                    gallery = EXCLUDED.gallery,
                    is_featured = EXCLUDED.is_featured,
                    priority = EXCLUDED.priority,
                    country_id = EXCLUDED.country_id,
                    region_id = EXCLUDED.region_id,
                    locality_id = EXCLUDED.locality_id,
                    location = EXCLUDED.location,
                    managed_by_company_id = EXCLUDED.managed_by_company_id,
                    owner_user_id = EXCLUDED.owner_user_id,
                    assigned_to_user_id = EXCLUDED.assigned_to_user_id,
                    website = EXCLUDED.website,
                    signature = EXCLUDED.signature,
                    about = EXCLUDED.about,
                    status = EXCLUDED.status
                RETURNING id
                """,
                (ct_id, name,
                 (a.get("intro") or "").strip() or None,
                 (a.get("story") or "").strip() or None,
                 slug, cover_id,
                 Json(seo) if seo else None,
                 Json(gallery) if gallery else None,
                 bool(a.get("isFeatured")), a.get("priority") or 0,
                 country_id, region_id, locality_id,
                 Json(location) if location else None,
                 company_id, owner_id, assigned_id,
                 website, signature,
                 (a.get("sustainability") or "").strip() or None,
                 status),
            )
            album_to_collection[al["id"]] = cur.fetchone()[0]

    conn.commit()
    print(f"collections upserted (dedicated types): {len(album_to_collection)}")
    print(f"postcards upserted (non-dedicated types): {len(album_to_postcard)}")
    print(f"status distribution: {dict(status_counts)}")
    print(f"skipped Designer Tours albums ({len(skipped_designer_tours)})")  # expect 59
    print(f"skipped (no name): {skipped_no_name}")
    print(f"media rows created by this step: {media.created}")
    print(f"no directory -> defaulted to Properties ({len(no_directory)})")
    print(f"MANUAL REVIEW multi-directory albums, lowest id wins ({len(multi_directory)}): {multi_directory[:20]}")
    print(f"MANUAL REVIEW country not found ({len(missing_country)}): {missing_country[:20]}")
    print(f"MANUAL REVIEW region not found ({len(missing_region)}): {missing_region[:20]}")
    print(f"MANUAL REVIEW locality missing/ambiguous ({len(ambiguous_locality)}): {ambiguous_locality[:20]}")
    print(f"MANUAL REVIEW company unmatched ({len(unmatched_company)}): {unmatched_company[:20]}")
    print(f"MANUAL REVIEW legacy user/assignTo not in user map ({len(unmapped_owner)}): {sorted(unmapped_owner)[:20]}")
    print(f"MANUAL REVIEW album fields with no postcards column, dropped "
          f"({len(dropped_on_postcard)}): {dropped_on_postcard[:20]}")
    return album_to_collection, album_to_postcard


def drop_stale_nondedicated_collections(conn):
    """Delete `collections` rows for non-dedicated types (left by earlier runs).

    Aborts instead of cascading if anything still points at them, so a partly
    migrated DB is never silently gutted.
    """
    with conn.cursor() as cur:
        cur.execute("""
            SELECT c.id FROM collections c
            JOIN collection_types ct ON ct.id = c.collection_type_id
            WHERE ct.has_dedicated_collection = false
        """)
        stale = [r[0] for r in cur.fetchall()]
        if not stale:
            print("stale non-dedicated collections: 0")
            return

        # (label, count query, ready-to-paste remediation SQL)
        DEPENDENTS = [
            ("postcards",
             "SELECT COUNT(*) FROM postcards WHERE collection_id = ANY(%s)",
             "-- postcards of a non-dedicated type must not carry a collection\n"
             "UPDATE postcards p SET collection_id = NULL\n"
             "  FROM collections c JOIN collection_types ct ON ct.id = c.collection_type_id\n"
             " WHERE p.collection_id = c.id AND ct.has_dedicated_collection = false;"),
            ("subcollections",
             "SELECT COUNT(*) FROM subcollections WHERE collection_id = ANY(%s)",
             "-- a Journey needs a real Collection parent: review these by hand\n"
             "SELECT s.id, s.name FROM subcollections s\n"
             "  JOIN collections c ON c.id = s.collection_id\n"
             "  JOIN collection_types ct ON ct.id = c.collection_type_id\n"
             " WHERE ct.has_dedicated_collection = false;"),
            ("memories",
             "SELECT COUNT(*) FROM memories WHERE collection_id = ANY(%s)",
             "-- re-point the memory at the album-derived postcard, or detach\n"
             "UPDATE memories m SET collection_id = NULL\n"
             "  FROM collections c JOIN collection_types ct ON ct.id = c.collection_type_id\n"
             " WHERE m.collection_id = c.id AND ct.has_dedicated_collection = false;"),
            ("facet_assignments",
             "SELECT COUNT(*) FROM facet_assignments WHERE owned_type = 'collection' AND owned_id = ANY(%s)",
             "-- facet assignments are re-created by the facet migrations\n"
             "DELETE FROM facet_assignments fa USING collections c, collection_types ct\n"
             " WHERE fa.owned_type = 'collection' AND fa.owned_id = c.id\n"
             "   AND ct.id = c.collection_type_id AND ct.has_dedicated_collection = false;"),
            ("circles",
             "SELECT COUNT(*) FROM circles WHERE owned_type = 'collection' AND owned_id = ANY(%s)",
             "-- follow-album circles: re-point at the album-derived postcard by hand,\n"
             "-- or delete and re-run scripts/follows.py\n"
             "DELETE FROM circles ci USING collections c, collection_types ct\n"
             " WHERE ci.owned_type = 'collection' AND ci.owned_id = c.id\n"
             "   AND ct.id = c.collection_type_id AND ct.has_dedicated_collection = false;"),
        ]

        blockers = []
        for label, q, fix in DEPENDENTS:
            cur.execute(q, (stale,))
            n = cur.fetchone()[0]
            if n:
                blockers.append((label, n, fix))

        if blockers:
            conn.rollback()
            summary = ", ".join(f"{label} ({n})" for label, n, _ in blockers)
            fixes = "\n\n".join(fix for *_, fix in blockers)
            raise SystemExit(
                f"\nABORT: {len(stale)} stale non-dedicated collections are still referenced by "
                f"{summary}.\nThey are left over from an older run where Restaurants/Events/"
                f"Shopping albums became collections.\nEither run scripts/truncate_all.py for a "
                f"clean re-migration, or detach the referencing rows and re-run this script:\n\n"
                f"{fixes}\n"
            )

        cur.execute("DELETE FROM collections WHERE id = ANY(%s)", (stale,))
        deleted = cur.rowcount
    conn.commit()
    print(f"deleted stale non-dedicated collections: {deleted}")


def verify(conn):
    with conn.cursor() as cur:
        print("collections per type (non-dedicated types must be 0):")
        cur.execute("""
            SELECT ct.name, ct.has_dedicated_collection, COUNT(c.id) FROM collection_types ct
            LEFT JOIN collections c ON c.collection_type_id = ct.id
            GROUP BY ct.id, ct.name, ct.has_dedicated_collection ORDER BY MIN(ct.priority)
        """)
        for name, ded, n in cur.fetchall():
            print(f"  {name:20} dedicated={str(ded):5}: {n}")
        print("album-derived postcards per type (collection_id IS NULL):")
        cur.execute("""
            SELECT ct.name, COUNT(p.id) FROM collection_types ct
            LEFT JOIN postcards p ON p.collection_type_id = ct.id AND p.collection_id IS NULL
            WHERE ct.has_dedicated_collection = false
            GROUP BY ct.id, ct.name ORDER BY MIN(ct.priority)
        """)
        for name, n in cur.fetchall():
            print(f"  {name:20}: {n}")
        for label, q in [
            ("collections total",  "SELECT COUNT(*) FROM collections"),
            ("with cover media",   "SELECT COUNT(*) FROM collections WHERE cover_media_id IS NOT NULL"),
            ("with country",       "SELECT COUNT(*) FROM collections WHERE country_id IS NOT NULL"),
            ("with region",        "SELECT COUNT(*) FROM collections WHERE region_id IS NOT NULL"),
            ("with locality",      "SELECT COUNT(*) FROM collections WHERE locality_id IS NOT NULL"),
            ("with company",       "SELECT COUNT(*) FROM collections WHERE managed_by_company_id IS NOT NULL"),
            ("with owner",         "SELECT COUNT(*) FROM collections WHERE owner_user_id IS NOT NULL"),
            ("with assignee",      "SELECT COUNT(*) FROM collections WHERE assigned_to_user_id IS NOT NULL"),
            ("with signature",     "SELECT COUNT(*) FROM collections WHERE signature IS NOT NULL"),
            ("with about",         "SELECT COUNT(*) FROM collections WHERE about IS NOT NULL"),
            ("status = live",      "SELECT COUNT(*) FROM collections WHERE status = 'live'"),
            ("dup slugs (want 0)", "SELECT COUNT(*) FROM (SELECT slug FROM collections GROUP BY slug HAVING COUNT(*) > 1) d"),
            ("postcards total",    "SELECT COUNT(*) FROM postcards"),
            ("pc w/ website",      "SELECT COUNT(*) FROM postcards WHERE website IS NOT NULL"),
            ("pc w/ signature",    "SELECT COUNT(*) FROM postcards WHERE signature IS NOT NULL"),
            ("pc w/ event_details", "SELECT COUNT(*) FROM postcards WHERE event_details IS NOT NULL"),
            ("pc w/ location",     "SELECT COUNT(*) FROM postcards WHERE location IS NOT NULL"),
            ("bad: nonded w/ coll", """
                SELECT COUNT(*) FROM postcards p JOIN collection_types ct ON ct.id = p.collection_type_id
                WHERE ct.has_dedicated_collection = false AND p.collection_id IS NOT NULL"""),
        ]:
            cur.execute(q)
            print(f"{label:22}: {cur.fetchone()[0]}")


def main():
    conn = connect()

    user_map = load_map("legacy_user_id_map")
    print(f"loaded {len(user_map)} user mappings (for owner/assignTo, R3)")

    dir_id_to_ct, default_ct_id, skipped_dir_ids, dedicated_ct_ids = migrate_directories(conn)

    albums = sorted(fetch_all("/api/albums", {"populate": "*"}), key=lambda x: x["id"])
    print(f"fetched {len(albums)} albums")

    album_to_collection, album_to_postcard = migrate_albums(
        conn, albums, dir_id_to_ct, default_ct_id, skipped_dir_ids, dedicated_ct_ids, user_map)

    save_map("legacy_album_id_map", album_to_collection, "album -> collection")
    save_map("legacy_album_postcard_id_map", album_to_postcard, "album -> postcard")

    drop_stale_nondedicated_collections(conn)
    verify(conn)
    conn.close()


if __name__ == "__main__":
    main()
