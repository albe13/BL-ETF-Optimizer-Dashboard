"""Page 3 — ETF Market Performance (all ten ETFs shown by default)."""

from __future__ import annotations

from typing import Dict

import pandas as pd
import streamlit as st

from bldash.core import derived as D, design as X, model as M, registry as R, widgets as W
from bldash.core.store import get_store


@st.cache_data(show_spinner=False)
def _stats(fp: str, start: str, end: str) -> pd.DataFrame:
    store = get_store()
    lv = M.etf_levels(store)
    ex = M.execution_dates(store)
    cash = M.cash_monthly(store)
    rows = []
    for a in R.ASSETS:
        s = D.level_stats(lv[a], start, end)
        r_m = D.returns_on_calendar(lv[a], ex)
        r_m = r_m.loc[(r_m.index > pd.Timestamp(start)) & (r_m.index <= pd.Timestamp(end))]
        rows.append({"asset_class": a, **s, "sharpe_model_window": D.sharpe_excess(r_m, cash), "sharpe_periods": int(len(r_m.dropna())),
                     "return_over_vol": (s["cagr"] / s["volatility"]) if s["volatility"] and s["volatility"] == s["volatility"] and s["volatility"] > 0 else float("nan")})
    return pd.DataFrame(rows).set_index("asset_class")


def _no_levels(store) -> None:
    X.note("<b>ETF total-return series not included in this deployment.</b> The daily EUR total-return levels of the ten ETFs are Bloomberg-derived data classified "
           "REQUIRES_LICENSE_REVIEW; they are excluded from the public package until the data licence has been reviewed. The identities, benchmark weights and the "
           "strategy results built on them are shown; the comparative price charts and the ETF risk statistics appear only when the licensed series are present "
           "(local repository mode or a package built with the review tier).", "warn")


