"""Seed ALL developer-defined type/definition tables.

Boilerplate seed for every table the API/application will NOT write to —
these rows are entered by developers and everything else hangs off them.
Each table gets its real known values or 2-3 samples; extend the lists as
the platform grows.

  collection_types          Properties, Restaurants, Events, ...
  subcollection_types       Journey (under Properties)
  collection_cluster_types  City Guide (+ collection_type_ids: which collection
                            types it clusters — Restaurants, Events, Shopping;
                            + match_field: the column that binds content to a
                            cluster instance — region_id for City Guide)
  tags                      curated persona-interest tags (samples)
  response_types            contact_form
  response_fields           field definitions per response type

Idempotent: everything upserts on its natural key (slug / field name), so it
is safe to run after every truncate_all.py.

Usage:
    python scripts/seed.py
"""

import os
import sys
from pathlib import Path

import psycopg
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

# -----------------------------------------------------------------------------
# Content hierarchy types
# -----------------------------------------------------------------------------

# name, slug, has_dedicated_collection, priority
COLLECTION_TYPES = [
    ("Properties",         "properties",         True,  1),
    ("Restaurants",        "restaurants",        False, 2),
    ("Events",             "events",             False, 3),
    ("Shopping",           "shopping",           False, 4),
    ("Destination Expert", "destination-expert", True,  5),
]

# collection_type_slug, name, slug, priority
SUBCOLLECTION_TYPES = [
    ("properties", "Journey", "journey", 1),
]

# name, slug, priority, collection_type_slugs, match_field
#
# A cluster type declares BOTH halves of its derivation rule:
#   collection_type_slugs -> collection_cluster_types.collection_type_ids:
#       which collection types are eligible, in display order.
#   match_field: which column on collections/postcards matches content to a
#       specific cluster instance.
# Rendering a cluster page is a query, not a stored join:
#   WHERE collection_type_id = ANY(collection_type_ids)
#     AND <match_field> = <the cluster row's own value for that field>
# There is deliberately no collection_cluster_entries table (tracker
# 2026-08-12: cluster membership is fully derived, never curated).
COLLECTION_CLUSTER_TYPES = [
    ("City Guide", "city-guide", 1, ["restaurants", "events", "shopping"], "region_id"),
]

# NOTE: user_types are NOT seeded here — they are migrated from the legacy CMS
# by notebooks/media_usertypes_companies_migration.ipynb.

# -----------------------------------------------------------------------------
# Classification (domain model, Figure 4)
# -----------------------------------------------------------------------------

# NOTE: facet_types / facet_values are NOT seeded here — they are migrated from
# the legacy CMS: Tag -> 'Experience' (scripts/tags_facet.py); Category and
# Environment -> per-collection-type facets (scripts/category_environment_facet.py).

# name, slug — curated interest vocabulary for the persona engine
# (user_persona_tags). Legacy content tags do NOT go here; they migrate to
# facet_values under FacetType 'Experience'.
TAGS = [
    ("Stargazing",    "stargazing"),
    ("Infinity Pool", "infinity-pool"),
    ("Farm to Table", "farm-to-table"),
]

# -----------------------------------------------------------------------------
# Response form definitions
# contact_form mirrors the legacy Strapi ContactUs collection.
# -----------------------------------------------------------------------------

# name, slug, description
RESPONSE_TYPES = [
    ("contact_form",      "contact-form",      "Contact Us form (legacy ContactUs)"),
]

# response_type slug, field_name, field_type, is_required, order
RESPONSE_FIELDS = [
    ("contact-form",      "first_name",   "string",   True,  1),
    ("contact-form",      "last_name",    "string",   False, 2),
    ("contact-form",      "email",        "email",    True,  3),
    ("contact-form",      "country_code", "number",   False, 4),
    ("contact-form",      "phone_number", "phone",    False, 5),
    ("contact-form",      "question",     "textarea", True,  6),
]


