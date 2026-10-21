"""One-page hybrid-search demo (F07).

Run with ``make app``. Requires the AlloyDB Auth Proxy running and ``ENABLE_CLOUD=true``;
reuses the F06 search functions (keyword / vector / hybrid RRF) and shows them side by side.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from src.config import get_settings
from src.errors import ConfigError
from src.load.apply_sql import connect_alloydb
from src.search.hybrid_search import route_query, search_hybrid, search_keyword

_COLUMNS = ("sku", "name", "brand", "category", "size_in", "pressure_psi", "lead_free", "score")
_CATEGORIES = ("ball_valves", "gate_valves", "check_valves", "pipe", "fittings")


def _to_frame(rows) -> pd.DataFrame:
    return pd.DataFrame([dict(zip(_COLUMNS, row)) for row in rows])


def _filtered(frame: pd.DataFrame, brand: str, lead_free: str) -> pd.DataFrame:
    """Client-side brand / lead-free filters (small demo set — kept simple)."""
    if brand:
        frame = frame[frame["brand"].str.contains(brand, case=False, na=False)]
    if lead_free == "yes":
        frame = frame[frame["lead_free"].eq(True)]
    return frame


def main() -> None:
    st.set_page_config(page_title="Catalog Search", page_icon="🔎", layout="wide")
    st.title("Product Catalog — hybrid search")
    st.caption("dirty feeds → quality gate → gold → AlloyDB (vector + keyword + RRF)")

    try:
        conn = connect_alloydb(get_settings())
    except ConfigError as exc:
        st.error(f"{exc}\n\nStart the Auth Proxy and set `ENABLE_CLOUD=true` in `.env`.")
        st.stop()

    with st.form("search_form"):
        query = st.text_input("Query", value="3/4 brass ball valve lead free")
        col1, col2, col3, col4 = st.columns(4)
        category = col1.selectbox("Category", [""] + _CATEGORIES)
        brand = col2.text_input("Brand contains", "")
        lead_free = col3.selectbox("Lead free", ["any", "yes"])
        limit = col4.slider("Show top N", 5, 25, 10)
        mode = st.radio(
            "Mode", ["hybrid vs keyword", "hybrid only", "keyword only"], horizontal=True
        )
        st.form_submit_button("Search", type="primary")

    category_filter = category or None
    route = route_query(query)
    st.caption(f"query: ``{query}`` → route: ``{route}``")

    if route == "sku":
        rows = conn.execute(
            "select sku, name, brand, category, size_in, pressure_psi, lead_free, 0.0 as score "
            "from products where sku = upper(%s)",
            [query],
        ).fetchall()
        st.dataframe(_filtered(_to_frame(rows), brand, lead_free))
        return

    kw = search_keyword(conn, query, category=category_filter, limit=limit)
    hyb = search_hybrid(conn, query, category=category_filter, limit=limit)

    if mode in ("hybrid vs keyword", "keyword only"):
        left, right = st.columns(2)
        with left:
            st.subheader(f"Keyword-only — {len(kw)} results")
            st.dataframe(_filtered(_to_frame(kw), brand, lead_free))
        if mode == "hybrid vs keyword":
            with right:
                st.subheader(f"Hybrid RRF — {len(hyb)} results")
                st.dataframe(_filtered(_to_frame(hyb), brand, lead_free))
    else:
        st.subheader(f"Hybrid RRF — {len(hyb)} results")
        st.dataframe(_filtered(_to_frame(hyb), brand, lead_free))

    if mode == "hybrid vs keyword" and not kw and hyb:
        st.success("Keyword search found nothing — hybrid still finds matches by meaning.")
    conn.close()


if __name__ == "__main__":
    main()
