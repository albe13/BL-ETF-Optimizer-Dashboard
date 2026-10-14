"""Data façade for the pages: tidy, cached views of the verified artifacts (pivots and joins only; nothing is recomputed)."""

from __future__ import annotations

from typing import Dict, List, Optional

import numpy as np
import pandas as pd
import streamlit as st

from bldash.core import registry as R
from bldash.core.store import get_store

A = R.ASSETS


def _store():
    return get_store()


def _fp(store) -> str:
    return store.fingerprint()


# ----------------------------------------------------------------------------------------------------------------------- universe
@st.cache_data(show_spinner=False)
def _etf_meta(fp: str) -> pd.DataFrame:
    cfg = _store().read("cfg_benchmark")
    rows = []
    for c in cfg["components"]:
        grp = next((g for g, m in R.GROUPS.items() if c["asset_class"] in m), "")
        rows.append({"asset_class": c["asset_class"], "etf_name": c["etf_name"], "ticker": c["ticker"], "isin": c["isin"], "underlying_index": c["underlying_index"],
                     "geography": c["geography"], "fund_currency": c["fund_currency"], "listing_currency": c["listing_currency"], "hedging": c["hedging"],
                     "income_treatment": c["income_treatment"], "proxy_quality": c["proxy_quality"], "target_weight": float(c["target_weight"]), "group": grp,
                     "notes": str(c.get("notes", "")).strip()})
    return pd.DataFrame(rows).set_index("asset_class").reindex(A)


def etf_meta(store) -> pd.DataFrame:
    return _etf_meta(_fp(store))


def benchmark_weights(store) -> pd.Series:
    bw = store.meta.get("benchmark_weights") or {}
    if bw:
        return pd.Series({k: float(v) for k, v in bw.items()}).reindex(A)
    return etf_meta(store)["target_weight"]


def etf_audit(store) -> Optional[pd.DataFrame]:
    a = store.read("m0_data_audit")
    return None if a is None else a.set_index("asset_class").reindex(A)


# ----------------------------------------------------------------------------------------------------------------------- strategies
@st.cache_data(show_spinner=False)
def _summary(fp: str) -> pd.DataFrame:
    return _store().read("bl2_summary_metrics").set_index("strategy")


def summary(store) -> pd.DataFrame:
    return _summary(_fp(store))


def metric(store, strategy: str, name: str):
    s = summary(store)
    return s.loc[strategy, name] if strategy in s.index and name in s.columns else None


@st.cache_data(show_spinner=False)
def _nav_long(fp: str) -> pd.DataFrame:
    return _store().read("bl2_nav_daily")


def nav(store, strategy: str, gross: bool = False) -> pd.Series:
    nd = _nav_long(_fp(store))
    sub = nd[nd["strategy"] == strategy].set_index("date").sort_index()
    return sub["nav_gross" if gross else "nav_net"].rename(strategy)


def drawdown_stored(store, strategy: str) -> pd.Series:
    nd = _nav_long(_fp(store))
    return nd[nd["strategy"] == strategy].set_index("date").sort_index()["drawdown"].rename(strategy)


@st.cache_data(show_spinner=False)
def _monthly_long(fp: str) -> pd.DataFrame:
    return _store().read("bl2_monthly_returns")


def monthly(store, strategy: str, col: str = "net_return") -> pd.Series:
    m = _monthly_long(_fp(store))
    return m[m["strategy"] == strategy].set_index("end").sort_index()[col].rename(strategy)


def cash_monthly(store) -> pd.Series:
    m = _monthly_long(_fp(store))
    return m[m["strategy"] == R.BENCHMARK].set_index("end").sort_index()["cash_return"].rename("cash")


def execution_dates(store) -> pd.DatetimeIndex:
    cal = store.read("p7_execution_calendar")
    return pd.DatetimeIndex(sorted(pd.to_datetime(cal["execution_date"]).unique()))


def comparison(store, strategy: str, reference: str, method: str = "OLS_HAC_NEWEY_WEST_L3") -> Optional[pd.Series]:
    c = store.read("bl2_comparison_tests")
    r = c[(c["strategy"] == strategy) & (c["reference"] == reference) & (c["method"] == method)]
    return None if r.empty else r.iloc[0]


