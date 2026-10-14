"""Synchronized historical date navigation (one decision date shared by every page) and the decision/execution/observation triplet."""

from __future__ import annotations

from typing import Dict, List, Optional

import pandas as pd
import streamlit as st

KEY = "bl_decision_date"


def model_dates(store) -> List[pd.Timestamp]:
    return [pd.Timestamp(d) for d in store.meta.get("model_dates", [])]


def calendar(store) -> pd.DataFrame:
    cal = store.read("p7_execution_calendar")
    if cal is None:
        return pd.DataFrame(columns=["decision_date", "execution_date", "accrual_start", "accrual_end"])
    return cal


def triplet(store, d: pd.Timestamp) -> Dict[str, Optional[pd.Timestamp]]:
    """Decision date (signals observed at the close), execution date (next common session), return-observation window."""
    cal = calendar(store)
    row = cal[cal["decision_date"] == pd.Timestamp(d)]
    if row.empty:
        return {"decision": pd.Timestamp(d), "execution": None, "accrual_start": None, "accrual_end": None, "sessions": None}
    r = row.iloc[0]
    return {"decision": pd.Timestamp(d), "execution": r.get("execution_date"), "accrual_start": r.get("accrual_start"), "accrual_end": r.get("accrual_end"),
            "sessions": r.get("holding_period_sessions")}


def current(store) -> pd.Timestamp:
    dates = model_dates(store)
    d = st.session_state.get(KEY)
    if d is None or pd.Timestamp(d) not in dates:
        st.session_state[KEY] = dates[-1]
    return pd.Timestamp(st.session_state[KEY])


def set_date(store, d) -> None:
    st.session_state[KEY] = pd.Timestamp(d)


def sidebar_selector(store) -> pd.Timestamp:
    """Sidebar control shared by every page; stores the chosen decision date in session state."""
    dates = model_dates(store)
    cur = current(store)
    st.sidebar.markdown("**Historical decision date**")
    idx = dates.index(cur)
    c1, c2, c3 = st.sidebar.columns([1, 3, 1])
    if c1.button("◀", key="bl_prev", help="Previous decision date", disabled=idx == 0):
        st.session_state[KEY] = dates[idx - 1]
        st.rerun()
    if c3.button("▶", key="bl_next", help="Next decision date", disabled=idx == len(dates) - 1):
        st.session_state[KEY] = dates[idx + 1]
        st.rerun()
    sel = c2.selectbox("Decision date", dates, index=dates.index(current(store)), format_func=lambda x: x.strftime("%Y-%m-%d"), key="bl_date_box", label_visibility="collapsed")
    if pd.Timestamp(sel) != current(store):
        st.session_state[KEY] = pd.Timestamp(sel)
        st.rerun()
    t = triplet(store, current(store))
    ex = t["execution"].strftime("%Y-%m-%d") if t["execution"] is not None and not pd.isna(t["execution"]) else "n/a"
    ae = t["accrual_end"].strftime("%Y-%m-%d") if t["accrual_end"] is not None and not pd.isna(t["accrual_end"]) else "beyond the frozen window"
    st.sidebar.caption(f"Decision {current(store).strftime('%Y-%m-%d')} (close) · execution {ex} · return observed to {ae}. "
                       "Synchronized across Allocation, Engine, Macro, Trend and Decisions.")
    return current(store)


def date_caption(store, d: pd.Timestamp) -> str:
    t = triplet(store, d)
    ex = t["execution"].strftime("%Y-%m-%d") if t["execution"] is not None and not pd.isna(t["execution"]) else "n/a"
    if t["accrual_end"] is not None and not pd.isna(t["accrual_end"]):
        tail = f"return observed over the holding period to {t['accrual_end'].strftime('%Y-%m-%d')}"
    else:
        tail = "the holding period after this execution lies beyond the frozen backtest window (no realized return is published for it)"
    return (f"Decision date {d.strftime('%Y-%m-%d')} (signals observed at the close) → execution at the next common session {ex} → "
            f"{tail}. No information after the decision close enters the decision.")