def render() -> None:
    store = get_store()
    X.page_header("ETF Market Performance", "The complete ten-ETF investment universe: EUR total-return performance, risk statistics and correlations, with every "
                  "instrument displayed by default.", "Page 3 · Portfolio")
    meta = M.etf_meta(store)
    lv = M.etf_levels(store)
    X.note("Series are <b>EUR total-return indices</b> (distributions reinvested; USD-listed lines translated at ECB reference rates), not traded ETF prices or quotes. "
           "All ten series start on 2016-10-06 on the common valuation calendar; the backtest window begins on 2019-11-01.", "info")
    if lv is None:
        _no_levels(store)
        X.section("Investment universe", "authoritative identities from the frozen benchmark definition")
        X.table(meta[["etf_name", "ticker", "isin", "group", "target_weight", "hedging", "income_treatment"]].rename(columns={"etf_name": "ETF", "target_weight": "Benchmark weight"}), {"Benchmark weight": "{:.2%}"})
        X.source_note(store, ["cfg_benchmark"])
        return

    # ------------------------------------------------------------------------------------------------------- A
    X.section("A · Comparative performance", "all ten ETF total-return series normalized to 100 at the start of the selected window")
    start, end = W.date_range(lv.index, "etf_range")
    c1, c2 = st.columns([1, 5])
    logy = c1.toggle("Logarithmic scale", value=False, key="etf_log")
    norm = {a: D.rebase(lv[a], start, end, 100.0) for a in R.ASSETS}
    fig = X.line_chart(norm, colors=X.ETF_COLORS, labels={a: f"{R.ASSET_SHORT[a]} · {meta.loc[a, 'ticker'].split(' ')[0]}" for a in R.ASSETS}, yfmt=",.0f",
                       height=520, ytitle="total-return index (start = 100)", hover_fmt=",.1f", log=logy, end_labels=True, width=1.8)
    fig.update_layout(margin=dict(r=110))
    X.plot(fig, key="etf_cmp")
    st.caption(f"Window {start.date()} → {end.date()}. Normalization: level_t / level_start × 100 on the stored M0 total-return levels (display derivation only).")

    # ------------------------------------------------------------------------------------------------------- B
    X.section("B · Individual ETF panels", "five rows, two instruments per row; statistics on the selected window")
    stats = _stats(store.fingerprint(), str(start.date()), str(end.date()))
    audit = M.etf_audit(store)
    for i in range(0, len(R.ASSETS), 2):
        cols = st.columns(2)
        for col, a in zip(cols, R.ASSETS[i:i + 2]):
            m = meta.loc[a]
            s = stats.loc[a]
            with col:
                st.markdown(f"**{m['etf_name']}**")
                st.markdown(f'<div class="bl-small">{a} · {m["group"]} · {m["ticker"]} · ISIN {m["isin"]} · {m["hedging"]} · {m["income_treatment"]}</div>', unsafe_allow_html=True)
                f = X.line_chart({a: norm[a]}, colors=X.ETF_COLORS, labels={a: R.ASSET_SHORT[a]}, yfmt=",.0f", height=230, hover_fmt=",.1f", width=1.8)
                f.update_layout(showlegend=False, margin=dict(l=6, r=10, t=10, b=6))
                X.plot(f, key=f"etf_panel_{i}_{a}")
                sh = X.fmt_num(s["sharpe_model_window"]) if s["sharpe_periods"] >= 12 else "n/a"
                st.markdown(f'<div class="bl-small">CAGR <b>{X.fmt_pct(s["cagr"])}</b> · volatility <b>{X.fmt_pct(s["volatility"], 1)}</b> · Sharpe (excess over cash, model-window months) '
                            f'<b>{sh}</b> · max drawdown <b>{X.fmt_pct(s["max_drawdown"], 1)}</b> · total return <b>{X.fmt_pct(s["total_return"], 1)}</b></div>', unsafe_allow_html=True)
    st.caption("CAGR = (level_end / level_start)^(365.25 / days) − 1; volatility = √252 × std of daily returns; Sharpe = √12 × mean / std of monthly returns in excess of the "
               "realized EUR cash return, computed on the holding-period calendar of the backtest (2019-11 → 2026-10) that falls inside the window, since the cash "
               "series is published only there; max drawdown from the running peak of the level inside the window.")

    # ------------------------------------------------------------------------------------------------------- C
    X.section("C · Risk analytics", "drawdowns, rolling volatility, correlation structure and the comparative table")
    tabs = st.tabs(["Drawdowns", "Rolling volatility", "Correlation matrix", "Comparative table", "Identity, data and audit"])
    with tabs[0]:
        dd = {a: D.drawdown(D.window(lv[a], start, end)) for a in R.ASSETS}
        X.plot(X.line_chart(dd, colors=X.ETF_COLORS, labels={a: R.ASSET_SHORT[a] for a in R.ASSETS}, yfmt=".0%", height=420, ytitle="drawdown from running peak", hover_fmt=".1%", width=1.5), key="etf_dd")
        st.caption("Drawdown = level_t / running maximum inside the window − 1.")
    with tabs[1]:
        rv = {a: D.rolling_vol_daily(lv[a]).loc[start:end] for a in R.ASSETS}
        X.plot(X.line_chart(rv, colors=X.ETF_COLORS, labels={a: R.ASSET_SHORT[a] for a in R.ASSETS}, yfmt=".0%", height=420, ytitle="annualized volatility (252-session window)", hover_fmt=".1%", width=1.5), key="etf_rv")
        st.caption("Rolling √252 × std of daily returns over the trailing 252 sessions (first value one year after inception).")
    with tabs[2]:
        ex = M.execution_dates(store)
        rets = pd.DataFrame({a: D.returns_on_calendar(lv[a], ex) for a in R.ASSETS})
        rets = rets.loc[(rets.index > start) & (rets.index <= end)]
        if len(rets) >= 12:
            corr = D.correlation(rets)
            X.plot(X.heatmap(corr, f"Correlation of monthly total returns, {len(rets)} holding periods", 520, zmid=0.0, fmt=".2f", zmin=-1, zmax=1,
                             xlabels=[R.ASSET_SHORT[a] for a in R.ASSETS], ylabels=[R.ASSET_SHORT[a] for a in R.ASSETS], text=True), key="etf_corr")
            st.caption("Pearson correlation of simple returns between consecutive execution dates of the backtest calendar (2019-11 → 2026-10); the model itself uses "
                       "a daily 3-year Ledoit-Wolf covariance (Page 5), not this matrix.")
        else:
            st.info("The correlation matrix needs at least 12 holding periods of the backtest calendar inside the selected window.")
    with tabs[3]:
        tb = stats.copy()
        tb.insert(0, "ETF", meta["etf_name"])
        tb.insert(1, "Ticker", meta["ticker"])
        tb.insert(2, "ISIN", meta["isin"])
        tb.insert(3, "Group", meta["group"])
        tb["Sharpe (model window)"] = tb.apply(lambda r: r["sharpe_model_window"] if r["sharpe_periods"] >= 12 else float("nan"), axis=1)
        show = tb[["ETF", "Ticker", "ISIN", "Group", "start", "end", "total_return", "cagr", "volatility", "Sharpe (model window)", "max_drawdown", "max_drawdown_trough"]].rename(
            columns={"start": "Window start", "end": "Window end", "total_return": "Total return", "cagr": "CAGR", "volatility": "Volatility", "max_drawdown": "Max drawdown", "max_drawdown_trough": "Drawdown trough"})
        for c in ("Window start", "Window end", "Drawdown trough"):
            show[c] = pd.to_datetime(show[c]).dt.date
        X.table(show, {"Total return": "{:.1%}", "CAGR": "{:.2%}", "Volatility": "{:.2%}", "Sharpe (model window)": "{:.2f}", "Max drawdown": "{:.1%}"}, height=420)
    with tabs[4]:
        ident = meta[["etf_name", "ticker", "isin", "underlying_index", "geography", "fund_currency", "listing_currency", "hedging", "income_treatment", "proxy_quality", "target_weight", "notes"]].rename(
            columns={"etf_name": "ETF", "target_weight": "Benchmark weight"})
        X.table(ident, {"Benchmark weight": "{:.2%}"}, height=420)
        if audit is not None:
            cols = [c for c in ["ticker", "first_valid_tr_date", "last_valid_tr_date", "valid_tr_observations", "missing_observations", "missing_venue_holidays", "tr_distribution_steps",
                                "tr_convention", "currency_status", "fx_translation", "data_quality_status"] if c in audit.columns]
            st.markdown("**M0 data audit (frozen data stage)**")
            X.table(audit[cols], height=420)
        pxtr = store.read("m0_px_vs_tr")
        if pxtr is not None:
            st.markdown("**Price return vs total return over the full history (distribution effect)**")
            X.table(pxtr.set_index("asset_class").reindex(R.ASSETS)[["income_treatment", "cumulative_px_last_return_eur", "cumulative_total_return_eur", "difference_tr_minus_px", "finding"]],
                    {"cumulative_px_last_return_eur": "{:.1%}", "cumulative_total_return_eur": "{:.1%}", "difference_tr_minus_px": "{:+.1%}"})
    X.source_note(store, ["m0_weights_history", "cfg_benchmark", "m0_data_audit", "p7_cash_returns"])
