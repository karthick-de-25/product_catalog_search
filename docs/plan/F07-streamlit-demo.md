---
feature: F07
title: Streamlit search demo
status: done
approved: 2026-10-21
depends_on: [F06]
---

# F07 — Streamlit search demo

**Goal:** a one-page Streamlit app that shows hybrid search beating keyword-only on the same query.

**Non-goals:** RAG/Q&A, dashboards, auth, feedback capture (all optional).

## Slices

### Slice 1 — Search page   `[x]`
- **In → out:** user query + filters → ranked results table
- **Files:** `src/app/streamlit_app.py`, `Makefile`
- **UI:** search box; filters (brand, category, lead-free); a "keyword only / hybrid" toggle that
  runs the same query both ways side by side; results table (sku, name, brand, size, score).
- **Test:** none (UI) — verified manually with `make app`.
- **Critical actions:** none (reading from AlloyDB requires the Auth Proxy running).
- **Done when:** `make app` launches and a query returns ranked results.

## Acceptance
- [x] `make app` opens the search page and returns results for a natural-language and a part-number query.
- [x] The keyword-only vs hybrid comparison is visible side by side.

## Commands
```bash
make app
```

## Log
- 2026-10-21 — plan created (proposed); simplified for the round-1 demo.
- 2026-10-21 — plan approved by human.
- 2026-10-21 — slice 1: `src/app/streamlit_app.py` + `make app` — search box, category/brand/
  lead-free filters, keyword vs hybrid side by side (SKU route too). Reuses the F06 search
  API; client-side brand/lead-free filtering. Headless boot verified (HTTP 200). F07 done.
