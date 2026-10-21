# ADR-0002 — Hybrid retrieval ranked with Reciprocal Rank Fusion (RRF)

- **Status:** accepted
- **Date:** 2026-10-21
- **Deciders:** human
- **Related:** `docs/plan/F11-hybrid-search.md`, `sql/04_hybrid_search.sql`

## Context
Contractors search in two very different ways: natural language (*"3/4 inch brass ball valve
lead free"*) and exact/fuzzy identifiers (part numbers, with typos). Semantic (vector) search
handles the former; keyword/full-text and trigram matching handle the latter. We must combine
two ranked lists whose scores are not on a comparable scale (`<=>` cosine distance vs
`ts_rank_cd`), and do it **inside AlloyDB** to keep one round trip.

## Decision
Run a vector query and a keyword query (each `LIMIT 50`) as CTEs, `FULL OUTER JOIN` them by
product id, and rank with Reciprocal Rank Fusion: `score = Σ 1/(k + rank)` with `k = 60`.
Add a `pg_trgm` fuzzy path as a fallback for identifier-like queries.

## Consequences
- **Positive:** no score calibration or per-query weights; robust when one retriever returns
  nothing; trivially expressed in one SQL statement; easy to add a third retriever later.
- **Negative / trade-offs:** ignores score magnitude, so a very strong single-signal match can
  rank below a mediocre but doubly-retrieved one; `k` and the `LIMIT 50` are tunables that need
  evaluation.
- **Follow-ups:** F12 must measure keyword-only, vector-only, and hybrid (RRF) with Recall@k/MRR/
  NDCG@10 and record `k`. Query routing decides which paths run.

## Alternatives considered
- **Weighted linear score fusion** — requires normalization and tuning per query type; brittle.
- **Rerank only (Vertex AI Ranking API)** — higher latency and cost; can still be added on top
  of the top-N RRF results.
- **Single retriever** — keyword misses paraphrase; vector misses exact part numbers and typos.
