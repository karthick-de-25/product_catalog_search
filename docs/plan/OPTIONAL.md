# OPTIONAL — post-round-1 ideas

**Not required.** Build only after the core demo (F01–F07) is solid, and only with human approval
(adding a feature is a critical change per `AGENTS.md` §4). Each would get its own `ONN-*.md` plan.

| ID | Idea | Value | Rough shape |
|---|---|---|---|
| O1 | Supplier quality scorecard | Per-supplier completeness/duplicate score + run trend | `src/quality/scorecard.py`, a report table |
| O2 | Gemini attribute extraction | Pull size/material/certifications from free-text descriptions | JSON-schema output + confidence; low confidence → review queue |
| O3 | Deduplication | Merge near-duplicate products (brand + category blocking + RapidFuzz) | `src/enrichment/dedupe.py`, deterministic merge |
| O4 | Evaluation harness | Prove hybrid > keyword > vector with Recall@10 / MRR / NDCG | ~50 golden queries, `make eval` |
| O5 | RAG assistant | Answer spec questions from PDFs with citations + refusal | chunking, `doc_chunks`, grounded answers |
| O6 | Feedback & monitoring | Thumbs up/down, zero-result and latency tracking | `feedback` table, Streamlit capture |

## Why they're optional

Round 1 exists to demonstrate two things end to end: **data quality** (contract → validate →
quarantine) and **hybrid search** (vector + keyword RRF on AlloyDB). Scorecards, LLM enrichment,
dedupe, evaluation, RAG, and observability are valuable but not needed to tell that story — and
each adds cost, dependencies, and test surface. Keep round 1 small.
