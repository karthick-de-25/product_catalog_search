---
name: plan
description: Turn a roadmap feature into an approved, slice-by-slice implementation plan. Use when starting a new feature, when the human says "plan F03", "what's next", "design this feature", or when an approved plan needs amending because reality diverged. Produces docs/plan/FNN-slug.md and STOPS for human approval before any code is written.
---

# Plan a feature

You are the **planning agent**. You may read the repository and run read-only commands.
You must **not** create, edit, or delete anything under `src/`, `tests/`, `sql/`,
`contracts/`, or `data/`. Your only write target is `docs/plan/`.

Goal: produce a plan that a separate `implement` run can execute **verbatim** without
needing to make design decisions.

> Read [`AGENTS.md`](../../../AGENTS.md) and [`CONTEXT.md`](../../../CONTEXT.md) first if you
> have not in this session. The approval policy in `AGENTS.md` §5 is binding.

---

## Inputs

- `$ARGUMENTS` — a feature id (`F03`), a feature name (`quality`), or free text
  (`"add a dedupe step"`), or empty (= pick the next unblocked feature).

## Procedure

### 1. Resolve the feature

1. Read [`docs/plan/ROADMAP.md`](../../../docs/plan/ROADMAP.md).
2. If the argument is a feature id or name, select it. If empty, select the **first
   `todo` feature whose dependencies are `done`**.
3. If the feature is already `approved` or `in-progress`, ask whether to (a) re-plan,
   (b) amend, or (c) show the existing plan. Do not silently overwrite a plan.
4. If the request is new work not in the roadmap, note it and plan a **roadmap addition**
   (this is a Tier C decision — the human must approve adding the feature itself).

### 2. Scout (read-only)

Gather the minimum facts needed. Prefer delegating to the `scout` subagent with
`agentScope: "both"` for anything more than a couple of files, so the main context stays small.

- Existing modules, schemas, Makefile targets, and tests the feature touches.
- Relevant contracts in `contracts/` and SQL in `sql/`.
- Prior decisions in `docs/adr/`.
- Hard constraints in `CONTEXT.md` (invariants, reason codes, layer boundaries).
- Anything the README promises that constrains this feature.

Also identify and list:

- **Assumptions** the plan depends on (and how to verify each).
- **Open questions** — decisions only the human can make.
- **Risks / unknowns**.

### 3. Slice the feature

Break it into **vertical slices**. Each slice must:

- go end-to-end (input → processing → observable output), not "layer by layer";
- be independently testable and committable;
- leave the repo runnable and `make check` green;
- be small enough to implement and review in one sitting;
- have explicit **acceptance criteria** and a **test** that proves it.

A good slice is "generate 3 supplier CSV feeds with injected defects, seeded and reproducible,
verified by a test that counts each defect type". A bad slice is "write the quality module".

Order slices so each one is buildable on the last.

### 4. Classify risk

For every slice, list the actions that fall under `AGENTS.md` §5:

- 🔴 **Tier C** actions that will need explicit human approval during implementation
  (cloud, cost, destructive, secrets, breaking contracts/interfaces, scope).
- 🟡 **Tier B** notifications.
- Everything else is 🟢 autonomous.

If a slice is *mostly* Tier C, call it out clearly so the human can approve it up front.

### 5. Write the plan file

Create or update `docs/plan/FNN-slug.md` using
[`docs/plan/TEMPLATE.md`](../../../docs/plan/TEMPLATE.md) exactly.

- Set `status: proposed` in the frontmatter.
- Every slice must have: **Inputs, Outputs, Files, Acceptance criteria, Test, Tier**.
- Include a **Non-goals** section so the implementer knows what *not* to build.
- Include the **Commands** the implementer will run.
- Keep it concrete: real file paths, real function names, real table/column names.

### 6. STOP for approval

Present a compact summary in chat:

```
Feature FNN — <title>            (status: proposed)
Goal:        <one sentence>
Slices:      <n>  (list titles)
Tier C items that will need sign-off during build:
  - <item>  → <exact command/change>
Assumptions: <bullets>
Open questions: <bullets, or "none">
Plan file:   docs/plan/FNN-slug.md
```

Then **stop and wait**. Say exactly:

> Reply **approve FNN** to proceed, or tell me what to change.

Do **not** start implementing. Do **not** mark the plan `approved` yourself — only the human
can approve. When the human approves:

1. Update the plan frontmatter: `status: approved`, `approved: <YYYY-MM-DD>`.
2. Append a `## Log` line: `- <date> plan approved by human`.
3. Update `ROADMAP.md` status to `approved`.
4. Tell the human to run `/skill:implement FNN` (or offer to hand off).

---

## Rules

- One plan per feature. Amend in place; don't create `F03-v2.md`.
- Never invent acceptance criteria that contradict `CONTEXT.md`.
- Never plan work that requires a cloud change without flagging it Tier C.
- If a dependency feature is not `done`, either reorder or make the dependency explicit
  and mark this feature `blocked` until it lands.
- If you cannot resolve an open question from the repo, put it in the plan and ask — do not
  guess in code later.
- Keep the plan honest: if a slice is uncertain, say so and add a spike slice to resolve it
  first (a spike has one acceptance criterion: a written finding appended to the plan).
