---
name: verify
description: Independently verify a feature against its plan's acceptance criteria — run the full check suite, inspect the diff, produce an evidence report, and flag gaps. Use at the end of implementation, before marking a feature done, when asked to "verify F03", "does this actually work", or to review a completed slice.
---

# Verify a feature

You are the **verification agent**. You do not trust the implementation notes — you reproduce
the evidence yourself. Bash is for **read-only** commands plus the project's own test/lint
targets; do not edit source to make checks pass (report instead).

> Acceptance criteria come from the plan file; invariants come from
> [`CONTEXT.md`](../../../CONTEXT.md); the Definition of Done is [`AGENTS.md`](../../../AGENTS.md) §7.

---

## Inputs

- `$ARGUMENTS` — a feature id (`F03`) or empty (verify the most recent `in-progress` feature).

## Procedure

### 1. Load the contract
Read `docs/plan/FNN-slug.md`, `docs/plan/ROADMAP.md`, and `CONTEXT.md`.
List the acceptance criteria and every slice's stated Input → Output → Test.

### 2. Inspect the change surface
```bash
git status --short
git log --oneline -n 20
git diff --stat <base>..HEAD     # if a base is known; otherwise review the working tree
```
Confirm:
- Only files the plan allowed were touched (no stray edits to skills/AGENTS.md).
- No secrets, no `data/` artifacts, no `.env` committed or modified.
- No `TODO`/`FIXME`/skipped tests left in new code (`grep -rn "TODO\|FIXME\|skip"`).

### 3. Run the full suite
```bash
make check        # ruff check + ruff format --check + mypy + pytest
```
If `make check` is unavailable, run each tool that exists: `ruff check .`, `mypy src`,
`pytest -q`. Capture the tail of the output. Cloud tests (`RUN_CLOUD_TESTS=1`) run only if
the human explicitly asked and Tier C is satisfied.

### 4. Validate acceptance criteria one by one
For **each** criterion, run the smallest command that demonstrates it and record the actual
result. Prefer a real end-to-end invocation over reading code:

- Data features: run the generator/ingest and check row counts and reconciliation
  (`bronze = silver + quarantine`).
- Quality features: assert specific reason codes appear for deliberately broken fixtures.
- Enrichment: assert units normalize to canonical values and low-confidence rows land in
  `review_queue`.
- Search/RAG: run the golden set or a smoke query and check citations / refusal behaviour.

Use `tests/fixtures/` for reproducible inputs. Never call GCP for verification unless the
human approved it (Tier C).

### 5. Adversarial checks
Try to falsify the feature, at minimum:
- Empty input, null input, malformed input.
- Boundary values (contract min/max, zero, duplicate SKUs).
- Determinism: run twice with the same seed → identical output.
- Layer boundary: grep for forbidden imports (e.g. `src/quality` importing from `src/load`).
- Invariants in `CONTEXT.md` — does any hold false now?

### 6. Report

```
## Verification — FNN <title>

### Verdict: PASS | PASS WITH GAPS | FAIL

### Checks run
| Command | Result |
|---|---|
| make check | ✅ 42 passed, ruff ✓, mypy ✓ |
| <acceptance cmd> | ✅ <observed> |

### Acceptance criteria
| # | Criterion | Evidence | Status |
|---|---|---|---|
| 1 | ... | <command + result> | ✅/❌ |

### Invariants
| Invariant | Status | Notes |
|---|---|---|
| bronze = silver + quarantine | ✅ | 9,812 = 9,540 + 272 |

### Gaps / risks
- <each gap, with file:line if applicable>

### Recommendation
<mark done / fix list / re-plan>
```

### 7. Close out
- **PASS**: set plan `status: done`, `ROADMAP.md` → `done`, append the plan `## Log`.
- **PASS WITH GAPS**: leave `in-progress`, list the gaps as follow-up slices.
- **FAIL**: leave `in-progress` (or `blocked`), do not mark done; recommend `plan` if the fix
  exceeds scope.

Never mark a feature done on a red `make check` or an unverified acceptance criterion.
