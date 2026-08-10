"""Users migration — legacy user types, users and roles (incl. media/company attach).

Migration 5 of the run order (after media.py and company.py).

Legacy users must be fetched from TWO endpoints and merged by id:
  - /api/users -- custom controller: profile fields + populated relations
    (user_type, country, company, profilePic, coverImage), but it STRIPS
    email/username/provider/fbId/confirmed/blocked/isLoyaltyMember/
    isFeatured/tracking and ignores start/limit (returns everything at once)
  - admin content-manager API -- raw records incl. all the stripped fields;
    needs CMS_ADMIN_EMAIL / CMS_ADMIN_PASSWORD (super-admin) in .env

Steps:
  1. user_types      /api/user-types -> user_types, upsert by slug
  2. users           merged payload -> users, upsert by email;
                     profilePic/coverImage/profilePicURL resolve to media
                     rows by url (same normalization as media.py, so rows
                     are reused, never duplicated); legacy slug kept (unique)
  3. user_roles      legacy user_type -> role (default type when absent);
                     legacy company (N:1) -> user_roles.company_id, matched
                     against companies.name (how company.py keys its rows)
  4. legacy_user_id_map_dev.json / _prod.json  legacy id -> new id, for the
                     circles/content migrations that reference users by
                     legacy id (suffix from the DB name in DATABASE_URL)

password_hash stays NULL — no API exposes it; recover via a legacy DB dump
or force password resets. Free-text city cannot be auto-resolved — printed
as a manual-review list. Idempotent — safe to re-run.

Usage:
    python scripts/users.py
"""

import json
import os
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


def attrs(item):
    """Entry fields — Strapi v4 nests them under 'attributes', v5 is flat."""
    return item.get("attributes", item)


def fetch_all(path, params=None):
    """Fetch every page of a standard Strapi collection endpoint."""
    items, page = [], 1
    while True:
        p = {"pagination[page]": page, "pagination[pageSize]": 100, **(params or {})}
        r = requests.get(f"{CMS_BASE_URL}{path}", headers=HEADERS, params=p, timeout=60)
        r.raise_for_status()
        body = r.json()
        data = body["data"] if isinstance(body, dict) else body
        items.extend(data)
        pg = body.get("meta", {}).get("pagination", {}) if isinstance(body, dict) else {}
        if page >= pg.get("pageCount", 1):
            return items
        page += 1


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
    r = requests.post(
        f"{CMS_BASE_URL}/admin/login",
        json={"email": email, "password": password},
        timeout=60,
    )
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


def media_id_for(cur, media_obj=None, url=None):
    """Resolve a media row by url — same normalization + select-then-insert as
    media.py, so rows migrated there are reused, never duplicated."""
    if media_obj:
        url = media_obj.get("url") or url
    url = (url or "").strip()
    if not url:
        return None
    if url.startswith("/"):
        url = CMS_BASE_URL + url
    cur.execute("SELECT id FROM media WHERE url = %s", (url,))
    row = cur.fetchone()
    if row:
        return row[0]
    m = media_obj or {}
    alt = m.get("alternativeText") or m.get("caption") or m.get("name") or None
    cur.execute(
        "INSERT INTO media (url, mime_type, alt, width, height) VALUES (%s, %s, %s, %s, %s) RETURNING id",
        (url, m.get("mime"), alt, m.get("width"), m.get("height")),
    )
    return cur.fetchone()[0]


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
            name = (a.get("name") or "").strip()
            slug = (a.get("slug") or "").strip()
            if not name or not slug:
                skipped.append(t["id"])
                continue
            cur.execute(
                """
                INSERT INTO user_types (name, slug, is_default, is_creator, is_admin)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (slug) DO UPDATE
                SET name = EXCLUDED.name,
                    is_default = EXCLUDED.is_default,
                    is_creator = EXCLUDED.is_creator,
                    is_admin = EXCLUDED.is_admin
                """,
                (name, slug, bool(a.get("isDefault")), bool(a.get("isCreator")), bool(a.get("isAdmin"))),
            )
    conn.commit()
    if skipped:
        print(f"user_types skipped (no name/slug): {skipped}")


