---
name: implement
description: Execute an approved feature plan slice by slice with one light test each, running make check and only pausing for critical (cloud/cost/destructive) changes. Use after the human approves a plan, when asked to "implement F03", or to resume an in-progress feature.
---

# Implement an approved plan

You execute an **approved** plan in `docs/plan/FNN-slug.md`, one slice at a time. Do not redesign
the feature — if the plan is wrong, stop and amend it with `/skill:plan`.

> Bind to [`AGENTS.md`](../../../AGENTS.md) §4 (critical approvals) and §5 (testing policy).

## Preconditions

1. Read the plan; require `status: approved`. Otherwise stop: "Not approved — run `/skill:plan FNN`."
2. Confirm dependencies in `ROADMAP.md` are `done`.
3. Run `make check` to see the baseline. If it is red for reasons outside this plan, stop and report.

## Loop — one slice at a time

1. Read the next unchecked slice; restate it as **in → out → test**. Mark it `[~]`.
2. **Critical check.** If the slice contains a critical action (cloud/GCP, cost, destructive,
   secrets, scope/contract/interface/dependency change), STOP and print:

   ```
   🔴 Critical approval needed (slice: <name>)
   Action: <exact command/change>
   Impact: <cost or blast radius>
   Reply **approve** to proceed, or tell me an alternative.
   ```

   Do not proceed without an explicit yes. Record it in the plan `## Log`.
3. **Test first, then the smallest implementation** that passes it. One happy-path test per
   slice. Do not add edge-case or framework tests.
4. Run `make check` (ruff + pytest). It must be green before moving on.
5. Tick the slice `[x]`, append a one-line `## Log` entry, and commit:
   `FNN(slice-N): <summary>`.
6. Continue to the next slice **without asking again**.

## Finishing

- When every slice is checked, run the feature's end-to-end command once (e.g. `make data`).
- Set the plan `status: done`, update `ROADMAP.md` to `done`, and summarize:

```
## Done — FNN <title>
Slices: n/n   Evidence: <make check tail>
Files:  <list>   Critical approvals: <list or "none">
Next:   <next roadmap feature>
```

## Stop conditions

- Plan not approved or blocked.
- Critical action without approval.
- Baseline `make check` already red for unrelated reasons.
- The work exceeds the plan → amend it.
- You need to touch `AGENTS.md`, `CONTEXT.md`, or `.pi/` → ask first.

## Don't

- Don't refactor broadly, add dependencies, or hard-code config/secrets.
- Don't bypass a failure with a silent fallback.
- Don't mark a slice done with a failing or skipped test.
- Don't write exhaustive test suites — round 1 optimizes for a clear demo.
