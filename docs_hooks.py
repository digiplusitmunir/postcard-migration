"""MkDocs build hook.

The migration notebooks live in `notebooks/` (their run location — the cell
that finds `.env` assumes it). MkDocs can only render files under `docs/`, so
before each build we copy the notebooks into `docs/migrations/notebooks/`.

This keeps a single source of truth (`notebooks/`) and avoids committing a
duplicate — the copied folder is gitignored and regenerated on every build/serve.
"""

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "notebooks"
DEST = ROOT / "docs" / "migrations" / "notebooks"

NOTEBOOKS = [
    "geo_migration.ipynb",
    "media_usertypes_companies_migration.ipynb",
    "user_migration.ipynb",
    "directory_album_migration.ipynb",
    "tags_facet_migration.ipynb",
    "postcard_migration.ipynb",
    "journey_migration.ipynb",
    "cityguide_migration.ipynb",
    "bookmark_migration.ipynb",
]


def on_pre_build(config, **kwargs):
    DEST.mkdir(parents=True, exist_ok=True)
    for name in NOTEBOOKS:
        src = SRC / name
        if src.exists():
            shutil.copy2(src, DEST / name)
