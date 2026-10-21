---
name: plan
description: Turn a roadmap feature into a short slice-by-slice plan and stop for human approval. Use when starting a feature, when asked to "plan F03" or "what's next", or when a plan needs amending. Writes docs/plan/FNN-*.md and stops before any code is written.
---

# Plan a feature

You are the planning agent. Read-only: only write under `docs/plan/`. Never touch `src/`,
`tests/`, `sql/`, `contracts/`, or `data/`.

> Bind to [`AGENTS.md`](../../../AGENTS.md) §4 (critical approvals) and
> [`CONTEXT.md`](../../../CONTEXT.md) (invariants, reason codes).

## Steps

1. Read [`docs/plan/ROADMAP.md`](../../../docs/plan/ROADMAP.md). Pick the feature from
   `$ARGUMENTS` (id or name); if empty, the first unblocked `todo`.
   If it is already `approved`/`in-progress`, ask before overwriting.
2. Scout the repo read-only. For anything larger than a couple of files, delegate to the
   `scout` subagent (`agentScope: "both"`) to save context.
3. Break the feature into **at most 3 vertical slices**. Each slice is input → observable
   output, independently runnable, with **one happy-path test**. No exhaustive edge cases.
4. For each slice, flag any **critical action** (`AGENTS.md` §4): cloud/GCP, cost, destructive,
   secrets, scope/contract/interface/dependency changes.
5. Write `docs/plan/FNN-slug.md` from [`TEMPLATE.md`](../../../docs/plan/TEMPLATE.md), with
   `status: proposed`. Keep it under a page.
6. **STOP.** Present the summary below and wait.

```
Feature FNN — <title>   (proposed)
Goal:      <one sentence>
Slices:    <n>  (list)
Critical:  <items needing sign-off, or "none">
Plan file: docs/plan/FNN-slug.md
```

> Reply **approve FNN** to proceed, or tell me what to change.

7. On approval: set `status: approved`, `approved: <YYYY-MM-DD>`, append a `## Log` line,
   update `ROADMAP.md` to `approved`, and tell the human to run `/skill:implement FNN`.

## Rules
- One plan per feature. Amend in place; never create `FNN-v2.md`.
- Never invent scope or contradict `CONTEXT.md`.
- Never plan a cloud action without marking it critical.
- If a dependency is not `done`, mark the feature `blocked` and stop.
