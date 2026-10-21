# CONTEXT.md — Domain model & invariants

Shared vocabulary for humans and agents. If code and this file disagree, **this file wins**
and the code is a bug. Propose edits to this file via the `plan` skill (Tier C if it changes
an invariant).

---

## The business problem

A PVF/HVAC/plumbing distributor aggregates product feeds from ~37,000 suppliers. Each supplier
uses different schemas, units, naming, and completeness. Contractors search with vague natural
language (*"3/4 inch brass ball valve lead free"*) or paste part numbers (sometimes with typos).
Dirty data → bad search → lost sales. The platform cleans, enriches, and indexes the catalog so
that **hybrid AI search** returns the right product.

---

## Glossary

| Term | Meaning |
|---|---|
| **Supplier feed** | One supplier's product data delivered as CSV, JSON, or XML. |
| **Product** | A sellable item, canonically identified by `sku`. |
| **SKU** | Stock Keeping Unit — the supplier's unique product identifier. |
| **Canonical model** | The single normalized product schema all feeds map to (see below). |
| **Bronze** | Raw, as-ingested data. Immutable. Never corrected in place. |
| **Silver** | Validated + normalized rows that passed quality checks. |
| **Gold** | The canonical, enriched, deduplicated catalog loaded into AlloyDB. |
| **Quarantine** | Rows that failed validation, stored with a `reason_code` and the original payload. |
| **Data contract** | A YAML file declaring a feed's required fields, types, allowed values, and thresholds. |
| **Completeness** | Fraction of required attributes present and valid. |
| **Reason code** | A stable machine-readable tag explaining why a row was quarantined or flagged. |
| **Review queue** | Low-confidence LLM-extracted attributes awaiting human confirmation. |
| **Hybrid search** | Combines semantic (vector) and keyword (full-text) results via Reciprocal Rank Fusion. |
| **RRF** | Reciprocal Rank Fusion: `Σ 1/(k + rank)` across result lists; `k = 60` by default. |
| **RAG** | Retrieval-Augmented Generation — retrieve evidence, then have Gemini answer with citations. |
| **Grounding** | The requirement that an answer is supported by retrieved evidence; otherwise refuse. |
| **Golden set** | ~50 labeled queries with known relevant SKUs, used to score search quality. |

---

## Canonical product model (gold)

| Field | Type | Notes |
|---|---|---|
| `sku` | str | Unique, required. Normalized to uppercase, trimmed. |
| `supplier_id` | str | Required. |
| `name` | str | Required, human-readable. |
| `description` | str | Optional long text (used for embeddings). |
| `brand` | str | Normalized against a brand alias table. |
| `category` | str | Mapped to the controlled taxonomy. |
| `size_in` | float | Canonical unit is **inches**. |
| `material` | str | Lowercase, from the allowed set. |
| `pressure_psi` | int | Canonical unit is **PSI**. |
| `lead_free` | bool | `true` only with evidence; unknown ⇒ `null`, never `false` by default. |
| `certifications` | list[str] | e.g. `NSF/ANSI 61`, `NSF/ANSI 372`. Normalized codes. |
| `search_text` | str | Concatenation used for embeddings + `tsvector`. |
| `embedding` | vector(768) | Generated in AlloyDB via Vertex AI `text-embedding-005`. |

---

## Invariants (must always hold)

1. **Bronze is immutable.** Corrections happen in silver/gold, never by editing bronze.
2. **No silent data loss.** Every dropped/quarantined row carries a `reason_code`; counts
   reconcile: `bronze_rows = silver_rows + quarantine_rows`.
3. **`sku` is unique in gold.** Deduplication resolves conflicts deterministically (see ADR-0003
   once written); the losing SKU is recorded, not erased.
4. **Units are canonical in silver and gold:** length in inches, pressure in PSI.
   Original values are preserved in a `raw_*` companion field/table.
5. **Unknown ≠ false.** Missing booleans are `null`. Only positive evidence sets `true`.
6. **LLM output is untrusted until validated.** Every extracted attribute is schema-validated
   and carries a confidence score. Below threshold → `review_queue`.
7. **Embeddings are derived.** They are recomputed when `search_text` changes; never hand-edited.
8. **Search never returns quarantined or unverified products.**
9. **RAG refuses when evidence is weak.** No answer without citations; out-of-scope → explicit refusal.
10. **Row counts and scorecards are logged per run** so trends are observable over time.

---

## Reason codes (quarantine / flags)

Keep this list closed; add new codes only via a plan change (Tier C).

| Code | Meaning |
|---|---|
| `MISSING_REQUIRED` | A contract-required field is null/empty. |
| `TYPE_MISMATCH` | Value cannot be parsed as the declared type. |
| `OUT_OF_RANGE` | Numeric value outside the contract's min/max. |
| `INVALID_ENUM` | Value not in the allowed set. |
| `DUPLICATE_SKU` | SKU already seen in this run. |
| `UNIT_UNPARSEABLE` | Size/pressure string could not be normalized. |
| `BROKEN_REFERENCE` | Links to a category/brand not in the taxonomy. |
| `LOW_CONFIDENCE` | LLM-extracted attribute below the confidence threshold. |

---

## Layer boundaries

```
generate → ingest(bronze) → quality(silver + quarantine) → enrichment → gold → AlloyDB → search/rag → app
```

- A layer may import from layers to its left, never to its right.
- `src/config.py` and `src/logging_utils.py` are shared and importable anywhere.
- Any network or cloud call must be opt-in via config (`ENABLE_*` flags), never implicit.

---

## Non-goals (for now)

- Real-time streaming ingestion (batch only).
- Pricing/inventory freshness (separate concern from catalog attributes).
- Multi-tenant UI, SSO, or production deployment (local Streamlit + dev AlloyDB).
- Training or fine-tuning models (we only call hosted Gemini/embeddings).
