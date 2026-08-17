"""Users migration — legacy user types, users, roles and memberships.

Migration step 5 of the run order (after media.py and company.py).

Legacy users must be fetched from TWO endpoints and merged by id:
  - /api/users -- custom controller: profile fields + populated relations
    (user_type, country, company, profilePic, coverImage), but it STRIPS
    email/username/provider/fbId/confirmed/blocked/isLoyaltyMember/
    isFeatured/tracking and ignores start/limit (returns everything at once)
  - admin content-manager API -- raw records incl. all the stripped fields;
    needs CMS_ADMIN_EMAIL / CMS_ADMIN_PASSWORD (super-admin) in .env

Steps:
  1. user_types   /api/user-types -> user_types, upsert by slug.
                  `name` -> `title` (tracker rename). is_default / is_creator /
                  is_admin are KEPT: they exist and are populated in v1
                  ('Regular' is the default type), the canonical doc keeps them,
                  and is_default is what assigns the fallback role below.
  2. users        merged payload -> users, upsert by email; profilePic /
                  coverImage / profilePicURL resolve to media rows; legacy slug
                  kept (unique); legacy free-text `city` -> users.city_name
                  (informational only — City is no longer a geo tier, R1).
  3. memberships  R2: tier moved off User into its own table. Legacy
                  `isLoyaltyMember` is NULL on all 3371 users, so there is NO
                  v1 source for Free/StarLife — every migrated user gets one
                  `free` / `active` membership, matching the behaviour the old
                  `users.tier` default had. Upgrade StarLife members by hand or
                  from a later source. See SEED_FREE_MEMBERSHIP below.
  4. user_roles   legacy user_type -> role (default type when absent);
                  legacy company (N:1) -> user_roles.company_id
  5. legacy_user_id_map{_dev,_prod}.json  legacy id -> new id, consumed by the
                  content, circle and follow migrations.

password_hash stays NULL — no API exposes it, and the tracker forbids carrying
the shared hardcoded social-login hash forward. Recover via a reset flow.

Idempotent — safe to re-run.

Usage:
    python scripts/users.py
"""

import os

import requests
from psycopg.types.json import Json

from _common import (CMS_BASE_URL, HEADERS, MediaResolver, attrs, connect,
                     fetch_all, save_map)

# No v1 source for Free/StarLife exists (isLoyaltyMember is NULL everywhere).
# True  -> give every user a free/active membership row so the app always has
#          a current-tier row to read.
# False -> migrate no memberships at all and let the app treat "no row" as free.
SEED_FREE_MEMBERSHIP = True


def fetch_public_users():
    """Custom controller: ignores start/limit, returns ALL users in one response."""
    r = requests.get(f"{CMS_BASE_URL}/api/users", headers=HEADERS, timeout=300)
    r.raise_for_status()
    users = r.json()
    if not isinstance(users, list):
        raise SystemExit(f"unexpected /api/users body: {type(users)}")
    return users


def fetch_admin_users():
    """Raw user records (incl. email) via the admin content-manager API."""
    email = os.environ.get("CMS_ADMIN_EMAIL")
    password = os.environ.get("CMS_ADMIN_PASSWORD")
    if not email or not password:
        raise SystemExit(
            "CMS_ADMIN_EMAIL / CMS_ADMIN_PASSWORD missing from .env — required "
            "because the public /api/users controller strips email and auth fields."
        )
    r = requests.post(f"{CMS_BASE_URL}/admin/login",
                      json={"email": email, "password": password}, timeout=60)
    r.raise_for_status()
    admin_headers = {"Authorization": f"Bearer {r.json()['data']['token']}"}

    out, page = [], 1
    while True:
        r = requests.get(
            f"{CMS_BASE_URL}/content-manager/collection-types/plugin::users-permissions.user",
            headers=admin_headers,
            params={"page": page, "pageSize": 100, "sort": "id:ASC"},
            timeout=60,
        )
        r.raise_for_status()
        body = r.json()
        out.extend(body["results"])
        if page >= body["pagination"]["pageCount"]:
            return out
        page += 1


def split_name(u):
    first, last = u.get("firstName"), u.get("lastName")
    if not first and u.get("fullName"):
        parts = u["fullName"].strip().split(" ", 1)
        first = parts[0]
        last = last or (parts[1] if len(parts) > 1 else None)
    return first, last


def migrate_user_types(conn):
    user_types = fetch_all("/api/user-types")
    print(f"fetched {len(user_types)} user types")

    skipped = []
    with conn.cursor() as cur:
        for t in user_types:
            a = attrs(t)
            title = (a.get("name") or "").strip()
            slug = (a.get("slug") or "").strip()
            if not title or not slug:
                skipped.append(t["id"])
                continue
            cur.execute(
                """
                INSERT INTO user_types (title, slug, is_default, is_creator, is_admin)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (slug) DO UPDATE
                SET title      = EXCLUDED.title,
                    is_default = EXCLUDED.is_default,
                    is_creator = EXCLUDED.is_creator,
                    is_admin   = EXCLUDED.is_admin
                """,
                (title, slug, bool(a.get("isDefault")), bool(a.get("isCreator")),
                 bool(a.get("isAdmin"))),
            )
    conn.commit()
    if skipped:
        print(f"user_types skipped (no name/slug): {skipped}")


