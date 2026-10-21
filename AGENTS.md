# AGENTS.md — Product Catalog Intelligence Platform

Operating contract for AI coding agents (Pi, Claude Code, Cursor, …). Read fully before working.

> Human overview: [`README.md`](./README.md) · Domain: [`CONTEXT.md`](./CONTEXT.md) ·
> Delivery: [`docs/plan/ROADMAP.md`](./docs/plan/ROADMAP.md)

---

## 1. What we are building

A **demo** pipeline that turns messy multi-supplier product feeds into a clean catalog and serves
**hybrid search** (vector + keyword) from AlloyDB.

**Core = data quality + hybrid search. Nothing else is required for round 1.**
Optional extras (scorecard, LLM extraction, dedupe, eval, RAG, feedback) live in
[`docs/plan/OPTIONAL.md`](./docs/plan/OPTIONAL.md).

**Stack:** Python 3.11+ · DuckDB · pandas · AlloyDB (pgvector/ScaNN + tsvector/pg_trgm) ·
Gemini embeddings · Streamlit · pytest + ruff (+ optional mypy).

---

## 2. Principles

1. **Plan, then implement.** No code without an approved plan in `docs/plan/`. Use `/skill:plan`,
   get approval, then `/skill:implement`.
2. **Vertical slices.** Each slice goes input → output, leaves the repo runnable, and has **one
   small happy-path test**. Keep features to **≤3 slices**.
3. **Fail loudly.** Bad rows go to `quarantine` with a `reason_code`. Never drop rows silently.
   No bare `except: pass`.
4. **Local-first and offline.** Tests run with no GCP credentials and no network. Cloud code
   (AlloyDB) is opt-in and isolated behind config flags.
5. **Simple over complete.** Prefer the smallest thing that demonstrates the core. Deleting
   complexity is a valid change. Don't build for scale or for hypothetical needs.
6. **One test per slice** (the happy path). Skip exhaustive edge cases in round 1.
7. **Stop only for critical changes** (§4). Otherwise implement the whole approved plan without
   per-slice approval.
8. **Never commit secrets.** `.env` is git-ignored; `data/` is git-ignored.

---

## 3. The loop

```
/skill:plan FNN  →  human: "approve FNN"  →  /skill:implement FNN  →  done
```

- Plan approval is the only gate. After approval, implement every slice and run `make check`.
- One feature at a time. If reality diverges from the plan, stop and amend the plan.
- `/skill:status` prints a one-screen roadmap snapshot.

Skills live in [`.pi/skills/`](./.pi/skills). Subagents live in [`.pi/agents/`](./.pi/agents).

---

## 4. Approval: critical changes only

**STOP and ask the human** for any of these (state the exact command and its cost/blast radius):

- **Cloud & cost:** any `gcloud` command, AlloyDB create/modify/delete, IAM changes, running
  `alloydb-auth-proxy`, any SQL that writes to AlloyDB, bulk Gemini/Vertex jobs.
- **Destructive:** `DROP`/`TRUNCATE`/`DELETE` without `WHERE`, deleting `data/` or `contracts/`,
  `rm -rf`, `git push --force`, rewriting git history.
- **Secrets & security:** editing `.env`, adding credentials, changing auth or row-level security.
- **Scope & interfaces:** adding a feature not on the roadmap, changing a plan's acceptance
  criteria, breaking changes to `contracts/*.yaml`, the canonical schema, the AlloyDB schema, or
  a public function/CLI signature, adding/removing dependencies.

**Everything else is autonomous** — writing code, tests, and docs inside the approved plan,
formatting/lint fixes, `make data`, local DuckDB work, running `make check`, updating plan
checkboxes. Note anything surprising in the plan's `## Log`.

---

## 5. Testing policy (keep it light)

- **One focused test per slice**, covering the happy path. That is the bar for round 1.
- **Do not** write tests for trivial glue, framework behaviour, config parsing permutations,
  socket isolation, or exhaustive edge cases.
- Tests use tiny committed fixtures (`tests/fixtures/`) and must be offline and fast.
- `make check` = `ruff check` + `pytest`. `mypy` is available as an optional target
  (`make typecheck`) and must not gate a slice.
- "Done" for a slice = code + one test + `make check` green + plan checkbox ticked.

---

## 6. Repository layout

```
.
├── AGENTS.md · CONTEXT.md · README.md · Makefile · pyproject.toml
├── requirements.txt / requirements-dev.txt
├── .env.example                 # documented config (never real secrets)
├── .pi/{settings.json, agents/, skills/}
├── contracts/                   # YAML data contracts per supplier feed
├── data/                        # git-ignored artifacts (raw/ silver/ gold/ quarantine/ reports/)
├── sql/                         # AlloyDB DDL, indexes, hybrid search
├── src/
│   ├── config.py                # typed settings from env
│   ├── errors.py                # shared errors + reason codes
│   ├── logging_utils.py
│   ├── generate/                # synthetic dirty supplier feeds
│   ├── ingest/                  # raw → DuckDB bronze
│   ├── quality/                 # contract · validate · quarantine
│   ├── enrichment/              # normalize → gold
│   ├── load/                    # gold → AlloyDB + embeddings
│   ├── search/                  # query routing + hybrid RRF
│   └── app/                     # Streamlit
├── tests/                       # one focused test per slice
└── docs/{plan/, adr/, agents/}
```

**Layering:** `generate → ingest → quality → enrichment → load/search → app`. Lower layers never
import from higher layers. Cloud I/O lives only in `src/load/` behind a config flag.

---

## 7. Commands

```bash
make setup     # create .venv + install deps
make check     # ruff + pytest  (the gate)
make fmt       # ruff format + fix
make data      # generate dirty supplier feeds
make ingest    # raw → DuckDB bronze
make quality   # validate → silver + quarantine
make gold      # build clean catalog
make db        # AlloyDB schema/indexes      (🔴 critical)
make load      # gold → AlloyDB + embeddings (🔴 critical)
make app       # Streamlit demo
```

`make check` never requires GCP credentials. If a target does not exist yet, it belongs to a
future feature — do not add silent stubs.

---

## 8. Conventions

- Type hints on public functions; `pathlib` over `os.path`; no mutable default arguments.
- `snake_case` functions, `PascalCase` classes, `UPPER_SNAKE` constants.
- Tables: `bronze_*`, `silver_*`, `gold_*` in DuckDB; `products`, `doc_chunks` in AlloyDB.
- Config in `src/config.py`; no magic numbers in business logic.
- Tests mirror `src/`. No `print` in `src/` except CLI entry points.

---

## 9. When unsure

1. Read the approved plan. 2. Check `CONTEXT.md`. 3. Check `docs/adr/`.
4. Still unsure → **stop and ask**. Never guess on cloud, cost, schema, or scope.
5. Prefer the smallest, most reversible action.