def main() -> None:
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        sys.exit("DATABASE_URL not set — check the .env file in the project root.")

    with psycopg.connect(database_url) as conn, conn.cursor() as cur:
        for name, slug, dedicated, priority in COLLECTION_TYPES:
            cur.execute(
                """
                INSERT INTO collection_types (name, slug, has_dedicated_collection, priority)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (slug) DO UPDATE
                SET name = EXCLUDED.name,
                    has_dedicated_collection = EXCLUDED.has_dedicated_collection,
                    priority = EXCLUDED.priority
                """,
                (name, slug, dedicated, priority),
            )
        print(f"collection_types          : {len(COLLECTION_TYPES)} upserted")

        for ct_slug, name, slug, priority in SUBCOLLECTION_TYPES:
            cur.execute(
                """
                INSERT INTO subcollection_types (collection_type_id, name, slug, priority)
                SELECT id, %s, %s, %s FROM collection_types WHERE slug = %s
                ON CONFLICT (slug) DO UPDATE
                SET name = EXCLUDED.name,
                    collection_type_id = EXCLUDED.collection_type_id,
                    priority = EXCLUDED.priority
                """,
                (name, slug, priority, ct_slug),
            )
        print(f"subcollection_types       : {len(SUBCOLLECTION_TYPES)} upserted")

        for name, slug, priority, ct_slugs, match_field in COLLECTION_CLUSTER_TYPES:
            # collection_type_ids resolved from slugs, list order preserved by
            # WITH ORDINALITY (the array order is the display order)
            cur.execute(
                """
                INSERT INTO collection_cluster_types
                    (name, slug, priority, collection_type_ids, match_field)
                SELECT %s, %s, %s, ARRAY(
                    SELECT ct.id
                    FROM unnest(%s::text[]) WITH ORDINALITY AS s(slug, ord)
                    JOIN collection_types ct ON ct.slug = s.slug
                    ORDER BY s.ord
                ), %s
                ON CONFLICT (slug) DO UPDATE
                SET name = EXCLUDED.name,
                    priority = EXCLUDED.priority,
                    collection_type_ids = EXCLUDED.collection_type_ids,
                    match_field = EXCLUDED.match_field
                RETURNING collection_type_ids
                """,
                (name, slug, priority, ct_slugs, match_field),
            )
            resolved = cur.fetchone()[0]
            if len(resolved) != len(ct_slugs):
                sys.exit(f"seed failed: cluster type '{slug}' lists {len(ct_slugs)} collection "
                         f"type slugs {ct_slugs} but only {len(resolved)} resolved — check for "
                         f"a typo against COLLECTION_TYPES")
        print(f"collection_cluster_types  : {len(COLLECTION_CLUSTER_TYPES)} upserted "
              + ", ".join(f"({slug} clusters {len(cts)} types, match on {mf})"
                          for _, slug, _, cts, mf in COLLECTION_CLUSTER_TYPES))

        for name, slug in TAGS:
            cur.execute(
                """
                INSERT INTO tags (name, slug)
                VALUES (%s, %s)
                ON CONFLICT (slug) DO UPDATE
                SET name = EXCLUDED.name
                """,
                (name, slug),
            )
        print(f"tags                      : {len(TAGS)} upserted")

        for name, slug, description in RESPONSE_TYPES:
            cur.execute(
                """
                INSERT INTO response_types (name, slug, description)
                VALUES (%s, %s, %s)
                ON CONFLICT (slug) DO UPDATE
                SET name = EXCLUDED.name,
                    description = EXCLUDED.description
                """,
                (name, slug, description),
            )
        print(f"response_types            : {len(RESPONSE_TYPES)} upserted")

        for rt_slug, field_name, field_type, is_required, order in RESPONSE_FIELDS:
            cur.execute(
                """
                INSERT INTO response_fields
                    (response_type_id, field_name, field_type, is_required, "order")
                SELECT id, %s, %s, %s, %s FROM response_types WHERE slug = %s
                ON CONFLICT (response_type_id, field_name) DO UPDATE
                SET field_type = EXCLUDED.field_type,
                    is_required = EXCLUDED.is_required,
                    "order" = EXCLUDED."order"
                """,
                (field_name, field_type, is_required, order, rt_slug),
            )
        print(f"response_fields           : {len(RESPONSE_FIELDS)} upserted")

        conn.commit()
        print("\nSeed complete.")


if __name__ == "__main__":
    main()
