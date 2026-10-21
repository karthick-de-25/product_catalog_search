# CONTEXT.md — Domain model & invariants

Shared vocabulary. If code and this file disagree, this file wins. Changing an invariant here is
a critical (approval-required) change per `AGENTS.md` §4.

This is a **demo**, so keep the model deliberately small.

---

## The problem

Suppliers send product feeds with different schemas, units, and completeness. Contractors search
with vague phrases (*"3/4 inch brass ball valve lead free"*) or paste part numbers. Bad data means
bad search. We clean and enrich the catalog, then serve **hybrid search** (semantic + keyword).

---

## Glossary

| Term | Meaning |
|---|---|
| **Feed** | One supplier's product data (CSV, JSON, or XML). |
| **Product** | A sellable item identified by `sku`. |
| **Bronze** | Raw, as-ingested rows. Immutable. |
| **Silver** | Rows that passed quality checks. |
| **Gold** | The clean, searchable catalog loaded into AlloyDB. |
| **Quarantine** | Rows that failed validation, with a `reason_code`. |
| **Data contract** | YAML declaring a feed's required fields, types, ranges. |
| **Reason code** | Machine-readable tag explaining why a row was quarantined. |
| **Hybrid search** | Vector + keyword results fused with Reciprocal Rank Fusion (RRF). |
| **RRF** | `Σ 1/(k + rank)`, default `k = 60`. |

---

## Canonical product model (gold)

| Field | Type | Notes |
|---|---|---|
| `sku` | str | Unique, required. Trimmed, uppercased. |
| `supplier_id` | str | Required. |
| `name` | str | Required. |
| `description` | str | Optional long text (used for embeddings). |
| `brand` | str | Normalized. |
| `category` | str | From the controlled taxonomy. |
| `size_in` | float | Canonical unit: **inches**. |
| `material` | str | Lowercase. |
| `pressure_psi` | int | Canonical unit: **PSI**. |
| `lead_free` | bool | `null` when unknown — never defaulted to `false`. |
| `search_text` | str | Concatenation used for embeddings + `tsvector`. |
| `embedding` | vector(768) | Generated in AlloyDB via Vertex AI. |

---

## Invariants

1. **Bronze is immutable.** Corrections happen in silver/gold.
2. **No silent data loss.** `bronze_rows = silver_rows + quarantine_rows`, exactly. Every bad
   row carries a `reason_code`.
3. **`sku` is unique in gold.**
4. **Canonical units in silver and gold:** length in inches, pressure in PSI. Originals are kept
   in `raw_*` fields.
5. **Unknown ≠ false.** Missing booleans are `null`.
6. **Search never returns quarantined products.**
7. **Cloud is opt-in.** Nothing calls GCP unless a config flag enables it.

---

## Reason codes (closed set)

Changing this list is a critical change.

| Code | Meaning |
|---|---|
| `MISSING_REQUIRED` | A required field is null/empty. |
| `TYPE_MISMATCH` | Value cannot be parsed as the declared type. |
| `OUT_OF_RANGE` | Numeric value outside the contract's min/max. |
| `DUPLICATE_SKU` | SKU already seen in this run. |

---

## Non-goals (round 1)

- Streaming ingestion, pricing/inventory freshness, multi-tenant auth.
- LLM attribute extraction, deduplication, RAG, scorecards — all **optional**
  ([`docs/plan/OPTIONAL.md`](./docs/plan/OPTIONAL.md)).
- Production scale, CI/CD, Terraform.
