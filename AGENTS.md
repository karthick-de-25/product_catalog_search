# AGENTS.md — Product Catalog Intelligence Platform

This file is the operating contract for AI coding agents (Pi, Claude Code, Cursor, Codex, …)
working in this repository. Read it fully before doing anything.

> Human-facing overview lives in [`README.md`](./README.md).
> Domain context lives in [`CONTEXT.md`](./CONTEXT.md).
> Delivery plan lives in [`docs/plan/ROADMAP.md`](./docs/plan/ROADMAP.md).

---

## 1. What we are building

An end-to-end data platform that turns messy multi-supplier product feeds into a clean,
enriched, searchable catalog. Local-first (DuckDB + Parquet) with **AlloyDB for PostgreSQL**
on GCP as the only cloud component, powering hybrid (vector + keyword) search and a grounded
RAG assistant.

**Stack:** Python 3.11+ · DuckDB · Pandas/PyArrow · Pandera · YAML data contracts ·
Gemini + Vertex AI embeddings · AlloyDB (`vector`, `alloydb_scann`, `google_ml_integration`,
`pg_trgm`) · Streamlit · pytest + ruff + mypy.

---

## 2. Golden rules (non-negotiable)

1. **Plan before code.** No feature work without an approved plan file in `docs/plan/`.
   Use the `plan` skill. Get explicit human approval. Then use the `implement` skill.
2. **Vertical slices only.** Every change must leave the repo in a runnable, tested state.
   Never land "half a layer". A slice goes from input to observable output.
3. **Fail loudly, never silently.** Bad data goes to `quarantine` with a `reason_code`.
   No bare `except: pass`. No dropping rows without recording why.
4. **Everything is testable offline.** The core pipeline must run with no GCP credentials
   and no network. Cloud code is isolated behind an adapter and guarded by config flags.
5. **Determinism first.** Random data generation, IDs, and fixtures use a fixed seed.
   Tests must not depend on wall-clock time or ordering of unordered collections.
6. **Small, reviewable steps.** Prefer many small commits over one large one. One slice =
   one logical change set.
7. **Evidence over claims.** "Done" means tests/lint/type checks passed and you can show the
   command output. See §7.
8. **Stop for critical changes.** Follow the approval policy in §5 exactly. When in doubt,
   ask — a wrong guess about cloud resources or schema costs real money and time.
9. **Never commit secrets.** `.env` is git-ignored. Use `.env.example` for documentation.
10. **Update the plan as you go.** Tick slice checkboxes and append to the plan's log.

---

## 3. The delivery loop

```
        ┌──────────────────────────────────────────────────────────────┐
        │                    HUMAN (approval gates)                    │
        │   ✋ approve plan      ✋ approve critical change               │
        └───────────────▲──────────────────────────────▲───────────────┘
                        │                              │
   ┌────────────────────┴───────┐          ┌───────────┴───────────────┐
   │ 1. PLAN                    │          │ 3. IMPLEMENT               │
   │  /skill:plan <feature-id>  │  ──────► │  /skill:implement F0x      │
   │  → writes docs/plan/FNN-*.md│  approve │  slice → test → commit     │
   │  → STOPS for approval       │          │  only stops on critical    │
   └────────────────────────────┘          └───────────┬───────────────┘
                                                        │
                                            ┌───────────▼───────────────┐
                                            │ 4. VERIFY                  │
                                            │  /skill:verify F0x         │
                                            │  → make check, evidence    │
                                            └───────────┬───────────────┘
                                                        │
                                            ┌───────────▼───────────────┐
                                            │ 5. UPDATE ROADMAP + next   │
                                            └───────────────────────────┘
```

Rules of the loop:

- **Plan approval is the primary gate.** Once a plan is approved, implement the whole feature
  slice-by-slice without asking for per-slice approval — *except* for critical changes (§5).
- One feature at a time. Do not start `F05` while `F03` is `in-progress` unless the plan says
  they are independent and the human approves.
- If reality diverges from the plan (missing assumption, new dependency, blocked by a
  contract), **stop and amend the plan** — do not silently expand scope.

### Agent skills

| Skill | Command | Purpose |
|---|---|---|
| `plan` | `/skill:plan F03` | Scout repo, write/refresh the feature plan, request approval. Never edits `src/`. |
| `implement` | `/skill:implement F03` | Execute an *approved* plan, slice by slice, with tests. |
| `verify` | `/skill:verify F03` | Run the full check suite, validate acceptance criteria, produce an evidence report. |
| `status` | `/skill:status` | Summarize roadmap progress, blockers, and the next slice. |

Skills live in [`.pi/skills/`](./.pi/skills). Subagents live in [`.pi/agents/`](./.pi/agents).

