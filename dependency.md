# Migration Order Plan (old Strapi → new schema)

## What to migrate next, in order

Since many independent tables don't survive into the new schema, the useful sequence after geo (countries → regions → cities → localities) is:

| # | Old table | New table | Why this position |
|---|---|---|---|
| 1 | `files` | `media` | Independent, and nearly everything references cover images, so it unblocks the most |
| 2 | `user_types` | `user_types` | Independent lookup |
| 3 | `companies` | `companies` | Independent |
| 4 | `tag_groups`, then `tags` | `facet_types`, then `tags`/`facet_values` | Tags only depend on tag_groups |
| 5 | `up_users` | `users` | Needs user_types + companies + countries + media — all done by now |
| 6 | — (seed) | `collection_types` | New-schema lookup — mostly hand-seeded from `directories`/`categories`, not a straight copy |
| 7 | `albums` | `collections` | Needs geo, companies, media, users, collection_types |
| 8 | `postcards` | `postcards` | Needs collections, geo, tags, media |
| 9 | `property_itineraries` / `travelogues` | `subcollections` + `subcollection_postcards` | Needs collections + postcards |
| 10 | `memories` | `memories` | Needs users, postcards, geo, media (one of the last) |

## Tables that are dependent (for reference)

Everything else has real FKs:

- `regions` → countries
- `localities` → regions
- `categories` / `environments` → directories
- `tags` → tag_groups
- `up_users` → user_types / companies / countries
- `albums` → (user, country, region, locality, company, category, environment...)
- `postcards` → (user, country, album)
- `memories`, `dx_cards`, `city_guides`, `restaurants`, `travelogues`, `property_itineraries`
- All the activity/social tables (`bookmarks`, `follows*`, `chats`, `sessions`, `events`, `contact_uses`, `content_reviews`, `activity_logs`, `deletions`, `profiles`, `userdevices`, `waiting_lists`) — those all depend on `up_users` and content tables, so they come last or get dropped.

## TL;DR

Immediate next targets: **`media` (files)**, then **`user_types`**, **`companies`**, **`tag_groups` + `tags`**, then **`users`**. That unblocks collections and postcards right after.
