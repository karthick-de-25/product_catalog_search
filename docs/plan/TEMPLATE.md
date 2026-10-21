---
feature: FNN
title: <Short title>
status: proposed          # proposed | approved | in-progress | done | blocked
approved:                 # YYYY-MM-DD — set by the human only
depends_on: []
---

# FNN — <Title>

**Goal:** one sentence describing the observable outcome.
**Non-goals:** what this deliberately does *not* build.

## Slices (≤3)

### Slice 1 — <name>   `[ ]`
- **In → out:** <input> → <observable output>
- **Files:** `src/...`, `tests/...`
- **Test:** one happy-path test that proves the slice works
- **Critical actions:** `none` (or 🔴 exact command + cost/blast radius)
- **Done when:** <1–3 concrete checks>

### Slice 2 — <name>   `[ ]`
- **In → out:** …
- **Files:** …
- **Test:** …
- **Critical actions:** …
- **Done when:** …

## Acceptance (feature-level)
- [ ] <observable, testable>

## Commands
```bash
make check
make <target>
```

## Log
- <date> — plan created (proposed).
