"""Page 1 — Executive Overview."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from bldash.core import derived as D, design as X, model as M, registry as R, state, widgets as W
from bldash.core.store import get_store


def _findings(store) -> list:
    s = M.summary(store)
    b1, b2, bb = s.loc[R.BL1], s.loc[R.BL2], s.loc[R.BENCHMARK]
    t_21 = M.comparison(store, R.BL2, R.BL1)
    t_1b = M.comparison(store, R.BL1, R.BENCHMARK)
    t_2b = M.comparison(store, R.BL2, R.BENCHMARK)
    t_eq = M.comparison(store, "BL2_EQUILIBRIUM_ONLY", R.BENCHMARK)
    p7 = store.read("p7_inference_mean_tests")
    s1s4 = p7[(p7["series"] == "S1_minus_S4_EQUILIBRIUM_ONLY") & (p7["method"] == "OLS_HAC_NEWEY_WEST_L3")]
    hi_ret = R.BL1 if b1["cagr_net"] >= b2["cagr_net"] else R.BL2
    hi_sh = R.BL1 if b1["sharpe_excess_over_cash"] >= b2["sharpe_excess_over_cash"] else R.BL2
    lo_dd = R.BL1 if b1["max_drawdown"] >= b2["max_drawdown"] else R.BL2
    out = [
        f"<b>Realized return.</b> {X.strategy_label(hi_ret)} had the higher net CAGR ({X.fmt_pct(b1['cagr_net'])} BL 1.0 vs {X.fmt_pct(b2['cagr_net'])} BL 2.0); "
        f"both exceeded the Strategic Benchmark ({X.fmt_pct(bb['cagr_net'])}) over the same 83 holding periods and under identical accounting.",
        f"<b>Risk-adjusted.</b> {X.strategy_label(hi_sh)} had the higher Sharpe ratio (excess over realized EUR cash): {X.fmt_num(b2['sharpe_excess_over_cash'])} BL 2.0 vs "
        f"{X.fmt_num(b1['sharpe_excess_over_cash'])} BL 1.0 vs {X.fmt_num(bb['sharpe_excess_over_cash'])} benchmark; volatility {X.fmt_pct(b2['annualized_volatility'], 1)} / "
        f"{X.fmt_pct(b1['annualized_volatility'], 1)} / {X.fmt_pct(bb['annualized_volatility'], 1)}.",
        f"<b>Drawdown.</b> {X.strategy_label(lo_dd)} had the shallower maximum drawdown ({X.fmt_pct(b2['max_drawdown'], 1)} BL 2.0 vs {X.fmt_pct(b1['max_drawdown'], 1)} BL 1.0 vs "
        f"{X.fmt_pct(bb['max_drawdown'], 1)} benchmark); all three troughed in March 2020, so the difference is a property of the sample, not of a risk control.",
        f"<b>Tracking error.</b> BL 2.0 ran {X.fmt_pct(b2['tracking_error_realized'])} of realized tracking error against the benchmark, BL 1.0 {X.fmt_pct(b1['tracking_error_realized'])}: "
        f"BL 2.0's larger views reach the 2 % ex-ante cap on a large share of dates, so its information ratio ({X.fmt_num(b2['information_ratio'])}) is lower than BL 1.0's "
        f"({X.fmt_num(b1['information_ratio'])}) despite a similar active return ({X.fmt_pct(b2['excess_return_vs_benchmark_annual'])} vs {X.fmt_pct(b1['excess_return_vs_benchmark_annual'])} per year).",
        f"<b>Turnover and costs.</b> BL 2.0 trades about {b2['annual_turnover'] / b1['annual_turnover']:.0f} times more than BL 1.0 ({X.fmt_pct(b2['annual_turnover'], 0)} vs "
        f"{X.fmt_pct(b1['annual_turnover'], 0)} one-way per year; benchmark {X.fmt_pct(bb['annual_turnover'], 0)}), with an annualized cost drag of {X.fmt_bp(b2['cost_drag_annualized'])} vs "
        f"{X.fmt_bp(b1['cost_drag_annualized'])} at the assumed 10 bp one-way cost.",
    ]
    if t_21 is not None:
        out.append(f"<b>Statistical significance.</b> The BL 2.0 − BL 1.0 difference is {X.fmt_pct(t_21['mean_annualized'], 2, sign=True)} per year with a HAC t-statistic of "
                   f"{X.fmt_num(t_21['t_statistic'])} (p = {X.fmt_num(t_21['p_value_two_sided'], 2)}): the two models are statistically indistinguishable on this sample. "
                   f"Against the benchmark, BL 1.0 earns {X.fmt_pct(t_1b['mean_annualized'], 2, sign=True)} (t {X.fmt_num(t_1b['t_statistic'], 1)}) and BL 2.0 "
                   f"{X.fmt_pct(t_2b['mean_annualized'], 2, sign=True)} (t {X.fmt_num(t_2b['t_statistic'], 1)}) per year.")
    if t_eq is not None and not s1s4.empty:
        r = s1s4.iloc[0]
        out.append(f"<b>Where the active return comes from.</b> A cost-aware optimizer with <i>no views at all</i> earns most of the gap to the benchmark "
                   f"({X.fmt_pct(t_eq['mean_annualized'], 2, sign=True)} per year for the BL 2.0 equilibrium-only path; {X.fmt_pct(r['mean_annualized'], 2, sign=True)} per year is the "
                   f"part of BL 1.0's gap attributable to its views, p = {X.fmt_num(r['p_value_two_sided'], 2)}). The excess return is a persistent exposure to Equity and Gold "
                   f"financed by Government Bonds, which the 2019–2026 sample rewarded; it is not evidence of predictive alpha and does not demonstrate that either model forecasts returns.")
    out.append("<b>What this does not show.</b> No test on 2019–2026 is independent of model development; with 83 months the minimum detectable active return is about "
               "1.15 % per year against the benchmark, so neither model's edge can be confirmed or refuted from this history alone.")
    return out


def render() -> None:
    store = get_store()
    X.page_header("BL ETF Optimizer", "Quantitative Multi-Asset Portfolio Allocation Using Black-Litterman, Trend and Macroeconomic Analysis.", "Executive overview")
    win = store.meta.get("simulation_window", {})
    bl2s, bl1s = store.meta.get("bl2_status", {}), store.meta.get("bl1_status", {})
    X.badges([("BL 1.0 · frozen, validated backtest", "good"), (f"BL 2.0 · frozen research configuration · {bl2s.get('checks_passed')}/{bl2s.get('checks_total')} checks", "good"),
              ("Artifacts hash-verified", "good"), (f"Window {win.get('start')} → {win.get('end')} · {win.get('holding_periods')} monthly holding periods", "info"),
              ("EUR · net of 10 bp one-way costs", "info")])
    st.markdown("")
    st.markdown(
        "The BL ETF Optimizer allocates a long-only, fully invested portfolio across **ten UCITS ETFs** that proxy the liquid asset classes of a global market "
        "portfolio. A frozen **strategic benchmark** (LIQUID_GMP_2026_V1) anchors the allocation; the **Black-Litterman** framework turns an equilibrium prior "
        "implied by that benchmark and systematic **views** — trend signals in BL 2.0, trend plus a macro regime score in BL 1.0 — into posterior expected returns; "
        "a benchmark-relative optimizer with a 2 % tracking-error cap, position limits and transaction-cost awareness converts them into monthly target weights, "
        "executed at the next common session. Both model versions and the benchmark are simulated on the same EUR total-return data, calendar and accounting.")
    X.research_banner()

    # ------------------------------------------------------------------------------------------------------- A. performance comparison
    X.section("A · Performance comparison", "identical period, conventions and costs for the three strategies")
    s = M.summary(store)
    cards = []
    for strat in R.MAIN_STRATEGIES:
        r = s.loc[strat]
        cards.append({"label": X.strategy_label(strat), "value": X.fmt_pct(r["cagr_net"]), "sub": f"CAGR net · Sharpe {X.fmt_num(r['sharpe_excess_over_cash'])} · max drawdown {X.fmt_pct(r['max_drawdown'], 1)}",
                      "color": X.strategy_color(strat)})
    X.cards(cards)
    rows = []
    spec = [("CAGR (net)", "cagr_net", "pct"), ("Annualized volatility", "annualized_volatility", "pct"), ("Sharpe ratio (excess over cash)", "sharpe_excess_over_cash", "num"),
            ("Maximum drawdown", "max_drawdown", "pct"), ("Tracking error vs benchmark", "tracking_error_realized", "pct_rel"), ("Information ratio", "information_ratio", "num_rel"),
            ("Annualized active return vs benchmark", "excess_return_vs_benchmark_annual", "pct_rel"), ("Annual turnover (one-way)", "annual_turnover", "pct1"),
            ("Transaction-cost drag (annualized)", "cost_drag_annualized", "bp"), ("Share of months outperforming benchmark", "share_months_outperforming", "pct0_rel")]
    for lab, col, kind in spec:
        row = {"Metric": lab}
        for strat in R.MAIN_STRATEGIES:
            v = s.loc[strat, col] if col in s.columns else None
            if kind.endswith("_rel") and strat == R.BENCHMARK:
                row[X.strategy_label(strat)] = "—"
            elif kind.startswith("pct0"):
                row[X.strategy_label(strat)] = X.fmt_pct(v, 0)
            elif kind.startswith("pct1"):
                row[X.strategy_label(strat)] = X.fmt_pct(v, 1)
            elif kind.startswith("pct"):
                row[X.strategy_label(strat)] = X.fmt_pct(v)
            elif kind.startswith("num"):
                row[X.strategy_label(strat)] = X.fmt_num(v)
            elif kind == "bp":
                row[X.strategy_label(strat)] = X.fmt_bp(v, 1)
        rows.append(row)
    X.table(pd.DataFrame(rows).set_index("Metric"))
    st.caption("Definitions: CAGR = (NAV_T / NAV_0)^(365.25 / days) − 1 on the daily post-trade NAV; volatility = √12 × std of monthly net returns; Sharpe = √12 × mean / std of "
               "monthly returns in excess of the realized EONIA→€STR cash return; tracking error = √12 × std of monthly active returns vs the Strategic Benchmark; "
               "information ratio = annualized mean active return / tracking error; active return = 12 × mean monthly active return (arithmetic). Benchmark-relative "
               "statistics are undefined for the benchmark itself.")
    X.source_note(store, ["bl2_summary_metrics"])

    # ------------------------------------------------------------------------------------------------------- B. cumulative wealth
    X.section("B · Cumulative wealth", "growth of EUR 10,000 invested at the start of the window, net of costs")
    navs = {k: M.nav(store, k) for k in R.MAIN_STRATEGIES}
    dates = navs[R.BL1].index
    start, end = W.date_range(dates, "ov_range")
    logy = st.toggle("Logarithmic scale", value=False, key="ov_log")
    growth = {k: D.growth_of_capital(n, start, end, 10_000) for k, n in navs.items()}
    fig = X.line_chart(growth, yfmt=",.0f", height=440, ytitle="EUR", hover_fmt=",.0f", log=logy, end_labels=False)
    fig.update_layout(hovermode="x unified")
    X.plot(fig, key="ov_wealth")
    final = {k: g.iloc[-1] for k, g in growth.items()}
    X.cards([{"label": f"{X.strategy_label(k)} · end value", "value": X.fmt_eur(v), "sub": f"total return {X.fmt_pct(v / 10_000 - 1, 1)} over {start.date()} → {end.date()}",
              "color": X.strategy_color(k)} for k, v in final.items()])
    st.caption("Display derivation: capital × NAV_t / NAV_start on the stored daily post-trade NAV paths (identical start date and compounding for the three strategies).")

    # ------------------------------------------------------------------------------------------------------- C. active performance
    X.section("C · Active performance versus the Strategic Benchmark", "cumulative relative wealth under the compounding convention")
    rel = {k: D.relative_wealth(navs[k], navs[R.BENCHMARK], start, end) for k in (R.BL1, R.BL2)}
    fig = X.line_chart(rel, yfmt="+.1%", height=360, ytitle="relative wealth − 1", hover_fmt="+.2%")
    fig.add_hline(y=0, line=dict(color=X.AXIS, width=1))
    X.plot(fig, key="ov_rel")
    st.caption("Cumulative active performance = (NAV_strategy / NAV_strategy,start) ÷ (NAV_benchmark / NAV_benchmark,start) − 1. This is the compounded wealth ratio, "
               "not the arithmetic sum of monthly active returns: the two differ, and only the ratio compounds correctly.")

    # ------------------------------------------------------------------------------------------------------- D. current allocation
    d_last = state.model_dates(store)[-1]
    X.section("D · Latest published allocation", f"target weights decided on {d_last.date()} (executed at the next common session)")
    b = M.benchmark_weights(store)
    w1 = M.targets_at(store, R.BL1, d_last)["target_weight"]
    w2 = M.targets_at(store, R.BL2, d_last)["target_weight"]
    meta = M.etf_meta(store)
    cats = [f"{a} · {meta.loc[a, 'ticker'].split(' ')[0]}" for a in R.ASSETS]
    fig = X.grouped_bar(cats, {R.BL1: w1.to_numpy(), R.BL2: w2.to_numpy(), R.BENCHMARK: b.to_numpy()},
                        {k: X.strategy_color(k) for k in R.MAIN_STRATEGIES}, yfmt=".1%", height=460)
    X.plot(fig, key="ov_alloc")
    with st.expander("Allocation table (weights and active weights in percentage points)"):
        tbl = pd.DataFrame({"ETF": meta["etf_name"], "Benchmark": b, "BL 1.0": w1, "BL 1.0 active (pp)": (w1 - b) * 100, "BL 2.0": w2, "BL 2.0 active (pp)": (w2 - b) * 100,
                            "BL 2.0 − BL 1.0 (pp)": (w2 - w1) * 100})
        X.table(tbl, {"Benchmark": "{:.2%}", "BL 1.0": "{:.2%}", "BL 2.0": "{:.2%}", "BL 1.0 active (pp)": "{:+.2f}", "BL 2.0 active (pp)": "{:+.2f}", "BL 2.0 − BL 1.0 (pp)": "{:+.2f}"})
    X.source_note(store, ["p6_target_weights", "bl2_targets_long"])

    # ------------------------------------------------------------------------------------------------------- E. key findings
    X.section("E · Key findings", "factual reading of the frozen results")
    for f in _findings(store):
        st.markdown(f"- {f}", unsafe_allow_html=True)
    X.source_note(store, ["bl2_summary_metrics", "bl2_comparison_tests", "p7_inference_mean_tests"])
