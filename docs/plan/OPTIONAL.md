# OPTIONAL — post-round-1 ideas

**Not required.** Build only after the core demo (F01–F07) is solid, and only with human approval
(adding a feature is a critical change per `AGENTS.md` §4). Each gets its own `ONN-*.md` plan.

- `O1` — done (see `O01-scorecard.md`).

## Recommended order (analysis, 2026-10-21)

| Pri | Item | Status | Why now | Cost |
|---|---|---|---|---|
| P0 | Keyword tokenizer fix (`search_text` underscores → spaces + reload) | **done** | keyword column was always empty (underscore fused tokens); fixed 2026-10-21 | tiny code + 1 🔴 cloud UPDATE (approved) |
| P1 | O4 Evaluation harness | todo | proves "hybrid beats keyword" with numbers (Recall@10 / MRR / NDCG) | offline |
| P1 | O1 Quality scorecard | **done** | gives the data-quality pillar per-supplier numbers | offline |
| P2 | O3 Dedupe | todo | better catalog → better scores/search | offline |
| P3 | O2 Gemini extraction / O5 RAG | todo | wow factor; cloud cost + more tests | high |
| P4 | O6 Feedback | todo | after the demo exists | low |

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
