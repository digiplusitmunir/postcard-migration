"""Run the full migration pipeline in sequence, stopping on the first failure.

Order:
  1. seed.py           - type/definition tables (collection_types, ...)
  2. geo_migration.py  - countries -> regions -> cities -> localities
  3. media.py          - legacy upload files -> media
  4. company.py        - legacy companies -> companies (incl. icon -> media)
  5. users.py          - user_types, users (media attach), user_roles (company attach)
  6. directory_album.py - directories -> collection_types, albums -> collections
  7. tags_facet.py     - tags -> FacetType 'Experience' + facet_values
  8. postcard.py       - postcards -> postcards + facet_assignments (tags)

Each step runs as its own process; a non-zero exit code (any uncaught
exception in the step) aborts the whole pipeline immediately.

Usage:
    python scripts/migrate_data.py
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
]


def main():
    for i, step in enumerate(STEPS, 1):
        banner = f"[{i}/{len(STEPS)}] {step}"
        print(f"\n{'=' * 60}\n{banner}\n{'=' * 60}", flush=True)
        result = subprocess.run([sys.executable, str(SCRIPTS_DIR / step)])
        if result.returncode != 0:
            sys.exit(f"\nFAILED: {step} (exit code {result.returncode}) - pipeline stopped.")
        print(f"OK: {step}")
    print(f"\nAll {len(STEPS)} migration steps completed successfully.")


if __name__ == "__main__":
    main()
