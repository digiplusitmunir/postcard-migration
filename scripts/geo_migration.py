"""Geo migration — legacy Strapi countries/regions/localities -> new geo tables.

Migration step 2 of the run order (after seed.py). Nothing else can run before
this: every content migration resolves geo by name.

TRACKER REVISION R1 (2026-08-05) — the City tier is REMOVED. The hierarchy is
    Country -> Region -> Locality
and Locality parents DIRECTLY to Region. The previous version of this script
synthesized one placeholder city per region purely so localities had a parent;
that scaffolding is gone, and so is the `cities` table.

Field mapping (verified against the live API):
  Country  name / slug          -> name / slug
           code                 -> code            (ISO 3166-1 alpha-2, 215/265 set)
           continent            -> continent enum  (AF/AN/AS/EU/NA/OC/SA -> readable)
           coverImage           -> flag_media_id   (132/265 set)
           otherNames           -> NOT MIGRATED    (empty on every row)
  Region   name                 -> name; slug derived (legacy has no slug)
           country              -> country_id
           lat / lng            -> no legacy source; centroid comes from the
                                   Gmap enrichment workstream
  Locality name                 -> name; slug derived
           region               -> region_id       (direct, no city hop)
           google_place_id      -> no legacy source; the intended long-term
                                   uniqueness key, filled by Gmap enrichment.
                                   (name, region_id) is the load-time key.

Countries carry a flag image, so this step needs `media` rows. It resolves them
through the shared MediaResolver (find-or-create by legacy id, then url), which
means geo can still run before media.py without creating duplicates — media.py
will simply update the rows it already finds.

Idempotent — upserts on natural keys. Safe to re-run.

Usage:
    python scripts/geo_migration.py
"""

from collections import Counter

from _common import (MediaResolver, attrs, connect, fetch_all, rel, slugify)

# legacy two-letter continent code -> Continent enum value
CONTINENTS = {
    "AF": "africa",
    "AN": "antarctica",
    "AS": "asia",
    "EU": "europe",
    "NA": "north_america",
    "OC": "oceania",
    "SA": "south_america",
}


def migrate_countries(conn):
    countries = sorted(fetch_all("/api/countries", {"populate": "coverImage"}),
                       key=lambda c: c["id"])
    print(f"fetched {len(countries)} countries")

    media = MediaResolver(conn)
    skipped, unknown_continent = [], set()
    used_slugs = set()
    with_code = with_flag = 0

    with conn.cursor() as cur:
        for c in countries:
            a = attrs(c)
            name = (a.get("name") or "").strip()
            if not name:
                skipped.append(c["id"])
                continue

            base = (a.get("slug") or "").strip() or slugify(name) or "country"
            slug, n = base, 2
            while slug in used_slugs:      # two names can slugify the same
                slug, n = f"{base}-{n}", n + 1
            used_slugs.add(slug)

            raw_continent = (a.get("continent") or "").strip().upper() or None
            continent = CONTINENTS.get(raw_continent) if raw_continent else None
            if raw_continent and not continent:
                unknown_continent.add(raw_continent)

            code = (a.get("code") or "").strip() or None
            flag_id = media.resolve(cur, rel(a.get("coverImage")))
            with_code += bool(code)
            with_flag += bool(flag_id)

            cur.execute(
                """
                INSERT INTO countries (name, slug, code, continent, flag_media_id)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (name) DO UPDATE
                SET slug          = EXCLUDED.slug,
                    code          = EXCLUDED.code,
                    continent     = EXCLUDED.continent,
                    flag_media_id = EXCLUDED.flag_media_id
                """,
                (name, slug, code, continent, flag_id),
            )
    conn.commit()
    print(f"countries upserted; with code: {with_code}, with flag: {with_flag}")
    print(f"skipped (no name): {skipped}")
    print(f"MANUAL REVIEW unmapped continent codes: {unknown_continent or 'none'}")
    print(f"media rows created by this step: {media.created}")