def migrate_users(conn, legacy_users):
    media = MediaResolver(conn)
    skipped, with_city = [], 0

    with conn.cursor() as cur:
        for u in legacy_users:
            email = (u.get("email") or "").strip().lower()
            username = (u.get("username") or "").strip() or (email.split("@")[0] if email else None)
            if not email or not username:
                skipped.append((u["id"], u.get("username"), u.get("email")))
                continue

            # username/slug are unique — if another account holds one, disambiguate
            cur.execute("SELECT 1 FROM users WHERE username = %s AND email <> %s", (username, email))
            if cur.fetchone():
                username = f"{username}-{u['id']}"
            slug = (u.get("slug") or "").strip() or None
            if slug:
                cur.execute("SELECT 1 FROM users WHERE slug = %s AND email <> %s", (slug, email))
                if cur.fetchone():
                    slug = f"{slug}-{u['id']}"

            first, last = split_name(u)
            profile_pic_id = media.resolve(cur, u.get("profilePic"), u.get("profilePicURL"))
            cover_image_id = media.resolve(cur, u.get("coverImage"))

            country_name = ((u.get("country") or {}).get("name") or "").strip() or None
            # R1: legacy free-text city is informational display text, not a tier
            city_name = (u.get("city") or "").strip() or None
            with_city += bool(city_name)

            cur.execute(
                """
                INSERT INTO users (username, email, slug, first_name, last_name,
                                   auth_provider, provider_id, email_verified, is_blocked,
                                   profile_pic_id, cover_image_id, bio, social, seo, tracking,
                                   is_featured, priority, city_name, country_id)
                VALUES (%s, %s, %s, %s, %s,
                        %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s,
                        %s, %s, %s,
                        (SELECT id FROM countries WHERE name = %s))
                ON CONFLICT (email) DO UPDATE
                SET username       = EXCLUDED.username,
                    slug           = EXCLUDED.slug,
                    first_name     = EXCLUDED.first_name,
                    last_name      = EXCLUDED.last_name,
                    auth_provider  = EXCLUDED.auth_provider,
                    provider_id    = EXCLUDED.provider_id,
                    email_verified = EXCLUDED.email_verified,
                    is_blocked     = EXCLUDED.is_blocked,
                    profile_pic_id = EXCLUDED.profile_pic_id,
                    cover_image_id = EXCLUDED.cover_image_id,
                    bio            = EXCLUDED.bio,
                    social         = EXCLUDED.social,
                    seo            = EXCLUDED.seo,
                    tracking       = EXCLUDED.tracking,
                    is_featured    = EXCLUDED.is_featured,
                    priority       = EXCLUDED.priority,
                    city_name      = EXCLUDED.city_name,
                    country_id     = EXCLUDED.country_id
                """,
                (
                    username, email, slug, first, last,
                    u.get("provider"), u.get("fbId"),
                    bool(u.get("confirmed")), bool(u.get("blocked")),
                    profile_pic_id, cover_image_id, u.get("bio"),
                    Json(u["social"]) if u.get("social") else None,
                    Json(u["seo"]) if u.get("seo") else None,
                    Json(u["tracking"]) if u.get("tracking") else None,
                    bool(u.get("isFeatured")), u.get("priority") or 0,
                    city_name, country_name,
                ),
            )

    conn.commit()
    print(f"upserted users; skipped (no email/username): {len(skipped)}")
    for row in skipped[:20]:
        print("  skipped:", row)
    print(f"legacy free-text city carried to users.city_name: {with_city}")
    print(f"media rows created by this step: {media.created}")


def migrate_memberships(conn, legacy_users):
    """R2 — tier lives in its own table now.

    isLoyaltyMember is NULL for every legacy user, so nothing distinguishes a
    StarLife member in v1. Every user gets a `free` / `active` membership,
    which is exactly what the old users.tier default produced.
    """
    if not SEED_FREE_MEMBERSHIP:
        print("SEED_FREE_MEMBERSHIP = False — no membership rows written")
        return

    loyalty = sum(1 for u in legacy_users if u.get("isLoyaltyMember"))
    created = 0
    with conn.cursor() as cur:
        for u in legacy_users:
            email = (u.get("email") or "").strip().lower()
            if not email:
                continue
            tier = "star_life" if u.get("isLoyaltyMember") else "free"
            cur.execute(
                """
                INSERT INTO memberships (user_id, tier, status)
                SELECT us.id, %s, 'active' FROM users us
                WHERE us.email = %s
                  AND NOT EXISTS (SELECT 1 FROM memberships m WHERE m.user_id = us.id)
                """,
                (tier, email),
            )
            created += cur.rowcount
    conn.commit()
    print(f"memberships created: {created} (legacy isLoyaltyMember set on {loyalty} users)")
    if not loyalty:
        print("  NOTE: no legacy StarLife source — every membership is 'free'. "
              "Upgrade tiers manually or from a later source.")


