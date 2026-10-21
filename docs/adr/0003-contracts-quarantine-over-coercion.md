# ADR-0003 — Fail loudly: data contracts + quarantine instead of silent coercion

- **Status:** accepted
- **Date:** 2026-10-21
- **Deciders:** human
- **Related:** `docs/plan/F03-quality-contracts.md`, `CONTEXT.md` invariants 1–2

## Context
Supplier feeds are inconsistent and often wrong. The tempting shortcut is to coerce values
(parse what we can, default the rest, drop unparseable rows) so the pipeline "always succeeds".
That hides defects, makes quality unmeasurable, and lets bad products reach search — the exact
failure the project exists to prevent.

## Decision
Declare expectations per supplier in a YAML **data contract** (required fields, types, ranges,
allowed values, units, thresholds). Validate every bronze row against it. Rows that pass go to
**silver**; rows that fail go to a **quarantine** table carrying a `reason_code` from a closed
set, the offending field, and the original payload. Enforce the invariant
`bronze = silver + quarantine` exactly. Never drop or silently coerce.

## Consequences
- **Positive:** failures are visible and countable; quality has a per-supplier score and trend;
  quarantined rows are recoverable; contracts are the single source of thresholds and double as
  documentation of each feed.
- **Negative / trade-offs:** more upfront modeling per feed; strict contracts can quarantine a
  lot at first (this is the point, and F05/F06 exist to raise the pass rate); reason codes must
  be kept in sync with `CONTEXT.md` (guarded by a test).
- **Follow-ups:** F04 reports quarantine rates and trends; F05/F06 reduce legitimate
  quarantines via normalization and validated enrichment, not by loosening contracts.

## Alternatives considered
- **Best-effort coercion with logging** — silently changes data; logs are not queryable artifact
  and rarely reviewed; violates invariant 2.
- **Reject-and-drop bad rows** — loses recoverable data and hides supplier quality problems.
- **Great Expectations / Dataplex as the primary mechanism** — more powerful, but heavier to run
  offline; the contract + `reason_code` model keeps the demo self-contained while mapping
  cleanly to those tools in production.
