"""BL ETF Optimizer — presentation dashboard (BL 1.0 vs BL 2.0 vs the Strategic Rebalanced Benchmark).

Standalone deployment package: this file is the Streamlit entry point (Community Cloud main file) and sits at the repository root.
Local:   python -m streamlit run streamlit_app.py          (from this folder, after pip install -r requirements.txt)

The app reads the hash-verified artifacts bundled under artifacts/ (ARTIFACT_MANIFEST.json carries the frozen-run contract pins) and
recomputes no model quantity. The frozen models, their data and the original BL 1.0 / BL 2.0 dashboards are not part of this package.
"""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

APP_DIR = Path(__file__).resolve().parent
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from bldash.core import design, state  # noqa: E402
from bldash.core.store import ArtifactsMissing, IntegrityError, get_store  # noqa: E402
from bldash.views import (p01_overview, p02_allocation, p03_etf, p04_performance, p05_engine, p06_macro, p07_trend, p08_decisions,  # noqa: E402
                          p09_methodology, p10_limitations)

st.set_page_config(page_title="BL ETF Optimizer", page_icon="📊", layout="wide", initial_sidebar_state="expanded",
                   menu_items={"About": "BL ETF Optimizer — Black-Litterman multi-asset ETF allocation (BL 1.0, BL 2.0, strategic benchmark). "
                                        "Historical, in-sample results on hash-verified artifacts."})
design.inject_css()

try:
    store = get_store()
except ArtifactsMissing as exc:
    st.title("BL ETF Optimizer")
    st.warning(f"**No published artifacts found.** {exc}")
    st.stop()
except IntegrityError as exc:
    st.title("BL ETF Optimizer")
    st.warning(f"**Artifact verification failed — nothing is displayed.** {exc}")
    st.stop()

missing = store.missing_required()
if missing:
    st.title("BL ETF Optimizer")
    st.warning("**Required artifacts are missing from this deployment:** " + ", ".join(missing) + ". The dashboard cannot start without them.")
    st.stop()
st.markdown("""
<style>
    /* Sidebar background */
    section[data-testid="stSidebar"] {
        background-color: #142238 !important;
    }

    section[data-testid="stSidebar"] > div {
        background-color: #142238 !important;
    }

    /* Sidebar text */
    section[data-testid="stSidebar"] p,
    section[data-testid="stSidebar"] span,
    section[data-testid="stSidebar"] label {
        color: #F1F5F9 !important;
    }

    /* Navigation links */
    [data-testid="stSidebarNav"] a {
        color: #F1F5F9 !important;
    }

    /* Selected navigation item */
    [data-testid="stSidebarNav"] a[aria-current="page"] {
        background-color: #263B57 !important;
        border-radius: 8px;
    }
</style>
""", unsafe_allow_html=True)
with st.sidebar:
    st.markdown("### BL ETF Optimizer")
    st.caption("Quantitative multi-asset ETF allocation with Black-Litterman, trend and macroeconomic analysis · EUR · hash-verified frozen runs")
    state.sidebar_selector(store)
    st.markdown("---")
    mode_txt = "repository artifacts" if store.mode == "repo" else "deployment bundle"
    st.caption(f"Data source: {mode_txt} · BL 2.0 run `{store.run_ids.get('bl2', '')[:28]}…` · BL 1.0 backtest `{store.run_ids.get('p7', '')[:22]}…`")
    st.caption("Historical in-sample results · not investment advice · no forecast of future performance.")

PAGES = {
    "Overview": [st.Page(p01_overview.render, title="Executive Overview", icon=":material/dashboard:", default=True)],
    "Portfolio": [st.Page(p02_allocation.render, title="Portfolio Allocation", icon=":material/pie_chart:", url_path="allocation"),
                  st.Page(p03_etf.render, title="ETF Market Performance", icon=":material/show_chart:", url_path="etfs"),
                  st.Page(p04_performance.render, title="Performance Analytics", icon=":material/analytics:", url_path="performance")],
    "Model engine": [st.Page(p05_engine.render, title="Black-Litterman Engine", icon=":material/functions:", url_path="engine"),
                     st.Page(p06_macro.render, title="Macro Regime & Economic Outlook", icon=":material/public:", url_path="macro"),
                     st.Page(p07_trend.render, title="Trend & Signal Analytics", icon=":material/trending_up:", url_path="trend"),
                     st.Page(p08_decisions.render, title="Historical Portfolio Decisions", icon=":material/history:", url_path="decisions")],
    "Reference": [st.Page(p09_methodology.render, title="Model Methodology", icon=":material/menu_book:", url_path="methodology"),
                  st.Page(p10_limitations.render, title="Limitations & Future Improvements", icon=":material/report:", url_path="limitations")],
}
nav = st.navigation(PAGES, position="sidebar", expanded=True)
nav.run()
