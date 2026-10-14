"""Presentation-derived quantities (documented in DASHBOARD_DATA_CONTRACT.md §4).

Rule: every number that is a model output (NAV, returns, weights, views, posterior, metrics, tests) is displayed as stored. The functions
below only (a) rebase, pivot, filter and difference stored series, (b) compute statistics of the ten ETF total-return levels, which no
frozen run publishes, and (c) compute rolling statistics from stored monthly returns where the frozen runs publish none. Conventions
match the frozen Phase 7 definitions and are reconciled against stored metrics by tools/validate_dashboard.py.
"""

from __future__ import annotations

import math
from typing import Dict, Optional

import numpy as np
import pandas as pd

MONTHS = 12
SESSIONS = 252
DAY_COUNT = 365.25


# ----------------------------------------------------------------------------------------------------------------------- rebasing
def window(s: pd.Series, start=None, end=None) -> pd.Series:
    s = s.dropna().sort_index()
    if start is not None:
        s = s.loc[pd.Timestamp(start):]
    if end is not None:
        s = s.loc[:pd.Timestamp(end)]
    return s


def rebase(s: pd.Series, start=None, end=None, base: float = 100.0) -> pd.Series:
    """Stored level divided by its first value in the window, times `base`."""
    seg = window(s, start, end)
    return seg / float(seg.iloc[0]) * base if len(seg) else seg


def growth_of_capital(nav: pd.Series, start=None, end=None, capital: float = 10_000.0) -> pd.Series:
    """Growth of an initial investment: capital x NAV_t / NAV_start (stored daily post-trade NAV)."""
    return rebase(nav, start, end, capital)


def relative_wealth(nav_strategy: pd.Series, nav_benchmark: pd.Series, start=None, end=None) -> pd.Series:
    """Cumulative active performance under the compounding convention: (NAV_s,t / NAV_s,0) / (NAV_b,t / NAV_b,0) - 1 on common dates."""
    a, b = window(nav_strategy, start, end), window(nav_benchmark, start, end)
    j = pd.concat([a.rename("s"), b.rename("b")], axis=1, join="inner").dropna()
    if j.empty:
        return pd.Series(dtype=float)
    r = (j["s"] / float(j["s"].iloc[0])) / (j["b"] / float(j["b"].iloc[0])) - 1.0
    return r.rename("relative_wealth")


def period_return(s: pd.Series, start=None, end=None) -> float:
    seg = window(s, start, end)
    return float(seg.iloc[-1] / seg.iloc[0] - 1.0) if len(seg) > 1 else float("nan")


# ----------------------------------------------------------------------------------------------------------------------- level statistics
def drawdown(levels: pd.Series) -> pd.Series:
    """level_t / running maximum - 1 (running maximum over the displayed window, inclusive of the first observation)."""
    s = levels.dropna()
    return s / s.cummax() - 1.0


def daily_returns(levels: pd.Series) -> pd.Series:
    s = levels.dropna()
    return s / s.shift(1) - 1.0


def cagr(levels: pd.Series) -> float:
    """(L_T / L_0) ** (365.25 / calendar days) - 1 (Phase 7 convention)."""
    s = levels.dropna()
    if len(s) < 2:
        return float("nan")
    days = (s.index[-1] - s.index[0]).days
    return float((s.iloc[-1] / s.iloc[0]) ** (DAY_COUNT / days) - 1.0) if days > 0 else float("nan")


def annualized_vol_daily(levels: pd.Series) -> float:
    """sqrt(252) x sample standard deviation (ddof = 1) of daily simple returns."""
    r = daily_returns(levels).dropna()
    return float(r.std(ddof=1) * math.sqrt(SESSIONS)) if len(r) > 2 else float("nan")


def max_drawdown(levels: pd.Series) -> Dict[str, object]:
    dd = drawdown(levels)
    if dd.empty:
        return {"max_drawdown": float("nan"), "trough": None, "peak": None}
    trough = dd.idxmin()
    peak = levels.dropna().loc[:trough].idxmax()
    return {"max_drawdown": float(dd.min()), "trough": trough, "peak": peak}


def level_stats(levels: pd.Series, start=None, end=None) -> Dict[str, object]:
    seg = window(levels, start, end)
    md = max_drawdown(seg)
    return {"start": seg.index[0] if len(seg) else None, "end": seg.index[-1] if len(seg) else None, "observations": int(len(seg)),
            "total_return": period_return(seg), "cagr": cagr(seg), "volatility": annualized_vol_daily(seg), "max_drawdown": md["max_drawdown"],
            "max_drawdown_peak": md["peak"], "max_drawdown_trough": md["trough"]}


