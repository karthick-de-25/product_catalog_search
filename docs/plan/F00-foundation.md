---
feature: F00
title: Foundation & dev environment
status: done
owner: agent
approved: 2026-10-21
created: 2026-10-21
updated: 2026-10-21
depends_on: []
---

# F00 — Foundation & dev environment

## Goal
A typed, tested Python project skeleton with a single `make check` gate, so every later
feature lands on a green, reproducible baseline.

## Why now
Every other feature depends on config, logging, shared errors/reason codes, and a working
lint/type/test loop. Getting this right first prevents rework and keeps slices small.

## Scope
- In scope: `pyproject.toml` tool config, `src/` package skeleton, `src/config.py`,
  `src/logging_utils.py`, `src/errors.py` (with the closed `ReasonCode` enum), `tests/`
  harness, `Makefile` dev targets.
- Non-goals: any pipeline/business logic (generation, ingestion, quality, enrichment,
  search, RAG), any AlloyDB/GCP wiring, any dependency beyond dev tooling.

## Bootstrap (one-time, before Slice 1)

Scout verified this environment (2026-10-21): `Python 3.12.3`, `uv 0.12.1`, no `.venv`,
`ruff`/`mypy` **not on the system PATH**, and a bare system `pytest` without our plugins.
Therefore **every command in this feature runs inside `.venv`**, created once by:

```bash
uv venv .venv && uv pip install -r requirements.txt -r requirements-dev.txt
```

(or `make setup` once Slice 4 lands). Slices 1–3 use the raw commands because the Makefile
does not exist yet; from Slice 4 onward, "green" means `make check` is green.

## Already present (created during repo setup — verify, don't recreate)
- `.gitignore`, `.env.example`, `requirements.txt`, `requirements-dev.txt`
- `AGENTS.md`, `CONTEXT.md`, `docs/plan/*`, `.pi/*`
- `data/{raw,silver,gold,docs,quarantine,reports}/.gitkeep`, `tests/fixtures/.gitkeep`

## Assumptions
- [x] Python 3.11+ available — verified `Python 3.12.3`.
- [x] `uv` available — verified `uv 0.12.1`; fallback `python -m venv` + `pip`.
- [ ] Tool config in `pyproject.toml` is respected without an installable build backend —
      verify `ruff check` / `mypy src` / `pytest` run from the repo root in `.venv`.
- [ ] Tools run against `.venv` (not system) so `mypy` can resolve third-party types.
- [ ] `pytest` exits **5** (NO_TESTS_COLLECTED), not 0, when no tests exist; Slice 1 ships
      one trivial test so the gate is genuinely green.

## Open questions (needs human)
- none

## Acceptance criteria (feature-level)
- [ ] AC1: `make check` runs ruff + mypy + pytest and exits 0 on a clean tree.
- [ ] AC2: `python -m src.config` prints resolved, secret-redacted config and exits 0.
- [ ] AC3: `ReasonCode` matches the closed set in `CONTEXT.md` exactly (asserted by a test).
- [ ] AC4: No `src` module imports a cloud/app dependency (`google.cloud`, `google.genai`,
  `psycopg`, `streamlit`) at import time; asserted by a test (isolation guard).
- [ ] AC5: Importing any `src` module makes no network/cloud call.

---

## Slices

### Slice 1 — Package skeleton & tooling config
- **Status:** `[x]`
- **Tier:** 🟢
- **Inputs:** existing `requirements-dev.txt`, populated `.venv`
- **Outputs:** `pyproject.toml`, importable `src`, runnable pytest
- **Files:** `pyproject.toml`, `src/__init__.py`, `tests/__init__.py`, `tests/conftest.py`,
  `tests/test_package.py`
- **Acceptance criteria:**
  - [x] `pyproject.toml` configures ruff (line-length 100, target py311), mypy
        (`strict = true`, applied to `src`), pytest (`testpaths = ["tests"]`, markers `slow`,
        `cloud`, `integration`).
  - [x] `.venv/bin/python -c "import src"` succeeds from the repo root.
  - [x] `.venv/bin/ruff check .` exits 0 and `.venv/bin/mypy src` exits 0.
  - [x] `.venv/bin/pytest -q` exits 0 with the trivial import test below (zero tests would
        exit **5**, which is not green).
- **Test:** `tests/test_package.py::test_import_src` — asserts `import src` works.
- **Tier C actions:** none
- **Notes:** No `[build-system]` needed — this is an application, not a distributable package.
  `tests/conftest.py` may start empty; it exists so later fixtures have a home.

