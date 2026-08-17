# 05 — `users.py` (step 5)

Tables: `user_types`, `users`, `user_roles`, **`memberships` (new)**.

Two tracker revisions land here: **R2 (Membership split)** and the `UserType`
field drops. Both break `users.py`'s current logic.

---

## `user_types`

Tracker row: **User-type → UserType**.

| v1 field | v2 target | Disposition | Action |
|---|---|---|---|
| `name` | **`title`** | Transform — *"EXTENSION beyond canonical doc (confirmed intentional) — canonical schema calls this 'name'"* | **RENAME** `name` → `title` |
| `slug` | `slug` | Direct | **Keep** |
| *(relation)* | `UserRole.user_type_id` | Direct | **Keep** ✅ |
| `isDefault` / `isCreator` / `isAdmin` | **(dropped)** | **Flag** — *"DEVIATION beyond canonical doc (confirmed intentional) — canonical schema keeps these as real fields"* | **DROP** all three |

### ⚠️ Decision D3 — dropping `is_default` breaks role assignment

`users.py` hard-fails without it:

```python
# users.py:269-278
cur.execute("SELECT id FROM user_types WHERE is_default LIMIT 1")
default_row = cur.fetchone()
...
if not default_row:
    raise SystemExit("user_types has no is_default row — check legacy /api/user-types")
default_type_id = default_row[0]
```

`default_type_id` is the fallback for every legacy user with no `user_type`, and
for any unrecognised type slug. Dropping the column removes the only way to
find it.

Replacements, in order of preference:

- **(a)** Hard-code the member slug in the script (`WHERE slug = 'member'`). The
  role of "default type" becomes migration config, not schema. Simplest, and
  consistent with the tracker's intent that these are app concerns.
- **(b)** Keep `is_default` only, drop `is_creator` / `is_admin`. Deviates from
  the tracker.
- **(c)** Keep all three. Matches the canonical doc, contradicts the tracker's
  "confirmed intentional" deviation.

`is_creator` and `is_admin` are not read by any script — dropping them is free.
`is_default` is the only real blocker.

ℹ️ `User.is_admin` (on the User model) is a **separate** field and is unaffected.

---

## `users`

Tracker row: **Users-Permissions-User → User + UserRole (kept lean — no
unnecessary relations)**.

| v1 field | v2 target | Disposition | Action |
|---|---|---|---|
| `username` / `email` | `username` / `email` | Direct | **Keep** ✅ |
| `provider` / *(password)* | `auth_provider` / `provider_id` / `password_hash` | Transform — **SECURITY**: *"do not carry forward the shared hardcoded social-login password hash — issue fresh hashes/reset flow"* | **Keep** columns. `password_hash` stays NULL ✅ (already the case) |
| `confirmed` / `blocked` | `email_verified` / `is_blocked` | Direct | **Keep** ✅ |
| `role` | `UserRole.user_type_id` | Transform — *"CONFIRMED 2026-08-12: simplified to just the UserType assignment — no company_id/manager_user_id on User itself; that's a Company-side concern"* | See `user_roles` below |
| *(loyalty flag)* | → **`Membership.tier`** | R2 | **DROP** `users.tier` |
| *(city, free text)* | → `location.city_name` or archive | X1 | **DROP** `users.city_id` |

### Columns to drop

| Column | Reason |
|---|---|
| `tier` | R2 — moves to `Membership`. Delete the `UserTier` enum with it |
| `city_id` | X1 — City tier removed |

### Columns with no tracker row (v2-only — keep as-is)

`slug`, `first_name`, `last_name`, `bio`, `social`, `seo`, `tracking`,
`is_featured`, `priority`, `country_id`, `region_id`, `locality_id`, `is_admin`.

The tracker's *"kept lean — no unnecessary relations"* note is about
**relations**, not these scalar/embedded fields. `users.py` already migrates
`slug`, `bio`, `social`, `seo`, `tracking`, `is_featured`, `priority` and
`country_id`. No action.

⚠️ `users.py` never sets `region_id` or `locality_id` — only `country_id`. The
tracker does not map them. They stay NULL; fine, but worth knowing.

---

## `memberships` — NEW TABLE (R2)

Tracker row: **(implicit in v1 — source TBD) → Membership (new table)**.

