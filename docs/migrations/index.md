# Migrations — Overview & Run Order

Each data migration is a script in `scripts/` and/or a Jupyter notebook in
`notebooks/`, with a companion document here describing the full field
mapping, what gets dropped, and what needs manual work afterwards.

`python scripts/migrate_data.py` runs the scripted steps (seed → geo → media
→ company → users → directory/album → tags facet → postcard → journey →
city guide → bookmark) in sequence and stops on the first failure.

## Run order — this matters

Migrations depend on each other's data. Always run them in this order:

```text
0. Prerequisites   npm run migrate:deploy  +  python scripts/seed.py
                        (schema + type tables — see Get Started)

1. Geo             scripts/geo_migration.py  (or notebooks/geo_migration.ipynb)
                        countries → regions → cities (synthesized) → localities
                        nothing depends on users; everything depends on geo

2. Media           scripts/media.py
                        legacy upload files → media — independent; covers,
                        icons and profile pics all resolve against it

3. Company         scripts/company.py
                        companies incl. icon → icon_media_id (needs media);
                        must run BEFORE users — user_roles.company_id links
                        roles to these rows (nothing on the company side
                        depends on users)

4. Users           scripts/users.py  (or notebooks/user_migration.ipynb)
                        user_types → users → user_roles — requires geo
                        (country lookups), media (profile pics / covers) and
                        company (role links); needs CMS_ADMIN_EMAIL/PASSWORD
                        in .env (the public users endpoint strips emails).
                        user_types also migratable interactively via
                        media_usertypes_companies_migration.ipynb (step 2)

5. Directory/Album scripts/directory_album.py  (or notebooks/directory_album_migration.ipynb)
                        directories → collection_types; albums → collections
                        for types WITH a collection layer (Properties), or
                        straight into POSTCARDS for Restaurants/Events/
                        Shopping (has_dedicated_collection = false, so
                        collection_id stays NULL) — requires geo
                        (country/region/locality), media (covers), company
                        (managed_by links), seed, and schema migration
                        20260811060000 (postcards.website). Designer Tours is
                        skipped (dx-card migration later); writes
                        legacy_album_id_map.json (album → collection) AND
                        legacy_album_postcard_id_map.json (album → postcard).
                        Optional author/assigned_staff circles: notebook only

6. Tags facet      scripts/tags_facet.py  (or notebooks/tags_facet_migration.ipynb)
                        tags → FacetType 'Experience' + facet_values — only
                        needs seed (independent of geo/media/company/users).
                        NO facet_assignments yet; writes legacy_tag_id_map
                        (+ tag-group linkage side file) for the postcards
                        migration to create them (owned_type=postcard)

7. Postcard        scripts/postcard.py  (or notebooks/postcard_migration.ipynb)
                        postcards → postcards + tags → facet_assignments
                        (owned_type=postcard) — consumes the album AND tag
                        per-env map files (hard prerequisites) plus the
                        album→postcard map (optional); ADDS to the postcards
                        rows step 5 already created for Restaurants/Events/
                        Shopping albums, whose slugs it reserves; Designer
                        Tours postcards skipped (dx-card migration later);
                        writes legacy_postcard_id_map for bookmarks/memories.
                        Optional author circles: notebook only

8. Journey         scripts/journey.py  (or notebooks/journey_migration.ipynb)
                        property_itineraries → subcollections (Journey under
                        Properties) + ordered subcollection_postcards join —
                        consumes the album AND postcard per-env map files
                        (hard prerequisites); needs schema migration
                        20260810060000 (cover + days columns); writes
                        legacy_itinerary_id_map for enquiries/bookings.
                        Optional author circles: notebook only

9. City Guide      scripts/cityguide.py  (or notebooks/cityguide_migration.ipynb)
                        city_guides → collection_clusters (City Guide type) +
                        geo-derived collection_cluster_entries for live
                        collections AND live collection-less postcards in the
                        region — legacy region maps to the v2 CITIES tier
                        (cities were synthesized 1:1 from regions); needs
                        schema migration 20260810080000 (cover +
                        community_link columns);
                        writes legacy_cityguide_id_map for follows (#24)

10. Bookmark       scripts/bookmark.py  (or notebooks/bookmark_migration.ipynb)
                        bookmarks → circles (owned_type=postcard,
                        relationship=bookmark) — first use of the Circle
                        layer; consumes the user AND postcard per-env map
                        files (hard prerequisites); createdAt carried into
                        added_at; Designer Tours bookmarks re-attach after
                        the dx-card migration (#13)

11. ...next        remaining facets (Category/Environment/Tag-group),
                        circles (follows), memories — to be added, in an
                        order that respects their FKs
```

| # | Migration | Depends on | Mapping doc | Notebook (rendered) |
|---|---|---|---|---|
| 1 | Geo | seed only | [Geo Migration](geo-migration.md) | [geo_migration.ipynb](notebooks/geo_migration.ipynb) |
| 2 | Media | — | [Media Migration](media-migration.md) | [media_usertypes_companies_migration.ipynb](notebooks/media_usertypes_companies_migration.ipynb) |
| 3 | Company | **2** | [Company Migration](company-migration.md) | [media_usertypes_companies_migration.ipynb](notebooks/media_usertypes_companies_migration.ipynb) |
| 4 | Users | **1**, **2**, **3**, user types | [User Migration](user-migration.md) | [user_migration.ipynb](notebooks/user_migration.ipynb) |
| 5 | Directory/Album | **1**, **2**, **3**, seed, schema `20260811060000` | [Directory & Album Migration](directory-album-migration.md) | [directory_album_migration.ipynb](notebooks/directory_album_migration.ipynb) |
| 6 | Tags facet | seed only | [Tags Facet Migration](tags-facet-migration.md) | [tags_facet_migration.ipynb](notebooks/tags_facet_migration.ipynb) |
| 7 | Postcard | **5**, **6** (map files) | [Postcard Migration](postcard-migration.md) | [postcard_migration.ipynb](notebooks/postcard_migration.ipynb) |
| 8 | Journey | **5**, **7** (map files) | [Journey Migration](journey-migration.md) | [journey_migration.ipynb](notebooks/journey_migration.ipynb) |
| 9 | City Guide | **1**, **2**, **5**, seed | [City Guide Migration](cityguide-migration.md) | [cityguide_migration.ipynb](notebooks/cityguide_migration.ipynb) |
| 10 | Bookmark | **4**, **7** (map files) | [Bookmark Migration](bookmark-migration.md) | [bookmark_migration.ipynb](notebooks/bookmark_migration.ipynb) |

The **Notebook (rendered)** column shows the live notebook — every markdown and
code cell — rendered straight from `notebooks/*.ipynb`. It is the same file you
run in Jupyter; the mapping doc beside it explains the field-by-field decisions.

!!! warning "Don't skip ahead"
    Running the user notebook before geo leaves every `users.country_id`
    NULL — the lookups silently miss. Each notebook states its prerequisites
    in its first cell; trust that list.

!!! info "`postcards` is written by steps 5 and 7"
    Only collection types with `has_dedicated_collection = true` (Properties)
    get `collections` rows. Restaurants/Events/Shopping albums *are* content,
    so step 5 writes them into `postcards` with `collection_id = NULL`, and
    step 7 adds the legacy postcards around them. See
    [the album split](directory-album-migration.md#the-album-split-collections-vs-postcards).

## Re-running

All notebooks are idempotent (upserts on natural keys). To restart an
experiment from scratch:

```powershell
python scripts/truncate_all.py
python scripts/seed.py
# then re-run the notebooks, again in order
```
