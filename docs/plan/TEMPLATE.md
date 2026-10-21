---
feature: FNN
title: <Short feature title>
status: proposed          # proposed | approved | in-progress | blocked | done
owner: agent
approved:                 # YYYY-MM-DD, set only by the human
created: YYYY-MM-DD
updated: YYYY-MM-DD
depends_on: []
---

# FNN — <Feature title>

## Goal
One sentence describing the user-visible outcome.

## Why now
What it unblocks, and how it fits the delivery order.

## Scope
- In scope: …
- Non-goals: …

## Assumptions
- [ ] <assumption> — verify by <how>

## Open questions (needs human)
- <question, or "none">

## Acceptance criteria (feature-level)
- [ ] AC1: <observable, testable statement>
- [ ] AC2: …

---

## Slices

> Each slice must be vertical (input → output → observable result), independently testable,
> and leave `make check` green. Copy the slice block per slice.

### Slice N — <name>
- **Status:** `[ ]` todo · `[~]` in progress · `[x]` done · `[!]` blocked
- **Tier:** 🟢 autonomous / 🟡 announce / 🔴 needs approval
- **Inputs:** <files/tables/args>
- **Outputs:** <artifacts/rows/API>
- **Files:** `path/to/file.py`, `sql/xx.sql`
- **Acceptance criteria:**
  - [ ] <specific, observable>
- **Test:** `tests/...::test_...` — asserts <what>
- **Tier C actions (if any):** <exact command + blast radius, or "none">
- **Notes:** <gotchas, links to ADRs>

---

## Commands
```bash
make check
make <target>
```

## Risks
- <risk> → <mitigation>

## Rollback
How to undo this feature if it lands badly (files to revert, tables to drop — Tier C).

---

## Log
- YYYY-MM-DD — plan created.