> "CONFIRMED 2026-08-12: separate Membership table chosen over a flat field on
> User, to support tier history/expiry."

| v1 field | v2 target | Disposition | Note |
|---|---|---|---|
| *(TBD — locate v1 source)* | `user_id` | **Flag** | FK to User. *"Still need to confirm where v1 actually stores Free/StarLife status before this can move past Decision Needed"* |
| *(TBD — Free/StarLife flag)* | `tier` (enum Free / StarLife) | Transform | |
| *(new)* | `started_at` | Transform | *"no v1 equivalent, defaults to migration date if no better source found"* |
| *(new)* | `ends_at` (nullable) | Transform | *"null = no expiry / not applicable"* |
| *(new)* | `status` (active/expired/cancelled) | Transform | |

### ⚠️ Decision D4 — the v1 source is marked TBD, but the script already assumes one

`users.py` line 247 writes:

```python
"star_life" if u.get("isLoyaltyMember") else "free",
```

So `isLoyaltyMember` **is** being used as the Free/StarLife source today, while
the tracker still lists this as "TBD — locate v1 source". Either the tracker is
stale or the script guessed. Confirm before building `memberships` on top of it.

### Target model

```
model Membership {
  id        BigInt           @id @default(autoincrement())
  userId    BigInt           @map("user_id")
  tier      MembershipTier
  startedAt DateTime         @default(now()) @map("started_at")
  endsAt    DateTime?        @map("ends_at")
  status    MembershipStatus @default(active)
  user User @relation(fields: [userId], references: [id], onDelete: Cascade)
  @@index([userId])
  @@map("memberships")
}

enum MembershipTier   { free  star_life }
enum MembershipStatus { active expired cancelled }
```

Note: **not** `@unique` on `user_id` — the whole point is tier *history*. The
"current" membership is the one with `status = active` (and `ends_at` null or
future). That invariant is a service-layer concern.

`UserTier` enum is **deleted** and replaced by `MembershipTier`.

---

## `user_roles`

Tracker: *"CONFIRMED 2026-08-12: simplified to just the UserType assignment — no
company_id/manager_user_id on User itself; that's a Company-side concern (see
Company block)."*

Reading that carefully: it says no company/manager on **User itself** — which is
already true, they live on `UserRole`. The Company block confirms
`UserRole (user_id + company_id)` as the correct home.

| Column | Action |
|---|---|
| `user_id`, `user_type_id` | **Keep** ✅ |
| `company_id` | **Keep** ✅ — confirmed by the Company row |
| `manager_user_id` | **Keep** — self-referential org hierarchy (Editor → Editor-in-Chief). No v1 source, stays NULL |
| `granted_at`, `status` | **Keep** — v2-only |

**No schema change.**

---

## Script impact

| Change | Where |
|---|---|
| `user_types.name` → `title` | `migrate_user_types()` INSERT + conflict set |
| Drop `is_default` / `is_creator` / `is_admin` from the INSERT | `migrate_user_types()` |
| Replace the `WHERE is_default` lookup per **D3** | `migrate_user_roles()` lines 269–279 |
| Remove `tier` from the users INSERT and conflict set | `migrate_users()` |
| **New step** — write `memberships` from `isLoyaltyMember` (pending **D4**) | new function after `migrate_users()` |
| Drop the free-text-city manual-review list, or re-route to `location.city_name` | `migrate_users()` lines 252–253, 259–261 |
| `companies` lookup `TRIM(name)` → `TRIM(title)` | `migrate_user_roles()` line 272 |
| Ownership FKs (X4) consume `legacy_user_id_map` — **already produced here**, no change | `dump_legacy_id_map()` ✅ |

---

## Summary of actions

| Action | Target |
|---|---|
| **RENAME column** | `user_types.name` → `title` |
| **DROP column** | `user_types.is_default`, `.is_creator`, `.is_admin` |
| **DROP column** | `users.tier`, `users.city_id` |
| **DELETE enum** | `UserTier` |
| **ADD model** | `Membership` + enums `MembershipTier`, `MembershipStatus` |
| **DECISION D3** | Replacement for the `is_default` fallback rule |
| **DECISION D4** | Confirm `isLoyaltyMember` is the Free/StarLife source |
| **NO CHANGE** | `user_roles` |
