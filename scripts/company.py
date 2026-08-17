"""Company migration — legacy Strapi `companies` -> new `companies` table.

Migration step 4 of the run order (run AFTER media.py so logos reuse its rows).

Field mapping (verified against the live API — legacy Company exposes exactly
name / website / icon):
  name    -> title            (tracker rename, confirmed intentional)
  icon    -> logo_media_id    (tracker calls the v2 field 'logo')
  website -> website
  (none)  -> cover_image_media_id  — the tracker confirms a cover image distinct
             from the logo, but legacy Company has no such field, so it stays
             NULL until the CMS starts collecting one.

slug is generated here (unique, de-duplicated within the run) and status is set
to 'active' since these are existing live companies — the schema default
'pending' is for new self-signups. contact_email / contact_phone stay NULL —
nothing to map.

Companies are processed sorted by legacy id so generated slug suffixes
(acme-2) stay stable across re-runs.

Writes `legacy_company_id_map{_dev,_prod}.json` — required by the
follow-company pass in scripts/follows.py.

Idempotent — upsert on slug. Safe to re-run.

Usage:
    python scripts/company.py
"""

from _common import (MediaResolver, attrs, connect, fetch_all, rel, save_map,
                     slugify, SlugAllocator)


def main():
    conn = connect()

    companies = sorted(fetch_all("/api/companies", {"populate": "icon"}),
                       key=lambda c: c["id"])
    print(f"fetched {len(companies)} companies")

    media = MediaResolver(conn)
    slugs = SlugAllocator(fallback="company")
    company_map = {}
    skipped = []

    with conn.cursor() as cur:
        for c in companies:
            a = attrs(c)
            name = (a.get("name") or "").strip()
            if not name:
                skipped.append(c["id"])
                continue

            slug = slugs.take(slugify(name))
            logo_id = media.resolve(cur, rel(a.get("icon")))

            cur.execute(
                """
                INSERT INTO companies (title, slug, website, logo_media_id, status)
                VALUES (%s, %s, %s, %s, 'active')
                ON CONFLICT (slug) DO UPDATE
                SET title         = EXCLUDED.title,
                    website       = EXCLUDED.website,
                    logo_media_id = EXCLUDED.logo_media_id
                RETURNING id
                """,
                (name, slug, (a.get("website") or "").strip() or None, logo_id),
            )
            company_map[c["id"]] = cur.fetchone()[0]

    conn.commit()
    print(f"upserted companies: {len(company_map)}; skipped (no name): {skipped}")
    print(f"media rows created by this step: {media.created}")

    save_map("legacy_company_id_map", company_map, "company -> company")

    with conn.cursor() as cur:
        for label, q in [
            ("companies total", "SELECT COUNT(*) FROM companies"),
            ("with logo",       "SELECT COUNT(*) FROM companies WHERE logo_media_id IS NOT NULL"),
            ("with website",    "SELECT COUNT(*) FROM companies WHERE website IS NOT NULL"),
            ("dup slugs (want 0)",
             "SELECT COUNT(*) FROM (SELECT slug FROM companies GROUP BY slug HAVING COUNT(*) > 1) d"),
        ]:
            cur.execute(q)
            print(f"{label:20}: {cur.fetchone()[0]}")
    conn.close()


if __name__ == "__main__":
    main()
