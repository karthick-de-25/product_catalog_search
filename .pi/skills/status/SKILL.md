---
name: status
description: Summarize delivery progress across the roadmap — feature statuses, current slice, blockers, and the next recommended action. Use when asked "where are we", "what's next", "status", "roadmap progress", or at the start of a session to orient before planning or implementing.
---

# Delivery status

Read-only orientation. Produce a short, accurate snapshot. Do not change anything.

## Procedure

1. Read [`docs/plan/ROADMAP.md`](../../../docs/plan/ROADMAP.md).
2. For each feature that is not `todo`, read its `docs/plan/FNN-slug.md` frontmatter and
   count checked/unchecked slices.
3. Read the tail of the `## Log` section of the active feature.
4. Optionally check repo state: `git status --short`, `git log --oneline -5`.
5. Report:

```
## Status — <date>

| Feature | Title | Status | Slices |
|---|---|---|---|
| F00 | Foundation | done | 5/5 |
| F01 | Dirty feeds | in-progress | 2/4 |
| ... | | | |

Active: F01 <title> — next slice: "<slice name>"
Blockers: <list or "none">
Tier C approvals pending: <list or "none">

Recommended next action: /skill:<plan|implement|verify> FNN
```

## Rules
- Derive everything from files; never guess.
- If a status in `ROADMAP.md` disagrees with the plan file, report the mismatch and trust the
  plan file. Suggest reconciling it.
- Keep it to one screen. Offer the next command, don't run it.
