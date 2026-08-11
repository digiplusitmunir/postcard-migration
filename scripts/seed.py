"""Seed ALL developer-defined type/definition tables.

Boilerplate seed for every table the API/application will NOT write to —
these rows are entered by developers and everything else hangs off them.
Each table gets its real known values or 2-3 samples; extend the lists as
the platform grows.

  collection_types          Properties, Restaurants, Events, ...
  subcollection_types       Journey (under Properties)
  collection_cluster_types  City Guide
  cluster_type_collection_types
                            City Guide -> Restaurants, Events, Shopping
  tags                      sample postcard-level feature tags
  response_types            contact_form, feedback, newsletter_signup
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

# name, slug, priority
COLLECTION_CLUSTER_TYPES = [
    ("City Guide",          "city-guide",          1),
]

# Which collection types each cluster type is a cluster OF — a City Guide
# groups the geo-direct content of a city: Restaurants, Events and Shopping.
# This drives the geo-derived entries in scripts/cityguide.py, so a collection
# type left out here is never pulled into a cluster of that kind.
# cluster_type_slug, collection_type_slug, priority (order within the cluster)
CLUSTER_TYPE_COLLECTION_TYPES = [
    ("city-guide", "restaurants", 1),
    ("city-guide", "events",      2),
    ("city-guide", "shopping",    3),
]

# NOTE: user_types are NOT seeded here — they are migrated from the legacy CMS
# by notebooks/media_usertypes_companies_migration.ipynb.

# -----------------------------------------------------------------------------
# Classification (domain model, Figure 4)
# -----------------------------------------------------------------------------

# NOTE: facet_types / facet_values are NOT seeded here — they are migrated from
# the legacy CMS: Tag -> 'Experience' (notebooks/tags_facet_migration.ipynb);
# Category / Environment / Tag-group facets follow in their own tracker rows.

# name, slug — granular postcard-level feature tags (samples)
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

        for name, slug, priority in COLLECTION_CLUSTER_TYPES:
            cur.execute(
                """
                INSERT INTO collection_cluster_types (name, slug, priority)
                VALUES (%s, %s, %s)
                ON CONFLICT (slug) DO UPDATE
                SET name = EXCLUDED.name,
                    priority = EXCLUDED.priority
                """,
                (name, slug, priority),
            )
        print(f"collection_cluster_types  : {len(COLLECTION_CLUSTER_TYPES)} upserted")

        for cluster_slug, ct_slug, priority in CLUSTER_TYPE_COLLECTION_TYPES:
            cur.execute(
                """
                INSERT INTO cluster_type_collection_types
                    (cluster_type_id, collection_type_id, priority)
                SELECT cct.id, ct.id, %s
                FROM collection_cluster_types cct, collection_types ct
                WHERE cct.slug = %s AND ct.slug = %s
                ON CONFLICT (cluster_type_id, collection_type_id) DO UPDATE
                SET priority = EXCLUDED.priority
                """,
                (priority, cluster_slug, ct_slug),
            )
            if cur.rowcount != 1:
                sys.exit(f"seed failed: cluster type '{cluster_slug}' or collection type "
                         f"'{ct_slug}' does not exist")
        print(f"cluster_type_collection_types: {len(CLUSTER_TYPE_COLLECTION_TYPES)} upserted")

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