def migrate_users(conn, legacy_users):
    skipped, city_review = [], []
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
            profile_pic_id = media_id_for(cur, u.get("profilePic"), u.get("profilePicURL"))
            cover_image_id = media_id_for(cur, u.get("coverImage"))

            country = u.get("country") or {}
            country_name = (country.get("name") or "").strip() or None

            cur.execute(
                """
                INSERT INTO users (username, email, slug, first_name, last_name,
                                   auth_provider, provider_id, email_verified, is_blocked,
                                   profile_pic_id, cover_image_id, bio, social, seo, tracking,
                                   is_featured, priority, tier,
                                   country_id)
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
                    tier           = EXCLUDED.tier,
                    country_id     = EXCLUDED.country_id
                """,
                (
                    username, email, slug, first, last,
                    u.get("provider"), u.get("fbId"), bool(u.get("confirmed")), bool(u.get("blocked")),
                    profile_pic_id, cover_image_id, u.get("bio"),
                    Json(u["social"]) if u.get("social") else None,
                    Json(u["seo"]) if u.get("seo") else None,
                    Json(u["tracking"]) if u.get("tracking") else None,
                    bool(u.get("isFeatured")), u.get("priority") or 0,
                    "star_life" if u.get("isLoyaltyMember") else "free",
                    country_name,
                ),
            )

            if u.get("city"):
                city_review.append((email, u["city"]))

    conn.commit()
    print(f"upserted users; skipped (no email/username): {len(skipped)}")
    for row in skipped:
        print("  skipped:", row)
    print(f"MANUAL REVIEW — free-text city to resolve to city_id ({len(city_review)}):")
    for row in city_review:
        print("  city:", row)
    return skipped


def migrate_user_roles(conn, legacy_users):
    with conn.cursor() as cur:
        cur.execute("SELECT slug, id FROM user_types")
        type_by_slug = dict(cur.fetchall())
        cur.execute("SELECT id FROM user_types WHERE is_default LIMIT 1")
        default_row = cur.fetchone()
        # companies are keyed by slugified name in company.py — match on trimmed name
        cur.execute("SELECT TRIM(name), id FROM companies ORDER BY id DESC")
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
                SELECT us.id, %s, %s, 'active' FROM users us
                WHERE us.email = %s
                  AND NOT EXISTS (
                        SELECT 1 FROM user_roles ur
                        WHERE ur.user_id = us.id AND ur.user_type_id = %s)
                """,
                (type_id, company_id, email, type_id),
            )
            if company_id:  # fill company on roles created by an earlier run
                cur.execute(
                    """
                    UPDATE user_roles ur SET company_id = %s
                    FROM users us
                    WHERE us.id = ur.user_id AND us.email = %s
                      AND ur.user_type_id = %s AND ur.company_id IS NULL
                    """,
                    (company_id, email, type_id),
                )
    conn.commit()
    print(f"roles assigned; unmatched legacy type slugs (fell back to default): {unmatched_types or 'none'}")
    print(f"legacy companies not found in companies table: {unmatched_companies or 'none'}")


def dump_legacy_id_map(conn, legacy_users):
    """Legacy Strapi user id -> new users.id, for migrations that reference
    users by legacy id (circles, memories, content)."""
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
    out = ROOT / f"legacy_user_id_map{ENV_SUFFIX}.json"
    out.write_text(json.dumps({str(k): str(v) for k, v in id_map.items()}, indent=2))
    print(f"saved {len(id_map)} legacy->new user id mappings to {out}")


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
        cur.execute("SELECT COUNT(*) FROM user_roles WHERE company_id IS NOT NULL")
        print("roles linked to a company:", cur.fetchone()[0])
        cur.execute("SELECT COUNT(*) FROM users WHERE profile_pic_id IS NOT NULL")
        print("users with profile pic   :", cur.fetchone()[0])
        cur.execute("SELECT COUNT(*) FROM users WHERE cover_image_id IS NOT NULL")
        print("users with cover image   :", cur.fetchone()[0])
        cur.execute("SELECT COUNT(*) FROM users WHERE password_hash IS NULL")
        print("users without password_hash (expected — see docstring):", cur.fetchone()[0])


def main():
    conn = psycopg.connect(DATABASE_URL)
    print("connected to:", DATABASE_URL.rsplit("/", 1)[-1])

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
    migrate_user_roles(conn, legacy_users)
    dump_legacy_id_map(conn, legacy_users)
    verify(conn)
    conn.close()


if __name__ == "__main__":
    main()