---

## 4. Feature & slice model

- A **feature** is a vertical capability with its own plan file: `docs/plan/FNN-slug.md`.
- A **slice** is the smallest end-to-end increment of that feature (input → output → test).
- Features are tracked in [`docs/plan/ROADMAP.md`](./docs/plan/ROADMAP.md) with status:
  `todo · planned · approved · in-progress · done · blocked`.
- A feature is **done** only when every slice is checked, `make check` is green, and the
  acceptance criteria in the plan are demonstrably met.

Ordering: features are numbered by dependency. `F09`–`F10` (AlloyDB) require human-approved
GCP setup; everything before them is local and free.

---

## 5. Approval policy

Three tiers. Apply the **highest** tier that matches any part of the action.

### 🔴 TIER C — Critical: STOP and get explicit human approval

Do not proceed until the human says yes in this conversation. Ask a concrete question with
the exact command/change and its cost/blast radius.

- **Cloud & cost**
  - Any `gcloud` command, enabling APIs, creating/modifying/deleting AlloyDB clusters,
    instances, or IAM bindings.
  - Running `alloydb-auth-proxy` or executing **any** SQL that writes to AlloyDB.
  - Bulk Vertex AI / Gemini jobs that incur material cost (e.g. embedding >1k rows,
    extracting attributes for the full catalog).
- **Destructive**
  - `DROP`, `TRUNCATE`, `DELETE` without a `WHERE` on shared tables; deleting `data/` or
    `contracts/`; `rm -rf`; `git push --force`; rewriting git history.
- **Secrets & security**
  - Editing `.env`, adding credentials, changing auth, changing row-level security.
- **Contracts & interfaces (breaking)**
  - Breaking changes to `contracts/*.yaml`, the canonical product schema, the AlloyDB
    schema, or a public function/CLI signature other slices depend on.
  - Changing the workflow in this file, the skills, or the approval policy.
- **Scope**
  - Adding a feature that is not in the roadmap, or changing a plan's acceptance criteria.
  - Adding/removing dependencies, or major version upgrades.

### 🟡 TIER B — Proceed, but announce in the plan log

- Adding a *new* helper module / internal function within the approved plan.
- Non-breaking additive changes (new optional column in silver/gold, new rule category).
- Introducing a new dev-only tool or test fixture.
- Refactors that keep all tests green and touch ≤3 files.

Record a one-line entry in the plan's `## Log` section, then continue.

### 🟢 TIER A — Autonomous

- Writing/editing code and tests inside the approved plan's scope.
- Formatting, lint fixes, type annotations, docstrings, comments.
- Generating synthetic local data (`make data`) with fixed seeds.
- Running local commands: `pytest`, `ruff`, `mypy`, `duckdb`, `make check`.
- Reading files, searching, running read-only shell commands.
- Updating `docs/plan/` checkboxes and logs.

> If an action is genuinely ambiguous between tiers, treat it as Tier C.

---

## 6. Repository layout

```
.
├── AGENTS.md                 # ← you are here (agent contract)
├── CONTEXT.md                # domain glossary & invariants
├── README.md                 # human overview
├── Makefile                  # single entry point for all tasks
├── requirements.txt / requirements-dev.txt
├── .env.example              # documented config (never real secrets)
├── .pi/
│   ├── settings.json         # project settings (skills, subagent scope)
│   ├── agents/               # scout · planner · worker · reviewer
│   └── skills/               # plan · implement · verify · status
├── contracts/                # YAML data contracts per supplier feed
├── data/                     # generated artifacts (git-ignored except .gitkeep)
│   ├── raw/  silver/  gold/  docs/  quarantine/  reports/
├── sql/                      # AlloyDB DDL, indexes, hybrid search, RLS
├── src/
│   ├── config.py             # typed settings from env
│   ├── generate/             # synthetic dirty supplier feeds
│   ├── ingest/               # raw → DuckDB bronze
│   ├── quality/              # profile · validate · quarantine · scorecard
│   ├── enrichment/           # normalize · extract (Gemini) · dedupe
│   ├── load/                 # gold → AlloyDB + embeddings
│   ├── search/               # query routing + hybrid RRF
│   ├── rag/                  # doc ingestion + grounded answers
│   ├── eval/                 # golden queries + metrics
│   └── app/                  # Streamlit
├── tests/                    # unit + slice-level + golden fixtures
│   └── fixtures/             # tiny committed sample data
└── docs/
    ├── plan/                 # ROADMAP.md, TEMPLATE.md, FNN-*.md
    ├── adr/                  # architecture decision records
    └── agents/               # how the agent skills/subagents are wired (README.md)
```