def migrate_user_roles(conn, legacy_users):
    with conn.cursor() as cur:
        cur.execute("SELECT slug, id FROM user_types")
        type_by_slug = dict(cur.fetchall())
        cur.execute("SELECT id FROM user_types WHERE is_default LIMIT 1")
        default_row = cur.fetchone()
        # companies are keyed by slugified title in company.py — match on trimmed title
        cur.execute("SELECT TRIM(title), id FROM companies ORDER BY id DESC")
        company_by_name = dict(cur.fetchall())  # DESC + dict -> smallest id wins on dupes

    if not type_by_slug:
        raise SystemExit("user_types is empty — the user-types step must have failed")
    if not default_row:
        raise SystemExit("user_types has no is_default row — check legacy /api/user-types")
    default_type_id = default_row[0]

    unmatched_types, unmatched_companies = set(), set()
    with conn.cursor() as cur:
        for u in legacy_users:
            email = (u.get("email") or "").strip().lower()
            if not email:
                continue

            ut = u.get("user_type") or {}
            type_slug = (ut.get("slug") or "").strip().lower()
            type_id = type_by_slug.get(type_slug) if type_slug else default_type_id
            if type_id is None:
                unmatched_types.add(type_slug)
                type_id = default_type_id

            company_id = None
            company_name = ((u.get("company") or {}).get("name") or "").strip()
            if company_name:
                company_id = company_by_name.get(company_name)
                if company_id is None:
                    unmatched_companies.add(company_name)

            cur.execute(
                """
                INSERT INTO user_roles (user_id, user_type_id, company_id, status)
                SELECT us.id, %s, %s, 'active' FROM users us WHERE us.email = %s
                ON CONFLICT (user_id, user_type_id) DO UPDATE
                SET company_id = COALESCE(EXCLUDED.company_id, user_roles.company_id)
                """,
                (type_id, company_id, email),
            )
    conn.commit()
    print(f"roles assigned; unmatched legacy type slugs (fell back to default): {unmatched_types or 'none'}")
    print(f"legacy companies not found in companies table: {unmatched_companies or 'none'}")


def dump_legacy_id_map(conn, legacy_users):
    id_map = {}
    with conn.cursor() as cur:
        for u in legacy_users:
            email = (u.get("email") or "").strip().lower()
            if not email:
                continue
            cur.execute("SELECT id FROM users WHERE email = %s", (email,))
            row = cur.fetchone()
            if row:
                id_map[u["id"]] = row[0]
    save_map("legacy_user_id_map", id_map, "user -> user")


def verify(conn):
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM users")
        print("users     :", cur.fetchone()[0])
        cur.execute(
            """SELECT ut.slug, COUNT(*) FROM user_roles ur
               JOIN user_types ut ON ut.id = ur.user_type_id
               GROUP BY ut.slug ORDER BY 2 DESC"""
        )
        for slug, n in cur.fetchall():
            print(f"role {slug:15}: {n}")
        for label, q in [
            ("roles linked to a company", "SELECT COUNT(*) FROM user_roles WHERE company_id IS NOT NULL"),
            ("users with profile pic",    "SELECT COUNT(*) FROM users WHERE profile_pic_id IS NOT NULL"),
            ("users with cover image",    "SELECT COUNT(*) FROM users WHERE cover_image_id IS NOT NULL"),
            ("users with city_name",      "SELECT COUNT(*) FROM users WHERE city_name IS NOT NULL"),
            ("memberships",               "SELECT COUNT(*) FROM memberships"),
            ("  free",                    "SELECT COUNT(*) FROM memberships WHERE tier = 'free'"),
            ("  star_life",               "SELECT COUNT(*) FROM memberships WHERE tier = 'star_life'"),
            ("users w/o password_hash (expected)",
             "SELECT COUNT(*) FROM users WHERE password_hash IS NULL"),
        ]:
            cur.execute(q)
            print(f"{label:36}: {cur.fetchone()[0]}")


def main():
    conn = connect()

    migrate_user_types(conn)

    public_users = fetch_public_users()
    admin_by_id = {u["id"]: u for u in fetch_admin_users()}
    # merge by id — admin record supplies auth/scalar fields, public payload
    # wins for its populated relations (user_type, country, company, media)
    legacy_users = [{**admin_by_id.get(u["id"], {}), **u} for u in public_users]
    missing_auth = [u["id"] for u in legacy_users if not u.get("email")]
    print(f"fetched {len(legacy_users)} users ({len(admin_by_id)} admin records; "
          f"{len(missing_auth)} without email)")

    migrate_users(conn, legacy_users)
    migrate_memberships(conn, legacy_users)
    migrate_user_roles(conn, legacy_users)
    dump_legacy_id_map(conn, legacy_users)
    verify(conn)
    conn.close()


if __name__ == "__main__":
    main()
