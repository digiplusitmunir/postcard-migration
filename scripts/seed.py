"""Seed ALL developer-defined type/definition tables.

Boilerplate seed for every table the API/application will NOT write to —
these rows are entered by developers and everything else hangs off them.
Each table gets its real known values or 2-3 samples; extend the lists as
the platform grows.

  collection_types          Properties, Restaurants, Events, ...
  user_types                Member, Partner, Staff Editor, Admin  (the roles
                            a UserRole row can point at — user_roles itself
                            is written by the app/user-migration, not here)
  subcollection_types       Journey (under Properties)
  collection_cluster_types  City Guide, Partner Affiliation
  facet_types               Property Type, Experience Theme, Cuisine
  facet_values              starter values per facet type
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
    ("Partner Affiliation", "partner-affiliation", 2),
]

# -----------------------------------------------------------------------------
# Actor types (role definitions — NOT user_roles rows, the app creates those)
# -----------------------------------------------------------------------------

# name, slug, is_default, is_creator, is_admin
USER_TYPES = [
    ("Member",       "member",       True,  False, False),
    ("Partner",      "partner",      False, True,  False),
    ("Staff Editor", "staff-editor", False, True,  False),
    ("Admin",        "admin",        False, False, True),
]

# -----------------------------------------------------------------------------
# Classification (domain model, Figure 4)
# -----------------------------------------------------------------------------

# name, slug, applies_to collection_type slug (None = applies broadly), allows_multiple
FACET_TYPES = [
    ("Property Type",    "property-type",    "properties",  False),
    ("Experience Theme", "experience-theme", None,          True),
    ("Cuisine",          "cuisine",          "restaurants", True),
]

# facet_type_slug, name, slug
FACET_VALUES = [
    ("property-type",    "Boutique Stays",        "boutique-stays"),
    ("property-type",    "Signature Experiences", "signature-experiences"),
    ("property-type",    "Glamping",              "glamping"),
    ("experience-theme", "Cultural",              "cultural"),
    ("experience-theme", "Wellness",              "wellness"),
    ("cuisine",          "Indian",                "indian"),
    ("cuisine",          "Italian",               "italian"),
]

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
    ("feedback",          "feedback",          "General feedback form"),
    ("newsletter_signup", "newsletter-signup", "Newsletter subscription"),
]

# response_type slug, field_name, field_type, is_required, order
RESPONSE_FIELDS = [
    ("contact-form",      "first_name",   "string",   True,  1),
    ("contact-form",      "last_name",    "string",   False, 2),
    ("contact-form",      "email",        "email",    True,  3),
    ("contact-form",      "country_code", "number",   False, 4),
    ("contact-form",      "phone_number", "phone",    False, 5),
    ("contact-form",      "question",     "textarea", True,  6),
    ("feedback",          "message",      "textarea", True,  1),
    ("feedback",          "rating",       "number",   False, 2),
    ("newsletter-signup", "email",        "email",    True,  1),
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

        for name, slug, is_default, is_creator, is_admin in USER_TYPES:
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
                (name, slug, is_default, is_creator, is_admin),
            )
        print(f"user_types                : {len(USER_TYPES)} upserted")

        for name, slug, ct_slug, allows_multiple in FACET_TYPES:
            cur.execute(
                """
                INSERT INTO facet_types (name, slug, applies_to_collection_type_id, allows_multiple)
                VALUES (%s, %s, (SELECT id FROM collection_types WHERE slug = %s), %s)
                ON CONFLICT (slug) DO UPDATE
                SET name = EXCLUDED.name,
                    applies_to_collection_type_id = EXCLUDED.applies_to_collection_type_id,
                    allows_multiple = EXCLUDED.allows_multiple
                """,
                (name, slug, ct_slug, allows_multiple),
            )
        print(f"facet_types               : {len(FACET_TYPES)} upserted")

        for ft_slug, name, slug in FACET_VALUES:
            cur.execute(
                """
                INSERT INTO facet_values (facet_type_id, name, slug)
                SELECT id, %s, %s FROM facet_types WHERE slug = %s
                ON CONFLICT (facet_type_id, slug) DO UPDATE
                SET name = EXCLUDED.name
                """,
                (name, slug, ft_slug),
            )
        print(f"facet_values              : {len(FACET_VALUES)} upserted")

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