**Layering rule:** `generate → ingest → quality → enrichment → load/search/rag → app`.
Lower layers never import from higher layers. `src/config.py` is importable everywhere.
Cloud I/O lives only in `src/load/` and `src/rag/` behind flags.

---

## 7. Definition of Done

A slice is done when **all** of the following hold:

- [ ] Code implements the slice's stated input → output behaviour.
- [ ] At least one test covers the happy path; edge cases from the plan are covered or explicitly listed as out of scope.
- [ ] `make check` passes (ruff + mypy + pytest) — paste the tail of the output.
- [ ] No new secrets, no new cloud calls, no git-ignored artifacts committed.
- [ ] Docstrings on public functions; `CONTEXT.md`/plan updated if a concept or invariant changed.
- [ ] Plan slice checkbox ticked and a line appended to the plan `## Log`.

A feature is done when all its slices are done **and** `/skill:verify FNN` reports PASS with
the acceptance criteria table filled in.

---

## 8. Commands

```bash
# setup (one-time)
uv venv && uv pip install -r requirements.txt -r requirements-dev.txt

# the everyday loop
make check          # ruff check + ruff format --check + mypy + pytest
make test           # pytest only
make fmt            # ruff format + ruff check --fix
make data           # generate synthetic dirty supplier feeds
make ingest         # raw → DuckDB bronze
make quality        # profile + validate + quarantine + scorecard
make enrich         # normalize + Gemini extraction + dedupe
make gold           # materialize the canonical catalog
make db             # create AlloyDB schema/extensions/indexes   (🔴 Tier C)
make load           # gold → AlloyDB                             (🔴 Tier C)
make embed          # generate embeddings in AlloyDB             (🔴 Tier C)
make eval           # compare keyword vs vector vs hybrid
make app            # launch Streamlit
```

Notes:

- Prefer `uv` when present, fall back to `python -m venv` + `pip`.
- `make check` must never require GCP credentials. Cloud smoke tests are separate and
  opt-in via `RUN_CLOUD_TESTS=1`.
- If a `make` target does not exist yet, it belongs to a future feature — do not stub it
  silently; check the roadmap.

---

## 9. Coding conventions

- **Python:** 3.11+ syntax, full type hints on public functions, `pathlib` over `os.path`,
  `pydantic`/`dataclasses` for structured config, no mutable default arguments.
- **Naming:** `snake_case` functions/vars, `PascalCase` classes, `UPPER_SNAKE` constants.
  Tables: `bronze_*`, `silver_*`, `gold_*` in DuckDB; `products`, `doc_chunks` in AlloyDB.
- **Errors:** raise specific exceptions with context; never swallow. Data problems carry a
  `reason_code` (see `CONTEXT.md`).
- **SQL:** lowercase keywords, explicit column lists (no `SELECT *` in committed queries),
  schema-qualified names, comments on governance-relevant columns.
- **Config:** every tunable comes from `src/config.py` (env-backed). No magic numbers in
  business logic; put thresholds in contracts or config.
- **Tests:** `tests/` mirrors `src/`. Use `tests/fixtures/` tiny datasets. Mark slow/cloud
  tests with `@pytest.mark.slow` / `@pytest.mark.cloud`.
- **Logging:** structured `logging`, module-level logger, no `print` in `src/`.

---

## 10. Working with data

- Never commit anything under `data/` except `.gitkeep`. Regenerate via `make data`.
- Synthetic data must be **seeded** and reproducible; document the seed in the generator.
- PDFs/docs used by RAG live in `data/docs/` (git-ignored); commit only tiny fixtures in
  `tests/fixtures/`.
- Treat every supplier feed as untrusted: validate before use, quarantine on failure.
- PII/sensitive columns must be flagged in `sql/` comments and covered by row-level security.

---

## 11. When you are unsure

1. Re-read the approved plan file — the answer is usually there.
2. Check `CONTEXT.md` for domain meaning and invariants.
3. Check `docs/adr/` for prior decisions.
4. If still unclear, **stop and ask the human**. Do not guess on cloud, schema, cost, or scope.
5. Prefer the smallest reversible action.

---

## 12. Skills & subagents

- **Skills** (`.pi/skills/`) are the canonical workflows. Use `/skill:plan`, `/skill:implement`,
  `/skill:verify`, `/skill:status`. They encode this file's rules; do not bypass them.
- **Subagents** (`.pi/agents/`): `scout` (read-only recon), `planner` (writes plans),
  `worker` (implements one slice), `reviewer` (read-only review). Invoke with
  `agentScope: "both"` so project agents load. Prefer delegation for large recon or review
  tasks to keep the main context small.
- Editing a skill or this file is a **Tier C** change.