### Slice 2 — Typed configuration & logging
- **Status:** `[x]`
- **Tier:** 🟢
- **Inputs:** env vars documented in `.env.example`
- **Outputs:** `src/config.py` (`Settings` dataclass/pydantic model + `get_settings()`),
  `src/logging_utils.py` (`configure_logging`, module logger factory)
- **Files:** `src/config.py`, `src/logging_utils.py`, `tests/test_config.py`,
  `tests/test_logging_utils.py`
- **Acceptance criteria:**
  - [x] All config comes from env with documented defaults; no secrets hard-coded.
  - [x] Cloud features are off by default (`ENABLE_CLOUD=false`); `GCP_PROJECT` optional.
  - [x] A `redacted()` view hides secrets (e.g. `PGPASSWORD`) for logging.
  - [x] `python -m src.config` prints the redacted settings as JSON and exits 0.
  - [x] Missing required local paths do not raise at import time.
- **Test:** `tests/test_config.py::test_defaults_and_redaction` — defaults apply;
  `redacted()` masks the password; env override wins (via `monkeypatch`).
- **Tier C actions:** none
- **Notes:** Follow `CONTEXT.md` — cloud/network calls must be opt-in.

### Slice 3 — Shared errors & reason codes
- **Status:** `[x]`
- **Tier:** 🟢
- **Inputs:** `CONTEXT.md` "Reason codes" table
- **Outputs:** `src/errors.py` with `ReasonCode` (closed enum), `DataQualityError`,
  `ContractError`, `ConfigError`, and a `PipelineError` base
- **Files:** `src/errors.py`, `tests/test_errors.py`
- **Acceptance criteria:**
  - [x] `ReasonCode` values exactly match `CONTEXT.md` (8 codes) — no extras, none missing.
  - [x] Errors carry structured context (e.g. `sku`, `field`, `reason_code`).
  - [x] A test parses `CONTEXT.md` and asserts the enum matches (guards against drift).
- **Test:** `tests/test_errors.py::test_reason_codes_match_context` — parses `CONTEXT.md`.
- **Tier C actions:** none
- **Notes:** Reason codes are a closed set; changing them is Tier C.

### Slice 4 — Makefile dev loop
- **Status:** `[x]`
- **Tier:** 🟡
- **Inputs:** the tools configured in Slice 1
- **Outputs:** `Makefile` with `setup`, `fmt`, `lint`, `typecheck`, `test`, `check`, `clean`
- **Files:** `Makefile`, `README.md` (Development section)
- **Acceptance criteria:**
  - [x] `make check` = `ruff check .` + `ruff format --check .` + `mypy src` + `pytest -q`.
  - [x] Tools resolve to `.venv` (e.g. `PY := .venv/bin/python`), falling back to the system
        interpreter when `.venv` is absent so the target still works on a fresh clone.
  - [x] `make setup` creates `.venv` and installs both requirements files
        (`uv venv .venv && uv pip install -r requirements.txt -r requirements-dev.txt`),
        with a `python -m venv` + `pip` fallback.
  - [x] `make check` needs no GCP credentials and no network.
  - [x] `make clean` removes caches only (never `data/`); `.PHONY` declared.
- **Test:** `make check` exits 0 from the repo root.
- **Tier C actions:** none
- **Notes:** Do **not** add pipeline targets (`data`, `ingest`, `db`, …) yet — each future
  feature adds its own target. No silent no-op stubs.
  `PY` falls back to `python3`; targets that need installed tools fail fast through
  `require-venv` with a clear message (exit 2) instead of a confusing ImportError.
  Verification fix: `make setup` is idempotent — `uv venv --allow-existing` so re-running
  does not fail when `.venv` already exists (found during `/skill:verify F00`).

### Slice 5 — Baseline verification & docs
- **Status:** `[x]`
- **Tier:** 🟢
- **Inputs:** Slices 1–4
- **Outputs:** a smoke test, an import-isolation test, fixture scaffolding, updated roadmap
- **Files:** `tests/test_smoke.py`, `tests/test_isolation.py`, `tests/fixtures/.gitkeep`,
  `docs/plan/ROADMAP.md`
- **Acceptance criteria:**
  - [x] `get_settings()` returns documented defaults with an empty environment.
  - [x] Importing every `src` module opens no socket and imports no cloud/app dependency
        (satisfies AC4/AC5).
  - [x] `tests/fixtures/.gitkeep` exists; `data/` is git-ignored except `.gitkeep`s.
  - [x] `make check` green from a clean checkout.