def migrate_regions(conn):
    regions = sorted(fetch_all("/api/regions", {"populate": "country"}),
                     key=lambda r: r["id"])
    print(f"fetched {len(regions)} regions")

    orphans = []
    with conn.cursor() as cur:
        for r in regions:
            a = attrs(r)
            name = (a.get("name") or "").strip()
            country = rel(a.get("country"))
            if not name or not country:
                orphans.append((r["id"], name))
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
    print(f"regions upserted; MANUAL REVIEW (no name/country): {orphans}")


def migrate_localities(conn):
    """R1: localities parent straight to their region.

    The legacy region relation carries only a name, and region names are unique
    per COUNTRY, not globally — so a name-only match is ambiguous. Regions whose
    name occurs in more than one country are reported instead of guessed.
    """
    localities = sorted(fetch_all("/api/localities", {"populate": "region"}),
                        key=lambda l: l["id"])
    print(f"fetched {len(localities)} localities")

    with conn.cursor() as cur:
        cur.execute("SELECT LOWER(name), id FROM regions")
        region_ids_by_name = {}
        for lname, rid in cur.fetchall():
            region_ids_by_name.setdefault(lname, []).append(rid)

    orphans, unmatched, ambiguous = [], [], []
    with conn.cursor() as cur:
        for l in localities:
            a = attrs(l)
            name = (a.get("name") or "").strip()
            region = rel(a.get("region"))
            if not name or not region:
                orphans.append((l["id"], name))
                continue

            ids = region_ids_by_name.get((region.get("name") or "").strip().lower(), [])
            if not ids:
                unmatched.append((l["id"], name, region.get("name")))
                continue
            if len(ids) > 1:
                ambiguous.append((l["id"], name, region.get("name"), len(ids)))
                continue

            cur.execute(
                """
                INSERT INTO localities (region_id, name, slug)
                VALUES (%s, %s, %s)
                ON CONFLICT (name, region_id) DO UPDATE SET slug = EXCLUDED.slug
                """,
                (ids[0], name, slugify(name)),
            )
    conn.commit()
    print(f"localities upserted")
    print(f"MANUAL REVIEW no name/region ({len(orphans)}): {orphans}")
    print(f"MANUAL REVIEW region name matched nothing ({len(unmatched)}): {unmatched[:20]}")
    print(f"MANUAL REVIEW region name in >1 country — skipped ({len(ambiguous)}): {ambiguous[:20]}")


def verify(conn):
    with conn.cursor() as cur:
        for t in ("countries", "regions", "localities"):
            cur.execute(f"SELECT COUNT(*) FROM {t}")
            print(f"{t:12}: {cur.fetchone()[0]}")
        for label, q in [
            ("countries w/ code",      "SELECT COUNT(*) FROM countries WHERE code IS NOT NULL"),
            ("countries w/ continent", "SELECT COUNT(*) FROM countries WHERE continent IS NOT NULL"),
            ("countries w/ flag",      "SELECT COUNT(*) FROM countries WHERE flag_media_id IS NOT NULL"),
            ("orphan regions (want 0)",
             "SELECT COUNT(*) FROM regions r LEFT JOIN countries c ON c.id = r.country_id WHERE c.id IS NULL"),
            ("orphan localities (want 0)",
             "SELECT COUNT(*) FROM localities l LEFT JOIN regions r ON r.id = l.region_id WHERE r.id IS NULL"),
        ]:
            cur.execute(q)
            print(f"{label:28}: {cur.fetchone()[0]}")

        cur.execute("SELECT continent, COUNT(*) FROM countries GROUP BY continent ORDER BY 2 DESC")
        print("continents:", dict(cur.fetchall()))


def main():
    conn = connect()
    conn.rollback()  # clear any aborted transaction from a previous failed run
    migrate_countries(conn)
    migrate_regions(conn)
    migrate_localities(conn)
    verify(conn)
    conn.close()


if __name__ == "__main__":
    main()
