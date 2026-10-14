"""Page 4 — Performance Analytics."""

from __future__ import annotations

from typing import Dict, List

import pandas as pd
import streamlit as st

from bldash.core import derived as D, design as X, model as M, registry as R, widgets as W
from bldash.core.store import get_store

DIAG = ["BL2_EQUILIBRIUM_ONLY", "BL2_EQUILIBRIUM_ONLY_H1", "BL2_EXPERIMENTAL_REVISED_MACRO", "ABL_H1_BL2_VIEWS", "ABL_H6_BL2_VIEWS", "ABL_BL1_VIEWS_BL2_ALLOCATION",
        "ABL_RELATIVE_ONLY", "ABL_COMMON_ONLY", "ABL_DIAG_OMEGA", "ABL_IC_EFF_LOW", "ABL_IC_EFF_HIGH"]


def _fmt_cols(df: pd.DataFrame, pct: List[str], num: List[str], bp: List[str] = ()) -> Dict[str, str]:
    f = {c: "{:.2%}" for c in pct if c in df.columns}
    f.update({c: "{:.2f}" for c in num if c in df.columns})
    f.update({c: "{:.1f} bp" for c in bp if c in df.columns})
    return f


def render() -> None:
    store = get_store()
    X.page_header("Performance Analytics", "Detailed return, risk, turnover and attribution analysis of BL 1.0, BL 2.0 and the Strategic Rebalanced Benchmark on identical "
                  "periods, conventions and costs.", "Page 4 · Portfolio")
    X.research_banner()
    s = M.summary(store)
    with st.expander("Strategy selection (the three authoritative strategies by default; labelled diagnostic paths can be added)"):
        sel = W.strategy_pick("pf_sel", options=R.MAIN_STRATEGIES + DIAG, default=R.MAIN_STRATEGIES)
        st.caption("Diagnostic paths are ablations and the EXPERIMENTAL revised-data macro scenario: they share the accounting of the authoritative strategies but are not "
                   "authoritative results and were never used to choose a parameter.")
    if not sel:
        sel = R.MAIN_STRATEGIES
    navs = {k: M.nav(store, k) for k in sel}
    bench_nav = M.nav(store, R.BENCHMARK)
    rets = {k: M.monthly(store, k) for k in sel}
    bench_r = M.monthly(store, R.BENCHMARK)
    cash = M.cash_monthly(store)
    tabs = st.tabs(["Cumulative & annual", "Monthly distribution", "Rolling statistics", "Drawdowns", "Turnover & costs", "Statistical tests", "Attribution", "Diagnostic paths"])

    # ------------------------------------------------------------------------------------------------------- cumulative & annual
    with tabs[0]:
        X.section("Cumulative returns", "net NAV rebased to 100 at the window start; relative wealth versus the benchmark")
        start, end = W.date_range(bench_nav.index, "pf_range")
        c1, c2 = st.columns([1, 6])
        logy = c1.toggle("Log scale", value=False, key="pf_log")
        X.plot(X.line_chart({k: D.rebase(n, start, end, 100.0) for k, n in navs.items()}, yfmt=",.0f", height=420, ytitle="net NAV (start = 100)", hover_fmt=",.1f", log=logy), key="pf_cum")
        rel = {k: D.relative_wealth(n, bench_nav, start, end) for k, n in navs.items() if k != R.BENCHMARK}
        if rel:
            fig = X.line_chart(rel, yfmt="+.1%", height=340, ytitle="relative wealth vs benchmark − 1", hover_fmt="+.2%")
            fig.add_hline(y=0, line=dict(color=X.AXIS, width=1))
            X.plot(fig, key="pf_rel")
        X.section("Calendar-year returns", "stored net returns compounded over the holding periods ending in each year (first and last years are partial)")
        cy, months = M.calendar_years(store, sel)
        cats = [str(y) + ("*" if months.loc[R.BENCHMARK, y] < 12 else "") for y in cy.columns]
        X.plot(X.grouped_bar(cats, {k: cy.loc[k].to_numpy() for k in sel}, {k: X.strategy_color(k) for k in sel}, yfmt="+.1%", height=380, orientation="v"), key="pf_cy")
        tbl = cy.rename(index=X.strategy_label).copy()
        tbl.columns = cats
        X.table(tbl, {c: "{:+.2%}" for c in tbl.columns})
        st.caption("* partial year (2019: November–December; 2026: January–September).")
        X.source_note(store, ["bl2_nav_daily", "bl2_calendar_year_returns"])

    # ------------------------------------------------------------------------------------------------------- monthly distribution
    with tabs[1]:
        X.section("Monthly net return distribution", "83 holding periods per strategy")
        X.plot(X.histogram({k: r for k, r in rets.items()}, "", 360, ".0%", 24), key="pf_hist")
        rows = []
        for k in sel:
            r = s.loc[k]
            rows.append({"Strategy": X.strategy_label(k), "Mean month": r["monthly_mean_return"], "Median month": r["monthly_median_return"], "Best month": r["best_month"],
                         "Best month date": X.fmt_month(r["best_month_date"]), "Worst month": r["worst_month"], "Worst month date": X.fmt_month(r["worst_month_date"]),
                         "Positive months": r["share_positive_months"], "VaR 95 % (monthly)": r["var_monthly_95"], "ES 95 % (monthly)": r["expected_shortfall_monthly_95"],
                         "VaR 99 % (monthly)": r["var_monthly_99"], "Downside volatility": r["downside_volatility"]})
        tb = pd.DataFrame(rows).set_index("Strategy")
        X.table(tb, {c: "{:.2%}" for c in ["Mean month", "Median month", "Best month", "Worst month", "VaR 95 % (monthly)", "ES 95 % (monthly)", "VaR 99 % (monthly)", "Downside volatility"]} | {"Positive months": "{:.0%}"})
        st.caption("Historical VaR and expected shortfall are loss quantiles of 83 monthly observations (4 and 1 tail points): descriptive, not risk limits.")
        pick = W.one_strategy("pf_heat", R.BL2, options=sel, label="Monthly return calendar")
        mt = D.monthly_table(rets[pick])
        X.plot(X.heatmap(mt, f"{X.strategy_label(pick)} · monthly net returns by period-end month", 300, fmt="+.1%", zmin=-0.12, zmax=0.12, xlabels=list(mt.columns),
                         ylabels=[str(i) for i in mt.index], text=True), key="pf_mt")
        X.source_note(store, ["bl2_monthly_returns", "bl2_summary_metrics"])

    # ------------------------------------------------------------------------------------------------------- rolling
    with tabs[2]:
        X.section("Rolling statistics", "derived from the stored monthly net returns; conventions reconciled with the frozen Phase 7 rolling metrics")
        w = st.radio("Window (months)", [12, 36], horizontal=True, key="pf_w")
        c1, c2 = st.columns(2)
        c1.plotly_chart(X.line_chart({k: D.rolling_vol(r, w) for k, r in rets.items()}, yfmt=".0%", height=320, title=f"Rolling {w}-month volatility (annualized)", hover_fmt=".1%"), use_container_width=True, key="pf_rv")
        c2.plotly_chart(X.line_chart({k: D.rolling_sharpe(r, cash, w) for k, r in rets.items()}, yfmt=".1f", height=320, title=f"Rolling {w}-month Sharpe (excess over cash)", hover_fmt=".2f"), use_container_width=True, key="pf_rs")
        c3, c4 = st.columns(2)
        act = {k: r for k, r in rets.items() if k != R.BENCHMARK}
        c3.plotly_chart(X.line_chart({k: D.rolling_te(r, bench_r, w) for k, r in act.items()}, yfmt=".1%", height=320, title=f"Rolling {w}-month tracking error vs benchmark", hover_fmt=".2%"), use_container_width=True, key="pf_rte")
        fig = X.line_chart({k: D.rolling_active(r, bench_r, w) for k, r in act.items()}, yfmt="+.0%", height=320, title=f"Rolling {w}-month active return vs benchmark (compounded)", hover_fmt="+.1%")
        fig.add_hline(y=0, line=dict(color=X.AXIS, width=1))
        c4.plotly_chart(fig, use_container_width=True, key="pf_ra")
        st.caption("Rolling volatility = √12 × std (ddof 1) of the trailing monthly net returns; Sharpe = √12 × mean / std of trailing returns in excess of the realized cash return; "
                   "tracking error = √12 × std of trailing monthly active returns; active return = trailing compounded strategy return − trailing compounded benchmark return. "
                   "The 12-month volatility, tracking error and return reproduce the stored Phase 7 series for BL 1.0 and the benchmark exactly (validation report).")
        X.source_note(store, ["bl2_monthly_returns", "p7_rolling_metrics"])

    # ------------------------------------------------------------------------------------------------------- drawdowns
    with tabs[3]:
        X.section("Drawdown history", "stored daily drawdown of the post-trade NAV")
        dd = {k: M.drawdown_stored(store, k) for k in sel}
        X.plot(X.line_chart(dd, yfmt=".0%", height=400, ytitle="drawdown from running peak", hover_fmt=".1%"), key="pf_dd")
        rows = []
        for k in sel:
            r = s.loc[k]
            rows.append({"Strategy": X.strategy_label(k), "Max drawdown": r["max_drawdown"], "Peak": X.fmt_date(r["max_drawdown_peak"]), "Trough": X.fmt_date(r["max_drawdown_trough"]),
                         "Recovery": X.fmt_date(r["max_drawdown_recovery"]), "Duration (days)": int(r["max_drawdown_duration_days"]), "Longest underwater (days)": int(r["longest_drawdown_days"]),
                         "Calmar": r["calmar"]})
        X.table(pd.DataFrame(rows).set_index("Strategy"), {"Max drawdown": "{:.2%}", "Calmar": "{:.2f}"})
        ep = store.read("p7_drawdown_episodes")
        if ep is not None:
            with st.expander("Stored drawdown episodes (BL 1.0 and benchmark, Phase 7; deepest first)"):
                e2 = ep[ep["strategy"].isin(["S1_BL", "S2_GMP_REBALANCED"])].copy()
                e2["strategy"] = e2["strategy"].map({"S1_BL": "BL 1.0", "S2_GMP_REBALANCED": "Strategic Benchmark"})
                X.table(e2.head(20), {"depth": "{:.2%}"}, hide_index=True)
        X.source_note(store, ["bl2_nav_daily", "bl2_summary_metrics", "p7_drawdown_episodes"])

    # ------------------------------------------------------------------------------------------------------- turnover & costs
    with tabs[4]:
        X.section("Turnover and transaction costs", "executed statistics from the ledger; planned statistics from the optimizer")
        X.note("<b>Three different costs, kept apart.</b> (1) <b>Transaction costs</b>: an assumed uniform 10 bp one-way charge on every trade, modelled explicitly and shown here. "
               "(2) <b>Fund ongoing charges</b> (TER) are already inside the ETF total-return series the backtest values with, so they are embedded in gross and net returns alike and "
               "are never charged a second time. (3) <b>Portfolio returns</b> are reported gross (before trading costs) and net (after them).", "info")
        rows = []
        p7 = store.read("p7_summary_metrics").set_index("strategy") if store.available("p7_summary_metrics") else None
        for k in sel:
            r = s.loc[k]
            planned_nt = None
            if p7 is not None and k == R.BL1:
                planned_nt = p7.loc["S1_BL", "planned_no_trade_months"]
            rows.append({"Strategy": X.strategy_label(k), "Annual turnover (one-way, executed)": r["annual_turnover"], "Mean monthly turnover": r["mean_monthly_turnover"],
                         "Max monthly turnover": r["max_monthly_turnover"], "No-trade months (executed)": int(r["no_trade_months"]), "Planned no-trade months": planned_nt,
                         "Mean cost per rebalance (bp)": r["mean_monthly_cost_bp"], "Cost drag annualized (bp)": r["cost_drag_annualized"] * 1e4, "Cost drag cumulative (bp)": r["cost_drag_cumulative"] * 1e4,
                         "CAGR gross": r["cagr_gross"], "CAGR net": r["cagr_net"]})
        X.table(pd.DataFrame(rows).set_index("Strategy"), {"Annual turnover (one-way, executed)": "{:.1%}", "Mean monthly turnover": "{:.2%}", "Max monthly turnover": "{:.1%}",
                                                            "Mean cost per rebalance (bp)": "{:.2f}", "Cost drag annualized (bp)": "{:.1f}", "Cost drag cumulative (bp)": "{:.1f}", "CAGR gross": "{:.2%}", "CAGR net": "{:.2%}"})
        c1, c2 = st.columns(2)
        ps2, ps1 = M.portfolio_summary(store, R.BL2), M.portfolio_summary(store, R.BL1)
        c1.plotly_chart(X.line_chart({R.BL1: ps1["planned_turnover"], R.BL2: ps2["planned_turnover"]}, yfmt=".0%", height=320, title="Planned one-way turnover per decision (optimizer)", hover_fmt=".2%"), use_container_width=True, key="pf_pt")
        c2.plotly_chart(X.line_chart({R.BL1: ps1["planned_cost_bp"], R.BL2: ps2["planned_cost_bp"]}, yfmt=".0f", height=320, title="Planned transaction cost per decision (bp of NAV)", hover_fmt=".1f"), use_container_width=True, key="pf_pc")
        drag = {k: (M.nav(store, k, gross=True) / M.nav(store, k) - 1.0) for k in sel}
        X.plot(X.line_chart(drag, yfmt=".2%", height=320, title="Cumulative transaction-cost drag: NAV_gross / NAV_net − 1 (display derivation on stored paths)", hover_fmt=".3%"), key="pf_drag")
        tc = store.read("p7_transaction_costs")
        if tc is not None:
            with st.expander("Executed trading events of BL 1.0 and the benchmark (Phase 7 ledger)"):
                t2 = tc[(tc["event"] == "REBALANCE") & (tc["strategy"].isin(["S1_BL", "S2_GMP_REBALANCED"]))].copy()
                t2["strategy"] = t2["strategy"].map({"S1_BL": "BL 1.0", "S2_GMP_REBALANCED": "Strategic Benchmark"})
                X.table(t2[["strategy", "date", "turnover_target_weight", "cost_fraction_exact", "n_sleeves_traded", "max_abs_trade"]].rename(columns={"turnover_target_weight": "executed turnover", "cost_fraction_exact": "cost (fraction of NAV)"}),
                        {"executed turnover": "{:.2%}", "cost (fraction of NAV)": "{:.4%}", "max_abs_trade": "{:.2%}"}, height=360, hide_index=True)
        cs = store.read("bl2_cost_sensitivity")
        if cs is not None:
            st.markdown("**Cost sensitivity** — frozen targets charged at another one-way cost (accounting only; the targets are not re-optimized)")
            c3 = cs[cs["strategy"].isin(sel)].copy()
            c3["strategy"] = c3["strategy"].map(X.strategy_label)
            X.table(c3, {"cagr_net": "{:.2%}", "annualized_volatility": "{:.2%}", "sharpe_excess_over_cash": "{:.2f}", "max_drawdown": "{:.2%}", "annual_turnover": "{:.1%}", "cost_drag_annualized": "{:.3%}", "cost_bp": "{:.0f}"}, hide_index=True)
        X.source_note(store, ["bl2_summary_metrics", "bl2_portfolio_summary", "p6_portfolio_summary", "p7_transaction_costs", "bl2_cost_sensitivity"])

    # ------------------------------------------------------------------------------------------------------- tests
    with tabs[5]:
        X.section("Statistical tests on monthly active returns", "Newey–West HAC t-tests (3 and 6 lags) and stationary block bootstrap (block 6, 10,000 draws)")
        cmp = store.read("bl2_comparison_tests")
        pairs = [(a, b) for a in sel for b in (R.BENCHMARK, R.BL1, "BL2_EQUILIBRIUM_ONLY") if a != b]
        rows = []
        for a, b in pairs:
            h3 = cmp[(cmp["strategy"] == a) & (cmp["reference"] == b) & (cmp["method"] == "OLS_HAC_NEWEY_WEST_L3")]
            h6 = cmp[(cmp["strategy"] == a) & (cmp["reference"] == b) & (cmp["method"] == "OLS_HAC_NEWEY_WEST_L6")]
            bs = cmp[(cmp["strategy"] == a) & (cmp["reference"] == b) & (cmp["method"] == "STATIONARY_BLOCK_BOOTSTRAP")]
            if h3.empty:
                continue
            r3 = h3.iloc[0]
            rows.append({"Comparison": f"{X.strategy_label(a)} − {X.strategy_label(b)}", "Mean active return (ann.)": r3["mean_annualized"], "HAC(3) t": r3["t_statistic"], "p (HAC 3)": r3["p_value_two_sided"],
                         "HAC(6) t": h6.iloc[0]["t_statistic"] if not h6.empty else None, "95 % CI low (ann.)": r3["ci_low_annualized"], "95 % CI high (ann.)": r3["ci_high_annualized"],
                         "Bootstrap CI low": bs.iloc[0]["ci_low_mean_annualized"] if not bs.empty else None, "Bootstrap CI high": bs.iloc[0]["ci_high_mean_annualized"] if not bs.empty else None,
                         "Information ratio": bs.iloc[0]["information_ratio"] if not bs.empty else None})
        X.table(pd.DataFrame(rows).set_index("Comparison"), {"Mean active return (ann.)": "{:+.2%}", "HAC(3) t": "{:.2f}", "p (HAC 3)": "{:.3f}", "HAC(6) t": "{:.2f}", "95 % CI low (ann.)": "{:+.2%}",
                                                             "95 % CI high (ann.)": "{:+.2%}", "Bootstrap CI low": "{:+.2%}", "Bootstrap CI high": "{:+.2%}", "Information ratio": "{:.2f}"})
        st.caption("83 monthly observations; the minimum detectable active return at 80 % power is about 1.15 % per year against the benchmark and 0.7 % per year against the equilibrium-only "
                   "path (Phase 8). Only the two 'model − benchmark' gaps survive a multiple-comparison correction; every BL 2.0 − BL 1.0 difference is inside the noise.")
        reg = store.read("p7_regressions")
        if reg is not None:
            with st.expander("BL 1.0 − benchmark factor regressions (Phase 7, HAC)"):
                cols = [c for c in ["regression", "method", "r_squared", "alpha_annualized", "alpha_t", "alpha_p", "alpha_ci_low_annualized", "alpha_ci_high_annualized"] if c in reg.columns]
                X.table(reg[cols], {"r_squared": "{:.3f}", "alpha_annualized": "{:+.2%}", "alpha_t": "{:.2f}", "alpha_p": "{:.3f}", "alpha_ci_low_annualized": "{:+.2%}", "alpha_ci_high_annualized": "{:+.2%}"}, hide_index=True)
        X.source_note(store, ["bl2_comparison_tests", "p7_regressions"])

    # ------------------------------------------------------------------------------------------------------- attribution
    with tabs[6]:
        X.section("Attribution of the active return", "static exposure versus dynamic timing; sleeve contributions")
        rows, curves = [], {}
        for key, name in (("bl2_att_bl1_static_dynamic", R.BL1), ("bl2_att_trend_static_dynamic", R.BL2), ("bl2_att_eq_static_dynamic", "BL2_EQUILIBRIUM_ONLY")):
            sd = store.read(key)
            if sd is None:
                continue
            rows.append({"Strategy": X.strategy_label(name), "Static (annualized)": 12 * sd["static"].mean(), "Dynamic (annualized)": 12 * sd["dynamic"].mean(),
                         "Static (sum)": sd["static"].sum(), "Dynamic (sum)": sd["dynamic"].sum(), "Periods": len(sd)})
            curves[f"{X.strategy_label(name)} · static"] = sd.set_index("end")["static"].cumsum()
            curves[f"{X.strategy_label(name)} · dynamic"] = sd.set_index("end")["dynamic"].cumsum()
        if rows:
            X.table(pd.DataFrame(rows).set_index("Strategy"), {"Static (annualized)": "{:+.2%}", "Dynamic (annualized)": "{:+.2%}", "Static (sum)": "{:+.2%}", "Dynamic (sum)": "{:+.2%}"})
            cols = {}
            for i, k in enumerate(curves):
                base = R.BL1 if k.startswith("BL 1.0") else R.BL2 if k.startswith("BL 2.0 ·") else "BL2_EQUILIBRIUM_ONLY"
                cols[k] = X.strategy_color(base)
            dash = {k: ("dot" if "dynamic" in k else "solid") for k in curves}
            X.plot(X.line_chart(curves, colors=cols, dash=dash, labels={k: k for k in curves}, yfmt="+.0%", height=360, title="Cumulative static and dynamic components (running arithmetic sums, Phase 8 convention)", hover_fmt="+.1%"), key="pf_sd")
            st.caption("Ex-post split of the gross active return a_t′r_t = ā′r_t + (a_t − ā)′r_t with ā the full-sample average active weight (future information: an accounting identity, not a "
                       "strategy). The time-varying part is indistinguishable from zero for both models.")
        aa = store.read("p7_allocation_attribution")
        if aa is not None:
            st.markdown("**BL 1.0 − benchmark: Cariño-linked attribution by sleeve (Phase 7)**")
            a2 = aa[(aa["strategy"] == "S1_BL") & (aa["reference"] == "S2_GMP_REBALANCED")].set_index("asset_class").reindex(R.ASSETS)
            X.plot(X.bar_chart([R.ASSET_SHORT[a] for a in R.ASSETS], a2["allocation_linked"].to_numpy(), "Linked allocation contribution to the cumulative NAV difference", "+.1%", 320), key="pf_car")
            X.table(a2[["mean_active_weight", "allocation_arithmetic", "allocation_linked", "cost_differential_linked"]].rename(columns={"mean_active_weight": "mean active weight", "allocation_arithmetic": "arithmetic sum", "allocation_linked": "Cariño-linked", "cost_differential_linked": "cost differential (linked)"}),
                    {"mean active weight": "{:+.2%}", "arithmetic sum": "{:+.2%}", "Cariño-linked": "{:+.2%}", "cost differential (linked)": "{:+.3%}"})
        for key, name in (("bl2_att_trend_active", R.BL2), ("bl2_att_bl1_active", R.BL1)):
            att = store.read(key)
            if att is None:
                continue
            tot = att.groupby("asset_class")["active_contribution"].sum().reindex(R.ASSETS)
            X.plot(X.bar_chart([R.ASSET_SHORT[a] for a in R.ASSETS], tot.to_numpy(), f"{X.strategy_label(name)} − benchmark: sum of per-period active contributions by sleeve (arithmetic)", "+.1%", 300), key=f"pf_att_{name}")
        X.source_note(store, ["bl2_att_bl1_static_dynamic", "bl2_att_trend_static_dynamic", "p7_allocation_attribution", "bl2_att_trend_active"])

    # ------------------------------------------------------------------------------------------------------- diagnostic paths
    with tabs[7]:
        X.section("Diagnostic paths and sensitivities", "ablations of BL 2.0 and the BL 1.0 sensitivity grid — labelled, never a policy choice")
        cols = ["cagr_net", "annualized_volatility", "sharpe_excess_over_cash", "max_drawdown", "tracking_error_realized", "information_ratio", "excess_return_vs_benchmark_annual", "annual_turnover", "cost_drag_annualized"]
        allm = s.loc[[k for k in R.MAIN_STRATEGIES + DIAG if k in s.index], cols].copy()
        allm.index = [X.strategy_label(k) for k in allm.index]
        allm.columns = ["CAGR", "Volatility", "Sharpe", "Max DD", "TE vs bench", "IR", "Active return (ann.)", "Turnover", "Cost drag"]
        X.table(allm, {"CAGR": "{:.2%}", "Volatility": "{:.2%}", "Sharpe": "{:.2f}", "Max DD": "{:.1%}", "TE vs bench": "{:.2%}", "IR": "{:.2f}", "Active return (ann.)": "{:+.2%}", "Turnover": "{:.0%}", "Cost drag": "{:.3%}"}, height=520)
        st.caption("Reading (BL 2.0 backtest comparison): the h = 1 and h = 3 allocations of the same BL 2.0 views earn the same return (optimizer change immaterial); BL 1.0's small views "
                   "through the narrower h = 3 band lose about 1.15 % per year; relative-only trend is the best path on the sample but was not selected (that would be performance-based); "
                   "the experimental revised-data macro block adds nothing detectable.")
        sens = store.read("p7_sensitivity_scenarios")
        if sens is not None:
            with st.expander("BL 1.0 diagnostic sensitivities (Phase 7: cost, horizon, TE cap, risk multiplier, limits, execution lag)"):
                sc = sens[sens["strategy"] == "S1_BL"][["scenario", "dimension", "cagr_net", "annualized_volatility", "sharpe_excess_over_cash", "max_drawdown", "tracking_error_realized", "information_ratio", "annual_turnover", "cost_drag_annualized"]]
                X.table(sc, {"cagr_net": "{:.2%}", "annualized_volatility": "{:.2%}", "sharpe_excess_over_cash": "{:.2f}", "max_drawdown": "{:.1%}", "tracking_error_realized": "{:.2%}", "information_ratio": "{:.2f}", "annual_turnover": "{:.1%}", "cost_drag_annualized": "{:.3%}"}, hide_index=True)
        X.source_note(store, ["bl2_summary_metrics", "p7_sensitivity_scenarios"])
