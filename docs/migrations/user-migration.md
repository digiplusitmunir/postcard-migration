# User Migration

Everything about migrating legacy Strapi users (`plugin::users-permissions.user`,
table `up_users`) into the new `users` + `user_roles` tables. Executed by
`notebooks/user_migration.ipynb`.

## The structural change

```text
LEGACY:  up_users ── user_type (1:1)  ── company (N:1) ── follows/bookmarks/...
NEW:     users ──< user_roles >── user_types      (one person, many roles)
                        └── company_id (per role, partner only)
         circles  ← replaces ALL follow/bookmark relations (separate migration)
```

## Field mapping — identity & auth

| Legacy field | Type | New column | Notes |
|---|---|---|---|
| `username` | string, required, unique | `username` (unique) | fallback: email prefix when blank |
| `email` | email, required | `email` (unique) | lowercased; upsert key |
| `password` | password (bcrypt), **private** | `password_hash` | ⚠️ **cannot be fetched via the REST API** — stays NULL. Options: (a) copy hashes with a direct dump of the legacy DB (`up_users.password`, bcrypt-compatible), or (b) force password-reset emails on first login |
| `provider` | string | `auth_provider` | `local`, `facebook`, ... |
| `fbId` | string | `provider_id` | the external provider's user id |
| `confirmed` | boolean | `email_verified` | |
| `blocked` | boolean | `is_blocked` | |
| `resetPasswordToken`, `confirmationToken` | private strings | — | **dropped** — transient auth state |
| `role` (users-permissions role) | relation | — | **dropped** — plugin's permission system is replaced by user_types/user_roles |

## Field mapping — profile

| Legacy field | Type | New column | Notes |
|---|---|---|---|
| `firstName` / `lastName` | string | `first_name` / `last_name` | |
| `fullName` | string | — | used as fallback: split on first space when firstName is empty |
| `slug` | uid (from fullName) | — | **dropped** — new users have no slug |
| `bio` | richtext | `bio` | as-is |
| `profilePic` | media | `profile_pic_id` | needs the media migration; not handled here |
| `profilePicURL` | string | `profile_pic_id` → `media.url` | notebook creates a minimal `media` row from the URL (deduped by url) |
| `coverImage` | media | `cover_image_id` | ⚠️ left NULL — needs media migration |
| `social` | component | `social` (Json) | stored as-is |
| `seo` | component | `seo` (Json) | stored as-is |
| `tracking` | component | `tracking` (Json) | stored as-is |
| `isFeatured` | boolean | `is_featured` | |
| `priority` | integer (default 100) | `priority` | |
| `isInstaActive` | boolean | — | **dropped** — fold into `social` Json manually if still needed |

## Field mapping — location

| Legacy field | Type | New column | Notes |
|---|---|---|---|
| `country` | relation → country | `country_id` | looked up by name — **geo migration must run first** |
| `city` | **free-text string** | `city_id` (FK) | ⚠️ cannot be auto-resolved — the notebook collects `(email, city)` pairs into a MANUAL REVIEW list; resolve against the new `cities` table by hand |
| — | | `region_id`, `locality_id` | legacy never stored these on users — NULL |

## Field mapping — membership & roles

| Legacy field | Type | New target | Notes |
|---|---|---|---|
| `user_type` | 1:1 relation → UserType | `user_roles` row (`user_type_id` by slug) | no legacy type → default **member**; unmatched slugs fall back to member and are reported |
| `isLoyaltyMember` | boolean | `users.tier` | `true → star_life`, `false → free` |
| `company` | N:1 relation | `user_roles.company_id` | ⚠️ **deferred** — companies aren't migrated yet; link partner roles to companies during the company migration |

## Not migrated here (separate migrations)

| Legacy field(s) | Future home |
|---|---|
| `bookmarks`, `follows`, `followings`, `follow_albums`, `follow_companies`, `follow_affiliates`, `follow_tags`, `follow_city_guides` | `circles` (relationship = bookmark / follow semantics) |
| `postcards`, `albums`, `travelogues`, `restaurants`, `dx_cards`, `property_itineraries` | content migrations + `circles` (relationship = author) |
| `memories`, `memory` | Memory migration |
| `profile` (travel preferences enums) | `user_personas` / `user_persona_tags` — derive later |
| `destination_expert` | Destination Expert content migration |
| `chats` | **dropped** — chat is not in the new model |

## What needs manual work — checklist

1. **Passwords** — decide: direct-DB hash copy vs forced reset (see above).
2. **Free-text `city` list** — resolve every entry in the notebook's
   `city_review` output to a real `city_id`.
3. **Cover images / profile pics as Media relations** — re-link once the
   media migration exists (only `profilePicURL` strings are carried today).
4. **Partner ↔ Company** — after the company migration, populate
   `user_roles.company_id` for partner roles.
5. **`is_admin` flag** — no legacy equivalent; grant manually to the staff
   who need it.
6. **Skipped users** — the notebook lists users with no email/username;
   fix at the source or discard.

## Run order

```text
npm run migrate:deploy → python scripts/seed.py → geo_migration.ipynb → user_migration.ipynb
```