def calendar_years(store, strategies: List[str]) -> pd.DataFrame:
    cy = store.read("bl2_calendar_year_returns")
    t = cy.pivot(index="strategy", columns="year", values="return").reindex(strategies)
    months = cy.pivot(index="strategy", columns="year", values="months").reindex(strategies)
    return t, months


# ----------------------------------------------------------------------------------------------------------------------- weights
@st.cache_data(show_spinner=False)
def _targets_long_bl2(fp: str) -> pd.DataFrame:
    t = _store().read("bl2_targets_long")
    t["date"] = pd.to_datetime(t["date"])
    return t


@st.cache_data(show_spinner=False)
def _targets_bl1(fp: str) -> pd.DataFrame:
    t = _store().read("p6_target_weights")
    t["date"] = pd.to_datetime(t["date"])
    return t


def targets_long(store, model: str) -> pd.DataFrame:
    """Per-sleeve target rows at every decision date: BL 2.0 production or BL 1.0 (Phase 6). Uniform columns."""
    if model == R.BL2:
        t = _targets_long_bl2(_fp(store))
        t = t[t["label"] == R.BL2]
        return t[["date", "asset_class", "benchmark_weight", "pretrade_weight", "target_weight", "active_weight", "lower_bound", "upper_bound", "at_lower_bound",
                  "at_upper_bound", "planned_trade", "posterior_adjustment_d", "untraded"]].copy()
    t = _targets_bl1(_fp(store)).rename(columns={"pretrade_weight_planned": "pretrade_weight"})
    t["untraded"] = t["planned_trade"].abs() < 1e-12
    t["posterior_adjustment_d"] = np.nan
    return t[["date", "asset_class", "benchmark_weight", "pretrade_weight", "target_weight", "active_weight", "lower_bound", "upper_bound", "at_lower_bound",
              "at_upper_bound", "planned_trade", "posterior_adjustment_d", "untraded"]].copy()


def targets_wide(store, model: str, col: str = "target_weight") -> pd.DataFrame:
    t = targets_long(store, model)
    w = t.pivot(index="date", columns="asset_class", values=col)[A].sort_index()
    return w


def ablation_targets_wide(store, label: str) -> pd.DataFrame:
    t = _targets_long_bl2(_fp(store))
    return t[t["label"] == label].pivot(index="date", columns="asset_class", values="target_weight")[A].sort_index()


def targets_at(store, model: str, d: pd.Timestamp) -> pd.DataFrame:
    t = targets_long(store, model)
    return t[t["date"] == pd.Timestamp(d)].set_index("asset_class").reindex(A)


@st.cache_data(show_spinner=False)
def _weights_exec(fp: str) -> pd.DataFrame:
    return _store().read("bl2_weights_executed")


def executed_wide(store, strategy: str) -> pd.DataFrame:
    w = _weights_exec(_fp(store))
    return w[w["strategy"] == strategy].pivot(index="date", columns="asset_class", values="weight")[A].sort_index()


def portfolio_summary(store, model: str) -> pd.DataFrame:
    if model == R.BL2:
        ps = store.read("bl2_portfolio_summary")
        ps = ps[ps["label"] == R.BL2].copy()
    else:
        ps = store.read("p6_portfolio_summary").copy()
    ps["date"] = pd.to_datetime(ps["date"])
    return ps.set_index("date").sort_index()


def ablation_summary(store, label: str) -> pd.DataFrame:
    ps = store.read("bl2_portfolio_summary")
    ps = ps[ps["label"] == label].copy()
    ps["date"] = pd.to_datetime(ps["date"])
    return ps.set_index("date").sort_index()


# ----------------------------------------------------------------------------------------------------------------------- engine inputs
@st.cache_data(show_spinner=False)
def _prior_wide(fp: str) -> pd.DataFrame:
    p = _store().read("p2_pi_wide")
    return p.set_index("estimation_date")[A].sort_index()


def prior_wide(store) -> pd.DataFrame:
    return _prior_wide(_fp(store))


def delta_history(store) -> pd.DataFrame:
    d = store.read("p2_delta_history")
    return d.set_index("estimation_date").sort_index()


@st.cache_data(show_spinner=False)
def _cov_long(fp: str) -> pd.DataFrame:
    return _store().read("p1_covariance_long")


def covariance(store, d: pd.Timestamp) -> pd.DataFrame:
    c = _cov_long(_fp(store))
    sub = c[c["estimation_date"] == pd.Timestamp(d)]
    return sub.pivot(index="row_asset", columns="col_asset", values="value").reindex(index=A, columns=A)


