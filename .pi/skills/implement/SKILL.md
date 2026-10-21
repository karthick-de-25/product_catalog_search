---
name: implement
description: Execute an approved feature plan slice by slice with tests, committing at each green slice and only pausing for critical (Tier C) changes. Use after the human approves a plan, when asked to "implement F03", "build the next slice", "continue the feature", or to resume an in-progress feature.
---

# Implement an approved plan

You are the **implementation agent**. You execute an **approved** plan in
`docs/plan/FNN-slug.md`, one vertical slice at a time, keeping the repo green after every
slice. You do **not** redesign the feature — if the plan is wrong, stop and amend it via the
`plan` skill.

> Bind to [`AGENTS.md`](../../../AGENTS.md) §5 (approval policy), §7 (Definition of Done),
> and §9 (conventions). Bind to [`CONTEXT.md`](../../../CONTEXT.md) invariants.

---

## Inputs

- `$ARGUMENTS` — a feature id (`F03`) or empty (resume the current `in-progress`/`approved` feature).

## Preconditions — verify before writing any code

1. Resolve the feature and read its plan file.
2. **Require `status: approved`** in the frontmatter.
   - If `proposed` → stop: "This plan is not approved. Run `/skill:plan FNN` or reply
     **approve FNN**."
   - If `blocked` → stop and report the blocker.
   - If `done` → ask whether to re-open or verify instead.
3. Check dependencies listed in the plan are `done` in `ROADMAP.md`. If not, stop.
4. Ensure a clean baseline: run `make check` (or `pytest` if Makefile target absent).
   Record the result. If it is already red, fix the baseline **only if** it is within this
   plan's scope; otherwise stop and report.

---

## Loop — one slice at a time

Repeat the following until every slice is checked:

### 1. Load the slice
Read the next unchecked slice. Restate in one sentence: **Inputs → Outputs → Test**.
Mark the slice `[~] in-progress` in the plan file (and `ROADMAP.md` → `in-progress`).

### 2. Confirm the tier
Scan the slice for Tier C actions (cloud/GCP, cost, destructive, secrets, breaking contracts
or interfaces, new deps, scope). If any are present, **stop and ask the human** with the exact
command and its blast radius:

```
🔴 Tier C approval needed (slice: <name>)
Action:  <exact command or change>
Why:     <reason>
Cost/impact: <cost or blast radius>
Reply **approve** to proceed, or tell me an alternative.
```

Do not proceed until you get an explicit yes. Record the approval in the plan `## Log`.

Tier B actions: proceed, but append a `## Log` line first.
Tier A: just do it.

### 3. Write the test first (or alongside)
- Add/extend a test in `tests/` that fails for the right reason before the code exists.
  Use tiny fixtures from `tests/fixtures/`; never depend on real supplier data or the network.
- Prefer delegating a large isolated implementation to the `worker` subagent with
  `agentScope: "both"`; keep the plan, the tier check, and verification in this context.

### 4. Implement minimally
- Smallest change that satisfies the slice's acceptance criteria and nothing more.
- Follow conventions in `AGENTS.md` §9 and layer boundaries in `CONTEXT.md`.
- No new dependency without Tier C approval.
- No cloud calls in default code paths; guard them behind config flags.
- Preserve the invariants: `bronze = silver + quarantine` counts, canonical units,
  `unknown ≠ false`, LLM output validated + confidence-scored, no silent drops.

### 5. Verify locally
Run the slice's stated test, plus:
```bash
make check          # ruff + mypy + pytest   (or the targets that exist)
```
All must pass. If they fail, fix before moving on. Never leave a red slice.

### 6. Tick and log
- Mark the slice `[x] done` in the plan; update the plan `## Log`:
  `- <date> slice "<name>": <one-line summary>; make check ✓`.
- Update `ROADMAP.md` if the feature's status changed.
- Commit (if the repo is a git repo and the human has not asked otherwise):
  `git add -A && git commit -m "FNN(slice-N): <summary>"`.

### 7. Report progress (brief)
One or two lines: what landed, test result, next slice. Then continue to the next slice
**without waiting for approval** — that is the point of plan approval.

---

## Completion

When all slices are checked:

1. Run `/skill:verify FNN` (load the `verify` skill) and produce the evidence report.
2. If PASS: set the plan `status: done`, update `ROADMAP.md` to `done`, and summarize.
3. If FAIL: fix within scope; if the fix exceeds the plan, return to the `plan` skill.

Final message format:

```
## Completed — FNN <title>
Slices: n/n
Evidence: <make check tail / test counts>
Files changed: <high-level list>
Tier C approvals obtained: <list or "none">
Next: <next roadmap feature id and title>
```

---

## Stop conditions (do not continue past these)

- The plan is not approved, or is blocked.
- A Tier C action was not approved.
- The baseline `make check` is red for reasons outside this plan.
- The plan's assumptions proved false, or a breaking change is needed → **amend the plan**.
- You would need to touch a file or layer the plan does not mention → ask first.
- A slice cannot be made green in a reasonable effort → mark `[!] blocked` in the plan, log
  the reason, and report.

## Anti-patterns (never do these)

- Implementing slices out of order, or batching several slices into one unreviewable commit.
- Broad refactors "while we're here" — file a roadmap item instead.
- Marking a slice done with a skipped or disabled test.
- Hard-coding thresholds/paths/credentials that belong in config or contracts.
- Adding retries/silent fallbacks that hide data-quality or cloud errors.
- Editing `AGENTS.md`, skills, or approval policy (Tier C).
