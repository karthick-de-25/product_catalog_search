---
name: status
description: Summarize roadmap progress — feature statuses, current slice, blockers, and the next command. Use when asked "where are we", "what's next", "status", or at the start of a session to orient.
---

# Delivery status

Read-only orientation. Produce a one-screen snapshot; do not change anything.

## Steps

1. Read [`docs/plan/ROADMAP.md`](../../../docs/plan/ROADMAP.md).
2. For each non-`todo` feature, read its plan frontmatter and count checked/ticked slices.
3. Read the tail of the active feature's `## Log`.
4. Report:

```
## Status — <date>

| Feature | Title | Status | Slices |
|---|---|---|---|
| F00 | Foundation | done | 5/5 |
| F01 | Dirty feeds | in-progress | 1/2 |
| ... | | | |

Active: F01 — next slice: "<name>"
Blockers / pending critical approvals: <list or "none">
Recommended next: /skill:plan FNN  |  /skill:implement FNN
```

## Rules
- Derive everything from files; never guess.
- If `ROADMAP.md` and a plan disagree, trust the plan and report the mismatch.
- Offer the next command; don't run it.