def rolling_vol_daily(levels: pd.Series, sessions: int = SESSIONS) -> pd.Series:
    """Rolling sqrt(252) x std (ddof = 1) of daily returns over `sessions` observations."""
    r = daily_returns(levels)
    return r.rolling(sessions, min_periods=sessions).std(ddof=1) * math.sqrt(SESSIONS)


# ----------------------------------------------------------------------------------------------------------------------- monthly statistics
def returns_on_calendar(levels: pd.Series, dates: pd.DatetimeIndex) -> pd.Series:
    """Simple returns between consecutive calendar dates (level_{k+1} / level_k - 1); levels must be observed on each date."""
    s = levels.dropna().reindex(dates)
    r = s / s.shift(1) - 1.0
    return r.iloc[1:]


def sharpe_excess(r: pd.Series, cash: pd.Series) -> float:
    """sqrt(12) x mean(r - cash) / std(r - cash, ddof = 1) on aligned holding periods (Phase 7 'sharpe_excess_over_cash')."""
    j = pd.concat([r.rename("r"), cash.rename("c")], axis=1, join="inner").dropna()
    if len(j) < 3:
        return float("nan")
    x = j["r"] - j["c"]
    sd = x.std(ddof=1)
    return float(x.mean() / sd * math.sqrt(MONTHS)) if sd > 0 else float("nan")


def annualized_vol_monthly(r: pd.Series) -> float:
    r = r.dropna()
    return float(r.std(ddof=1) * math.sqrt(MONTHS)) if len(r) > 2 else float("nan")


def tracking_error(r_s: pd.Series, r_b: pd.Series) -> float:
    j = pd.concat([r_s.rename("s"), r_b.rename("b")], axis=1, join="inner").dropna()
    return float((j["s"] - j["b"]).std(ddof=1) * math.sqrt(MONTHS)) if len(j) > 2 else float("nan")


def information_ratio(r_s: pd.Series, r_b: pd.Series) -> float:
    j = pd.concat([r_s.rename("s"), r_b.rename("b")], axis=1, join="inner").dropna()
    d = j["s"] - j["b"]
    sd = d.std(ddof=1)
    return float(d.mean() / sd * math.sqrt(MONTHS)) if len(j) > 2 and sd > 0 else float("nan")


def rolling_vol(r: pd.Series, w: int) -> pd.Series:
    return r.rolling(w, min_periods=w).std(ddof=1) * math.sqrt(MONTHS)


def rolling_sharpe(r: pd.Series, cash: pd.Series, w: int) -> pd.Series:
    j = pd.concat([r.rename("r"), cash.rename("c")], axis=1, join="inner")
    x = j["r"] - j["c"]
    return x.rolling(w, min_periods=w).mean() / x.rolling(w, min_periods=w).std(ddof=1) * math.sqrt(MONTHS)


def rolling_te(r_s: pd.Series, r_b: pd.Series, w: int) -> pd.Series:
    j = pd.concat([r_s.rename("s"), r_b.rename("b")], axis=1, join="inner")
    return (j["s"] - j["b"]).rolling(w, min_periods=w).std(ddof=1) * math.sqrt(MONTHS)


def rolling_active(r_s: pd.Series, r_b: pd.Series, w: int) -> pd.Series:
    """Trailing compounded return of the strategy minus that of the benchmark over the window (the stored Phase 7 convention,
    reproduced to 0.0 on S1 12-month windows)."""
    j = pd.concat([r_s.rename("s"), r_b.rename("b")], axis=1, join="inner")
    return rolling_return(j["s"], w) - rolling_return(j["b"], w)


def rolling_return(r: pd.Series, w: int) -> pd.Series:
    """Compounded return over the trailing window: prod(1 + r) - 1."""
    return (1.0 + r).rolling(w, min_periods=w).apply(np.prod, raw=True) - 1.0


def monthly_table(r: pd.Series) -> pd.DataFrame:
    """Year x month pivot of stored holding-period returns, keyed by the period end month."""
    s = r.dropna()
    df = pd.DataFrame({"year": s.index.year, "month": s.index.month, "r": s.to_numpy()})
    t = df.pivot(index="year", columns="month", values="r")
    t.columns = [pd.Timestamp(2000, m, 1).strftime("%b") for m in t.columns]
    return t


def correlation(returns_wide: pd.DataFrame) -> pd.DataFrame:
    """Pearson correlation of aligned simple returns (pairwise complete observations)."""
    return returns_wide.corr(method="pearson")


def annualized_mean(mean_monthly: float) -> float:
    return 12.0 * mean_monthly


def active_weights(w: pd.DataFrame, b: pd.Series) -> pd.DataFrame:
    """target - benchmark, columns aligned on the benchmark index."""
    return w[b.index].sub(b.to_numpy(), axis=1)