- **Test:** `tests/test_smoke.py` + `tests/test_isolation.py`.
- **Tier C actions:** none
- **Notes:** Two test defects were found and fixed during this slice: `google.cloud` is a
  namespace package pre-registered by a `google-cloud-aiplatform` `.pth`, so the isolation
  test compares `sys.modules` before/after instead of globally; and replacing
  `socket.socket` breaks `ssl`, so outbound calls are blocked via a `sys.addaudithook`.
  Update ROADMAP F00 to `done` only after `/skill:verify F00` passes.

---

## Commands
```bash
# one-time bootstrap (before Slice 1; `make setup` exists from Slice 4)
uv venv .venv && uv pip install -r requirements.txt -r requirements-dev.txt

# the gate (raw commands for Slices 1–3, then `make check`)
.venv/bin/ruff check . && .venv/bin/ruff format --check . && .venv/bin/mypy src && .venv/bin/pytest -q
make check
.venv/bin/python -m src.config
```

## Risks
- `mypy --strict` may be noisy early → keep `src` small and typed from day one.
- Ruff/mypy version drift → pinned in `requirements-dev.txt`.
- Adding pipeline target stubs prematurely → explicitly forbidden above.

## Rollback
Revert `pyproject.toml`, `src/`, `tests/`, `Makefile`; nothing here is destructive or cloud-side.

---

## Log
- 2026-10-21 — plan created (proposed).
- 2026-10-21 — plan approved by human.
- 2026-10-21 — scouted environment (pre-approval); fixed two plan defects: tooling requires
  `.venv` (`ruff`/`mypy` absent from system PATH), and `pytest` exits 5 with zero tests, so
  Slice 1 ships one trivial test; tightened AC4 and Slice 4/5 acceptance criteria.
- 2026-10-21 — slice 1 "Package skeleton & tooling config": added `pyproject.toml`
  (ruff/mypy/pytest/pydantic plugin), `src/__init__.py`, `tests/` package + import test;
  `ruff check`, `ruff format --check`, `mypy src`, `pytest` all exit 0 (1 test).
- 2026-10-21 — slice 2 "Typed configuration & logging": `src/config.py` (pydantic-settings,
  cloud off by default, `redacted()`), `src/logging_utils.py` (idempotent `configure_logging`,
  `get_logger`); `python -m src.config` prints redacted JSON; all checks green (7 tests).
- 2026-10-21 — slice 3 "Shared errors & reason codes": `src/errors.py` (`ReasonCode` StrEnum,
  `PipelineError` + `ConfigError`/`ContractError`/`DataQualityError`), drift test parses
  `CONTEXT.md`; all checks green (12 tests).
- 2026-10-21 — [Tier B] slice 4 "Makefile dev loop": added `Makefile` (help/setup/fmt/lint/
  typecheck/test/check/clean, venv-aware with `require-venv` guard) and a README
  "Development (local, no cloud)" section; `make check` green (12 tests).
- 2026-10-21 — slice 5 "Baseline verification & docs": added `tests/test_smoke.py` and
  `tests/test_isolation.py`; verified fixtures tracked and `data/` ignored; `make check`
  green (18 tests). Ready for `/skill:verify F00`.
- 2026-10-21 — [Tier B] `/skill:verify F00` PASS with one gap fixed in scope: `make setup`
  was not repeatable (`uv venv` fails on an existing `.venv`); added `--allow-existing`.
  Re-ran `make setup` twice (both exit 0) and `make check` (18 passed). F00 marked done.

---

## Verification — F00 (2026-10-21)

- **AC1** `make check` → exit 0, 18 passed, ruff + format + mypy ✓
- **AC2** `python -m src.config` → exit 0; `PGPASSWORD=topsecret` renders `"pgpassword": "***"`
  (0 occurrences of the secret); env override `SEED=7` respected
- **AC3** ReasonCode vs `CONTEXT.md` → 8 == 8, equal (independently parsed)
- **AC4** no cloud/app dependency newly imported by `src` → test passes
- **AC5** no socket opened on import → test passes (audit hook subprocess)
- Adversarial: `SEED=not-an-int` fails loudly (exit 1, ValidationError); two `src.config`
  runs are byte-identical; no internal/forbidden imports in `src/`; `make clean` leaves
  `data/` intact; no secrets or non-placeholder `data/` files tracked.