def correlation_at(store, d: pd.Timestamp) -> Optional[pd.DataFrame]:
    c = store.read("p1_correlation_long")
    if c is None:
        return None
    sub = c[c["estimation_date"] == pd.Timestamp(d)]
    return sub.pivot(index="row_asset", columns="col_asset", values="value").reindex(index=A, columns=A)


def sigma_wide(store) -> pd.DataFrame:
    s = store.read("p1_sleeve_vol")
    return s.set_index("estimation_date")[A].sort_index()


# ----------------------------------------------------------------------------------------------------------------------- views and posterior
@st.cache_data(show_spinner=False)
def _views_bl2(fp: str) -> pd.DataFrame:
    s = _store()
    vr = s.read("bl2_view_register")
    po = s.read("bl2_posterior")
    vr["date"], po["date"] = pd.to_datetime(vr["date"]), pd.to_datetime(po["date"])
    j = vr.merge(po[["date", "asset_class", "prior_expected_return", "posterior_expected_return", "posterior_adjustment", "adjustment_trend_relative", "adjustment_trend_common",
                     "adjustment_macro_news", "active_views_on_date", "omega_structure", "lambda"]], on=["date", "asset_class"], how="left")
    return j


def views_bl2(store, d: Optional[pd.Timestamp] = None) -> pd.DataFrame:
    j = _views_bl2(_fp(store))
    if d is None:
        return j
    return j[j["date"] == pd.Timestamp(d)].set_index("asset_class").reindex(A)


@st.cache_data(show_spinner=False)
def _views_bl1(fp: str) -> pd.DataFrame:
    s = _store()
    v = s.read("p5_views")
    po = s.read("p5_posterior")
    reg = s.read("p5_view_register")
    att = s.read("p5_attribution_summary")
    for df in (v, po, reg, att):
        df["date"] = pd.to_datetime(df["date"])
    base = reg[["date", "asset_class", "view_id", "source_mode", "view_status", "unavailability_reason"]]
    j = base.merge(v[["date", "asset_class", "signal_S", "trend_T", "macro_M", "sigma", "prior_return", "raw_view_adjustment", "view_target_Q", "normalized_uncertainty_variance"]],
                   on=["date", "asset_class"], how="left")
    j = j.merge(po[["date", "asset_class", "prior_expected_return", "posterior_expected_return", "posterior_adjustment", "view_available", "active_views_on_date"]],
                on=["date", "asset_class"], how="left")
    j = j.merge(att[["date", "asset_class", "own_view_contribution", "own_gain_K_ii", "cross_view_contribution", "largest_positive_cross_contributor",
                     "largest_positive_cross_contribution", "largest_negative_cross_contributor", "largest_negative_cross_contribution", "sign_agreement"]],
                on=["date", "asset_class"], how="left")
    return j


def views_bl1(store, d: Optional[pd.Timestamp] = None) -> pd.DataFrame:
    j = _views_bl1(_fp(store))
    if d is None:
        return j
    return j[j["date"] == pd.Timestamp(d)].set_index("asset_class").reindex(A)


def view_mapping_bl1(store) -> pd.DataFrame:
    m = store.read("p5_view_mapping")
    return m.set_index("asset_class").reindex(A)


def uncertainty_bl1(store, d: pd.Timestamp) -> Optional[pd.DataFrame]:
    u = store.read("p5_normalized_uncertainty")
    if u is None:
        return None
    u["date"] = pd.to_datetime(u["date"])
    sub = u[u["date"] == pd.Timestamp(d)]
    if sub.empty:
        return None
    ids = sorted(sub["row_view_id"].unique(), key=lambda v: list(sub[sub["row_view_id"] == v]["row_position"])[0])
    m = sub.pivot(index="row_view_id", columns="col_view_id", values="value").reindex(index=ids, columns=ids)
    names = {vid: vid.replace("ABS_", "").replace("_", " ").title() for vid in ids}
    return m.rename(index=names, columns=names)


def transmission_bl2(store) -> pd.DataFrame:
    t = store.read("bl2_transmission").copy()
    t["date"] = pd.to_datetime(t["date"])
    return t.set_index("date").sort_index()


