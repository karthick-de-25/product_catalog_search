# OPTIONAL — post-round-1 ideas

**Not required.** Build only after the core demo (F01–F07) is solid, and only with human approval
(adding a feature is a critical change per `AGENTS.md` §4). Each gets its own `ONN-*.md` plan.

- `O1` — done (see `O01-scorecard.md`).

## Recommended order (analysis, 2026-10-21; updated 2026-10-21)

Done: P0 keyword fix (F04), O1 scorecard. Remaining backlog, ranked by value/effort:

| Pri | Item | Status | Why | Cost |
|---|---|---|---|---|
| P1 | O4 Evaluation harness | todo | proves hybrid > keyword > vector with Recall@10 / MRR / NDCG on a fair baseline (P0 fixed) | offline |
| P2 | O3 Dedupe | todo | better catalog → better search + scorecards; do before final eval baseline | offline |
| P3 | O2 Gemini extraction | todo | close the README's enrichment gap (JSON-schema output, confidence, review queue) | medium, LLM $ |
| P3 | O5 RAG assistant | todo | biggest wow (citations + refusal); most effort, real Vertex AI usage | high |
| P4 | O6 Feedback | todo | only pays off once the demo is used repeatedly | low |

Quick win: add a `make demo` target (one command: data → ingest → quality → gold → scorecard).

## Ideas

| ID | Idea | Value | Rough shape | Status |
|---|---|---|---|---|
| O1 | Supplier quality scorecard | Per-supplier completeness/duplicate score + run trend | `src/quality/scorecard.py`, `supplier_scorecards` history table, `make scorecard` | ✅ done |
| O2 | Gemini attribute extraction | Pull size/material/certifications from free-text descriptions | JSON-schema output + confidence; low confidence → review queue | todo |
| O3 | Deduplication | Merge near-duplicate products (brand + category blocking + RapidFuzz) | `src/enrichment/dedupe.py`, deterministic merge | todo |
| O4 | Evaluation harness | Prove hybrid > keyword > vector with Recall@10 / MRR / NDCG | ~50 golden queries, `make eval` | todo |
| O5 | RAG assistant | Answer spec questions from PDFs with citations + refusal | chunking, `doc_chunks`, grounded answers | todo |
| O6 | Feedback & monitoring | Thumbs up/down, zero-result and latency tracking | `feedback` table, Streamlit capture | todo |

## Why they're optional

Round 1 exists to demonstrate two things end to end: **data quality** (contract → validate →
quarantine) and **hybrid search** (vector + keyword RRF on AlloyDB). Scorecards, LLM enrichment,
dedupe, evaluation, RAG, and observability are valuable but not needed to tell that story — and
each adds cost, dependencies, and test surface. Keep round 1 small.
