"""Reusable controls: date-range selector with presets, strategy pickers."""

from __future__ import annotations

from typing import List, Optional, Tuple

import pandas as pd
import streamlit as st

from bldash.core import registry as R
from bldash.core.design import strategy_label

PRESETS = ["Full window", "Last 5 years", "Last 3 years", "Last 12 months", "Custom"]


def date_range(dates: pd.DatetimeIndex, key: str, default_preset: str = "Full window", min_span_days: int = 40) -> Tuple[pd.Timestamp, pd.Timestamp]:
    """Window selector snapped to observed dates. Presets or custom start/end; invalid custom ranges fall back visibly."""
    lo, hi = pd.Timestamp(dates.min()), pd.Timestamp(dates.max())
    c1, c2, c3 = st.columns([2.2, 1, 1])
    preset = c1.segmented_control("Period", PRESETS, default=default_preset, key=f"{key}_preset", label_visibility="collapsed")
    preset = preset or default_preset
    if preset == "Full window":
        s, e = lo, hi
    elif preset == "Last 5 years":
        s, e = max(lo, hi - pd.DateOffset(years=5)), hi
    elif preset == "Last 3 years":
        s, e = max(lo, hi - pd.DateOffset(years=3)), hi
    elif preset == "Last 12 months":
        s, e = max(lo, hi - pd.DateOffset(years=1)), hi
    else:
        s = pd.Timestamp(c2.date_input("Start", value=lo.date(), min_value=lo.date(), max_value=hi.date(), key=f"{key}_s"))
        e = pd.Timestamp(c3.date_input("End", value=hi.date(), min_value=lo.date(), max_value=hi.date(), key=f"{key}_e"))
        if s >= e or (e - s).days < min_span_days:
            st.warning("The period start must precede the end by at least a few weeks; showing the full window instead.")
            s, e = lo, hi
    s2 = dates[dates >= s].min()
    e2 = dates[dates <= e].max()
    if pd.isna(s2) or pd.isna(e2) or s2 >= e2:
        return lo, hi
    return pd.Timestamp(s2), pd.Timestamp(e2)


def strategy_pick(key: str, default: Optional[List[str]] = None, options: Optional[List[str]] = None, label: str = "Strategies") -> List[str]:
    opts = options or R.MAIN_STRATEGIES
    return st.multiselect(label, opts, default=default or opts, format_func=strategy_label, key=key)


def one_strategy(key: str, default: str = R.BL2, options: Optional[List[str]] = None, label: str = "Strategy") -> str:
    opts = options or R.MAIN_STRATEGIES
    return st.selectbox(label, opts, index=opts.index(default) if default in opts else 0, format_func=strategy_label, key=key)