def active_vs_view_bl1(store) -> pd.DataFrame:
    t = store.read("p6_active_vs_view_sign").copy()
    t["date"] = pd.to_datetime(t["date"])
    return t


# ----------------------------------------------------------------------------------------------------------------------- trend
@st.cache_data(show_spinner=False)
def _trend_bl2(fp: str) -> pd.DataFrame:
    t = _store().read("bl2_trend_signals")
    t["estimation_date"] = pd.to_datetime(t["estimation_date"])
    return t


def trend_bl2(store, d: Optional[pd.Timestamp] = None) -> pd.DataFrame:
    t = _trend_bl2(_fp(store))
    if d is None:
        return t
    return t[t["estimation_date"] == pd.Timestamp(d)].set_index("asset_class").reindex(A)


def trend_wide(store, field: str) -> pd.DataFrame:
    t = _trend_bl2(_fp(store))
    return t.pivot(index="estimation_date", columns="asset_class", values=field)[A].sort_index()


def trend_common(store) -> pd.DataFrame:
    c = store.read("bl2_trend_common").copy()
    c["estimation_date"] = pd.to_datetime(c["estimation_date"])
    return c.set_index("estimation_date").sort_index()


@st.cache_data(show_spinner=False)
def _trend_bl1(fp: str) -> Optional[pd.DataFrame]:
    t = _store().read("p3_trend_score")
    if t is None:
        return None
    t["estimation_date"] = pd.to_datetime(t["estimation_date"])
    return t


def trend_bl1(store, d: Optional[pd.Timestamp] = None) -> Optional[pd.DataFrame]:
    t = _trend_bl1(_fp(store))
    if t is None or d is None:
        return t
    return t[t["estimation_date"] == pd.Timestamp(d)].set_index("asset_class").reindex(A)


# ----------------------------------------------------------------------------------------------------------------------- macro
@st.cache_data(show_spinner=False)
def _macro_wide(fp: str) -> pd.DataFrame:
    w = _store().read("bl2_macro_wide")
    w["date"] = pd.to_datetime(w["date"])
    return w.set_index("date").sort_index()


def macro_wide(store) -> pd.DataFrame:
    return _macro_wide(_fp(store))


def regimes(store, region: Optional[str] = None) -> pd.DataFrame:
    r = store.read("bl2_macro_regimes").copy()
    r["date"] = pd.to_datetime(r["date"])
    if region:
        r = r[r["region"] == region]
    return r.set_index("date").sort_index()


def composites(store, family: Optional[str] = None) -> pd.DataFrame:
    c = store.read("bl2_macro_composites").copy()
    c["date"] = pd.to_datetime(c["date"])
    if family:
        c = c[c["family"] == family]
    return c.set_index("date").sort_index()


def component_audit(store) -> Optional[pd.DataFrame]:
    c = store.read("bl2_macro_component_audit")
    if c is None:
        return None
    c = c.copy()
    c["date"] = pd.to_datetime(c["date"])
    return c


def regime_bl1(store) -> pd.DataFrame:
    r = store.read("p4_regime_history").copy()
    r["estimation_date"] = pd.to_datetime(r["estimation_date"])
    return r.set_index("estimation_date").sort_index()


def market_raw(store) -> Optional[pd.DataFrame]:
    r = store.read("bl2_market_raw")
    if r is None:
        return None
    r = r.copy()
    r["date"] = pd.to_datetime(r["date"])
    return r.set_index("date").sort_index()


# ----------------------------------------------------------------------------------------------------------------------- ETF levels
@st.cache_data(show_spinner=False)
def _etf_levels(fp: str) -> Optional[pd.DataFrame]:
    w = _store().read("m0_weights_history")
    if w is None:
        return None
    lv = w.pivot(index="date", columns="asset_class", values="price")[A]
    lv.index = pd.to_datetime(lv.index)
    return lv.sort_index()


def etf_levels(store) -> Optional[pd.DataFrame]:
    """Daily EUR total-return levels of the ten ETFs on the M0 common valuation calendar (absent in a SAFE-only bundle)."""
    return _etf_levels(_fp(store))


def previous_date(store, d: pd.Timestamp) -> Optional[pd.Timestamp]:
    dates = [pd.Timestamp(x) for x in store.meta.get("model_dates", [])]
    i = dates.index(pd.Timestamp(d)) if pd.Timestamp(d) in dates else -1
    return dates[i - 1] if i > 0 else None
