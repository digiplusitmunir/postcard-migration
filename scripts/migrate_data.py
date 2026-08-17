"""Run the full migration pipeline in sequence, stopping on the first failure.

Order (each step depends on the ones above it):

   1. seed.py                       type/definition tables — collection_types,
                                    subcollection_types, collection_cluster_types
                                    (incl. collection_type_ids + match_field),
                                    persona tags, response types/fields
   2. geo_migration.py              countries (code/continent/flag) -> regions
                                    -> localities (parented DIRECTLY to region;
                                    the City tier was removed 2026-08-05)
   3. media.py                      legacy upload files -> media (full field
                                    set, keyed on legacy_id)
   4. company.py                    legacy companies -> companies (+ logo),
                                    writes legacy_company_id_map
   5. users.py                      user_types, users, memberships, user_roles;
                                    writes legacy_user_id_map
   6. directory_album.py            directories -> collection_types; albums ->
                                    collections (Properties) or postcards
                                    (Restaurants/Events/Shopping); owner and
                                    assignee as direct FKs
   7. tags_facet.py                 tags -> FacetType 'Experience' + facet_values
   8. postcard.py                   postcards -> postcards (+ author FK) and
                                    facet_assignments from tags
   9. journey.py                    property_itineraries -> subcollections
                                    (+ price_type, 1:1 JourneyStatus) and
                                    subcollection_postcards
  10. category_environment_facet.py categories + environments -> facet_types /
                                    facet_values / facet_assignments
  11. cityguide.py                  city_guides -> collection_clusters, anchored
                                    to REGION. Membership is derived at query
                                    time, so nothing else is written.
  12. bookmark.py                   bookmarks -> circles (owned_type=postcard)
  13. follows.py                    all six Follow-* tables -> circles, all as
                                    relationship='bookmark'

Each step runs as its own process; a non-zero exit code (any uncaught exception
in the step) aborts the whole pipeline immediately.

Prerequisites: the schema migration must be applied first
(`npm run migrate:deploy`), and .env must carry CMS_BASE_URL, CMS_API_TOKEN,
DATABASE_URL, CMS_ADMIN_EMAIL and CMS_ADMIN_PASSWORD.

Usage:
    python scripts/migrate_data.py
    python scripts/migrate_data.py --from postcard.py   # resume from a step
    python scripts/migrate_data.py --only cityguide.py  # run one step
"""

import subprocess
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent

STEPS = [
    "seed.py",
    "geo_migration.py",
    "media.py",
    "company.py",
    "users.py",
    "directory_album.py",
    "tags_facet.py",
    "postcard.py",
    "journey.py",
    "category_environment_facet.py",
    "cityguide.py",
    "bookmark.py",
    "follows.py",
]


def select_steps(argv):
    if "--only" in argv:
        step = argv[argv.index("--only") + 1]
        if step not in STEPS:
            sys.exit(f"unknown step '{step}' — expected one of: {', '.join(STEPS)}")
        return [step]
    if "--from" in argv:
        step = argv[argv.index("--from") + 1]
        if step not in STEPS:
            sys.exit(f"unknown step '{step}' — expected one of: {', '.join(STEPS)}")
        return STEPS[STEPS.index(step):]
    return STEPS


def main():
    steps = select_steps(sys.argv[1:])
    if steps != STEPS:
        print(f"running {len(steps)} of {len(STEPS)} steps: {', '.join(steps)}")

    for i, step in enumerate(steps, 1):
        banner = f"[{i}/{len(steps)}] {step}"
        print(f"\n{'=' * 60}\n{banner}\n{'=' * 60}", flush=True)
        result = subprocess.run([sys.executable, str(SCRIPTS_DIR / step)])
        if result.returncode != 0:
            sys.exit(f"\nFAILED: {step} (exit code {result.returncode}) — pipeline stopped.\n"
                     f"Fix the cause, then resume with:\n"
                     f"    python scripts/migrate_data.py --from {step}")
        print(f"OK: {step}")
    print(f"\nAll {len(steps)} migration steps completed successfully.")


if __name__ == "__main__":
    main()
