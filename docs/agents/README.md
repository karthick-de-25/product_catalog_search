# Agent setup — how this repo is wired for AI coding agents

The binding contract is [`AGENTS.md`](../../AGENTS.md); this file is the map.

**Round-1 scope: data quality + hybrid search.** Everything else is optional
([`docs/plan/OPTIONAL.md`](../plan/OPTIONAL.md)).

## Files

| Path | Purpose |
|---|---|
| `AGENTS.md` | Rules: critical-only approval, light testing policy, conventions. |
| `CONTEXT.md` | Domain model, invariants, the 4 reason codes. |
| `.pi/settings.json` | Enables skill commands and loads `.pi/skills`. |
| `.pi/skills/plan/` | `/skill:plan FNN` — write a short plan, stop for approval. |
| `.pi/skills/implement/` | `/skill:implement FNN` — slice by slice, `make check`, stop only for critical changes. |
| `.pi/skills/status/` | `/skill:status` — roadmap snapshot + next command. |
| `.pi/agents/scout.md` | Read-only recon. |
| `.pi/agents/worker.md` | Implements one slice in an isolated context. |
| `docs/plan/ROADMAP.md` | Core features F00–F07 and their status. |
| `docs/plan/OPTIONAL.md` | Post-round-1 ideas (not required). |
| `docs/plan/TEMPLATE.md` | The short plan format. |
| `docs/adr/` | Architecture decision records. |

## The loop

```
/skill:plan FNN  →  human: "approve FNN"  →  /skill:implement FNN  →  done
```

There is **no separate verification step**: `implement` runs `make check` after every slice.

## Approval

🔴 **Ask first** for cloud/GCP, cost, destructive ops, secrets, and scope/contract/dependency
changes. 🟢 **Just do it** for code, tests, docs, and local data inside an approved plan.
Detail: [`AGENTS.md` §4](../../AGENTS.md).

## Keeping it simple (round 1)

- ≤3 vertical slices per feature, **one happy-path test each**.
- `make check` = `ruff` + `pytest`. `mypy` is optional (`make typecheck`) and never gates.
- No exhaustive edge-case suites, no socket/isolation tests, no scorecards unless asked.

## Project-local resources

Project skills/agents load only when the project is trusted (`/trust`, or `--approve`
non-interactively). Subagents need `agentScope: "both"` — the skills pass this for you.
