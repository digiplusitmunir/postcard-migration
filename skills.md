# Agent Skills & Working Rules

Rules for AI agents (Claude Code and others) working in this repository.

## Jupyter notebooks — NEVER edit directly

When a change involves a notebook (`notebooks/*.ipynb`):

- **Do NOT** modify the `.ipynb` file with any edit tool.
- **Instead**, reply with the full code (or markdown) for each affected cell as
  a copy-pasteable snippet, clearly labelled with which cell it replaces or
  where to insert it (e.g. "replace the cell under *2. Transform + upsert*").
- One snippet per cell, complete cell contents — no partial diffs to hand-apply.
- The user pastes and runs the cells themselves; cell outputs stay under their
  control.

**Why:** direct `.ipynb` edits clobber execution state/outputs and bypass the
user's review — they want to run every migration cell by hand.

## All other files — direct edits are fine

Scripts (`scripts/*.py`), schema (`schema/schema.prisma`), docs (`docs/**`),
config, etc. may be edited directly with the normal tools, following the usual
practice of showing/summarizing what changed.
