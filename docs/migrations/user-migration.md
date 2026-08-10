# User Migration

Everything about migrating legacy Strapi users (`plugin::users-permissions.user`,
table `up_users`) into the new `users` + `user_roles` tables. Executed by
`scripts/users.py` (step 5 of `scripts/migrate_data.py`); the same logic lives
in `notebooks/user_migration.ipynb` for interactive runs.

## The structural change

```text
LEGACY:  up_users ── user_type (1:1)  ── company (N:1) ── follows/bookmarks/...
NEW:     users ──< user_roles >── user_types      (one person, many roles)
                        └── company_id (per role)
         circles  ← replaces ALL follow/bookmark relations (separate migration)
```

Dependency direction: in the legacy schema the company FK lives **on the user**
(`company.users` is just the inverse view of `user.company`); in the new schema
the link lives on `user_roles.company_id`. Either way nothing on the company
side depends on users — so companies are migrated **before** users, and
`users.py` attaches roles to the already-migrated companies.

## Source endpoint quirk — why two fetches

The legacy `/api/users` controller is **customized**: it returns flat objects
with profile fields plus populated relations (`user_type`, `country`,
`company`, `profilePic`, `coverImage`) and computed extras, but it

- **strips** `email`, `username`, `provider`, `fbId`, `confirmed`, `blocked`,
  `isLoyaltyMember`, `isFeatured`, `tracking`, `isInstaActive`;
- **ignores** `start`/`limit` — the full set comes back in one response.

The stripped fields are therefore fetched through the **admin content-manager
API** (login via `CMS_ADMIN_EMAIL` / `CMS_ADMIN_PASSWORD` in `.env`, required)
and merged into the public record by legacy id.

⚠️ Related sanitization hole worth knowing until the legacy CMS is retired:
`/api/companies?populate=users` returns full user emails to any API-token
holder — the custom users controller does not protect relation-populated
user data.

## Field mapping — identity & auth

| Legacy field | Type | New column | Notes |
|---|---|---|---|
| `username` | string, required, unique | `username` (unique) | fallback: email prefix when blank; collision fallback `{username}-{legacy id}` |
| `email` | email, required | `email` (unique) | lowercased; upsert key — legacy duplicate accounts sharing an email collapse into one row |
| `password` | password (bcrypt), **private** | `password_hash` | ⚠️ **no API returns it** (not even admin) — stays NULL. Options: (a) copy hashes with a direct dump of the legacy DB (`up_users.password`, bcrypt-compatible), or (b) force password-reset emails on first login |
| `provider` | string | `auth_provider` | `local`, `facebook`, ... |
| `fbId` | string | `provider_id` | the external provider's user id |
| `confirmed` | boolean | `email_verified` | via admin API |
| `blocked` | boolean | `is_blocked` | via admin API |
| `resetPasswordToken`, `confirmationToken` | private strings | — | **dropped** — transient auth state |
| `role` (users-permissions role) | relation | — | **dropped** — plugin's permission system is replaced by user_types/user_roles |

## Field mapping — profile

| Legacy field | Type | New column | Notes |
|---|---|---|---|
| `firstName` / `lastName` | string | `first_name` / `last_name` | |
| `fullName` | string | — | used as fallback: split on first space when firstName is empty; the verbatim string is not stored (pending decision) |
| `slug` | uid (from fullName) | `slug` (unique, nullable) | collision fallback: `{slug}-{legacy id}`; schema migration `add_user_slug` |
| `bio` | richtext | `bio` | as-is |
| `profilePic` | media | `profile_pic_id` | resolved against `media` by url — media migration runs first, rows are reused |
| `profilePicURL` | string | `profile_pic_id` | fallback when no `profilePic` relation; creates a minimal `media` row if the url is unknown |
| `coverImage` | media | `cover_image_id` | resolved against `media` by url |
| `social` | component | `social` (Json) | stored as-is |
| `seo` | component | `seo` (Json) | stored as-is |
| `tracking` | component | `tracking` (Json) | stored as-is (via admin API) |
| `isFeatured` | boolean | `is_featured` | via admin API |
| `priority` | integer (default 100) | `priority` | |
| `isInstaActive` | boolean | — | **dropped for now** — available via admin API; pending decision (own column vs fold into `social`) |
| `createdAt` / `updatedAt` | datetime | — | **lost** — the new `users` table has no timestamp columns; pending decision |

## Field mapping — location

| Legacy field | Type | New column | Notes |
|---|---|---|---|
| `country` | relation → country | `country_id` | looked up by name — **geo migration must run first** |
| `city` | **free-text string** | `city_id` (FK) | ⚠️ cannot be auto-resolved — the script prints `(email, city)` pairs as a MANUAL REVIEW list; resolve against the new `cities` table by hand |
| — | | `region_id`, `locality_id` | legacy never stored these on users — NULL |

## Field mapping — membership & roles

| Legacy field | Type | New target | Notes |
|---|---|---|---|
| `user_type` | 1:1 relation → UserType | `user_roles` row (`user_type_id` by slug) | user_types are migrated from legacy `/api/user-types` first (step 1 of `users.py`); no legacy type → the legacy default (`regular`); unmatched slugs fall back to default and are reported |
| `isLoyaltyMember` | boolean | `users.tier` | `true → star_life`, `false → free` (via admin API) |
| `company` | N:1 relation | `user_roles.company_id` | matched against `companies.name` (**company migration runs first**); unmatched names are reported |

## Legacy id map

The new `users` table does not store the legacy Strapi id, but later
migrations (circles, memories, content) reference users **by that id**. The
script writes `legacy_user_id_map.json` (repo root): legacy id → new
`users.id`, with duplicates-by-email pointing at the same new user.

## Not migrated here (separate migrations)

| Legacy field(s) | Future home |
|---|---|
| `bookmarks`, `follows`, `followings`, `follow_albums`, `follow_companies`, `follow_affiliates`, `follow_tags`, `follow_city_guides` | `circles` (relationship = bookmark / follow semantics) |
| `postcards`, `albums`, `travelogues`, `restaurants`, `dx_cards`, `property_itineraries` | content migrations + `circles` (relationship = author) |
| `memories`, `memory` | Memory migration |
| `profile` (travel preferences enums) | `user_personas` / `user_persona_tags` — derive later |
| `destination_expert` | Destination Expert content migration |
| `chats` | **dropped** — chat is not in the new model |
| computed extras (`bookmarkedCount`, `postcardsCreated`, `uniqueCollectors`, ...) | derived values, recomputable — dropped |

## What needs manual work — checklist

1. **Passwords** — decide: direct-DB hash copy vs forced reset (see above).
2. **Free-text `city` list** — resolve every entry in the script's
   `MANUAL REVIEW` output to a real `city_id`.
3. **`is_admin` flag** — no legacy equivalent; grant manually to the staff
   who need it.
4. **Pending decisions** — `createdAt` (registration dates — lost without a
   schema addition), `isInstaActive`, verbatim `fullName`.
5. **Skipped users** — the script lists users with no email/username;
   fix at the source or discard.

## Run order

```text
npm run migrate:deploy → seed.py → geo_migration.py → media.py → company.py → users.py
                                   (= python scripts/migrate_data.py)
```
