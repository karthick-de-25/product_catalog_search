# Agent setup — how this repo is wired for AI coding agents

This directory documents the agent workflow. The binding contract is
[`AGENTS.md`](../../AGENTS.md) at the repo root; this file is the map.

## Files

| Path | Purpose |
|---|---|
| `AGENTS.md` | Binding rules: golden rules, approval policy, conventions, DoD. **Read first.** |
| `CONTEXT.md` | Domain glossary, canonical product model, invariants, reason codes. |
| `.pi/settings.json` | Project settings (enables skill commands and `.pi/skills`). |
| `.pi/skills/plan/` | `/skill:plan FNN` — write/refresh a feature plan, stop for approval. |
| `.pi/skills/implement/` | `/skill:implement FNN` — execute an approved plan, slice by slice. |
| `.pi/skills/verify/` | `/skill:verify FNN` — reproduce evidence, grade acceptance criteria. |
| `.pi/skills/status/` | `/skill:status` — roadmap snapshot and next action. |
| `.pi/agents/` | Subagents: `scout`, `planner`, `worker`, `reviewer`. |
| `docs/plan/ROADMAP.md` | Delivery order, feature statuses, slice outlines. |
| `docs/plan/TEMPLATE.md` | The plan file template used by the `plan` skill. |
| `docs/plan/FNN-*.md` | Per-feature plans (status: proposed → approved → in-progress → done). |
| `docs/adr/` | Architecture decision records. |
| `AGENTS.override.md` | (optional) local, uncommitted overrides for a specific machine. |

## Why project-local

Project resources load only when the project is trusted. Trust it once with `/trust` (interactive)
or pass `--approve` non-interactively. Subagents that must see `.pi/agents/` need
`agentScope: "both"` on the `subagent` tool call — the skills do this for you.

## The loop in one line

```
/skill:plan FNN  →  human: "approve FNN"  →  /skill:implement FNN  →  /skill:verify FNN
```

## Approval policy in one line

🟢 code/tests/docs inside an approved plan → just do it ·
🟡 additive/internal changes → announce in the plan log ·
🔴 cloud, cost, destructive, secrets, breaking contracts/interfaces, new deps, scope → **stop and ask**.

Full detail: [`AGENTS.md` §5](../../AGENTS.md).

## Maintaining this setup

- Editing a skill, `AGENTS.md`, `CONTEXT.md` invariants, or the approval policy is **Tier C**.
- After changing a skill, reload it (`/skill:name`) — skills are discovered fresh each session.
- Keep `ROADMAP.md` and plan files in sync; `/skill:status` reports drift.
