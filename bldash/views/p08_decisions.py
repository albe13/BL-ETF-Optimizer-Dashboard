"""Page 8 — Historical Portfolio Decision Explorer."""

from __future__ import annotations

import numpy as np
import pandas as pd
import streamlit as st

from bldash.core import derived as D, design as X, model as M, narrative as N, registry as R, state
from bldash.core.store import get_store

SHORT = [R.ASSET_SHORT[a] for a in R.ASSETS]


def render() -> None:
    store = get_store()
    d = state.current(store)
    trip = state.triplet(store, d)
    prev = M.previous_date(store, d)
    X.page_header("Historical Portfolio Decisions", "Select any published rebalance date and trace, for every ETF, how the prior, the signals, the views, the posterior and the "
                  "constraints produced the allocation — and why the model deviated from the benchmark.", "Page 8 · Model engine")
    X.note(state.date_caption(store, d))
    st.markdown("Use the **decision date** control in the sidebar (synchronized with the Allocation, Engine, Macro and Trend pages).")
    meta = M.etf_meta(store)
    b = M.benchmark_weights(store)
    v1, v2 = M.views_bl1(store, d), M.views_bl2(store, d)
    t1, t2 = M.targets_at(store, R.BL1, d), M.targets_at(store, R.BL2, d)
    pt1 = M.targets_at(store, R.BL1, prev) if prev is not None else None
    pt2 = M.targets_at(store, R.BL2, prev) if prev is not None else None
    ps1, ps2 = M.portfolio_summary(store, R.BL1), M.portfolio_summary(store, R.BL2)
    r1 = ps1.loc[d] if d in ps1.index else None
    r2 = ps2.loc[d] if d in ps2.index else None
    tr = M.transmission_bl2(store)
    tr2 = tr.loc[d] if d in tr.index else None
    av = M.active_vs_view_bl1(store)
    av = av[av["date"] == d].set_index("asset_class").reindex(R.ASSETS)
    tz = M.trend_bl2(store, d)
    W = M.macro_wide(store)
    w = W.loc[d] if d in W.index else None
    rg_us, rg_ea = M.regimes(store, "US"), M.regimes(store, "EA")
    b1 = M.regime_bl1(store)
    ql = lambda q: X.QUADRANT_LABELS.get(str(q), str(q))

    # ------------------------------------------------------------------------------------------------------- summary cards
    X.section("The decision in one view", f"{d.date()}")
    cm = M.trend_common(store)
    X.cards([{"label": "US · EA quadrant (BL 2.0 states)", "value": f"{ql(rg_us.loc[d, 'quadrant']) if d in rg_us.index else 'n/a'}", "sub": f"EA: {ql(rg_ea.loc[d, 'quadrant']) if d in rg_ea.index else 'n/a'} · BL 1.0 regime: {ql(b1.loc[d, 'regime']) if d in b1.index and isinstance(b1.loc[d, 'regime'], str) else 'unavailable'}"},
             {"label": "Financial conditions", "value": (f"credit z {w['fincond_level_US']:+.1f} · VIX z {w['vol_vix_z']:+.1f}" if w is not None else "n/a"), "sub": (f"stress z {w['fincond_stress_US']:+.1f} · MOVE z {w['vol_move_z']:+.1f}" if w is not None else "")},
             {"label": "Common trend component", "value": f"{cm.loc[d, 'cs_common_z']:+.2f}" if d in cm.index else "n/a", "sub": "market-direction part of the trend signal (date mean)"},
             {"label": "Ex-ante TE · BL 1.0 / BL 2.0", "value": f"{X.fmt_pct(r1['exante_tracking_error'], 2) if r1 is not None else 'n/a'} / {X.fmt_pct(r2['exante_tracking_error'], 2) if r2 is not None else 'n/a'}",
              "sub": f"cap binding: {'yes' if r1 is not None and bool(r1['te_cap_binding']) else 'no'} / {'yes' if r2 is not None and bool(r2['te_cap_binding']) else 'no'}"},
             {"label": "Planned turnover · cost", "value": f"{X.fmt_pct(r1['planned_turnover'], 1) if r1 is not None else 'n/a'} / {X.fmt_pct(r2['planned_turnover'], 1) if r2 is not None else 'n/a'}",
              "sub": f"{r1['planned_cost_bp']:.1f} bp / {r2['planned_cost_bp']:.1f} bp (one-way, decision close)" if r1 is not None and r2 is not None else ""}])
    for line in N.date_summary(store, d, v1, v2, t1, t2):
        st.markdown(f"- {line}", unsafe_allow_html=True)

    tabs = st.tabs(["A–D · Environment", "E–H · Weights", "I–K · Expected returns & views", "L–O · Constraints, costs, trading", "P · Changes vs previous", "Explain the decision", "Outcome of the holding period"])

    # ------------------------------------------------------------------------------------------------------- environment
    with tabs[0]:
        X.section("A · Economic environment, B · regime, C · financial conditions", "as measured at the decision close")
        if w is not None:
            env = pd.DataFrame({
                "United States": {"growth state (z)": rg_us.loc[d, "growth_state"], "inflation state (z)": rg_us.loc[d, "inflation_state"], "quadrant": ql(rg_us.loc[d, "quadrant"]),
                                  "growth surprise": rg_us.loc[d, "growth_news"], "inflation surprise": rg_us.loc[d, "inflation_news"], "policy repricing z": w["policy_repricing_USD"],
                                  "real-rate change z": w["realrate_chg_US"], "credit level z": w["fincond_level_US"], "credit stress z": w["fincond_stress_US"], "VIX z": w["vol_vix_z"], "MOVE z": w["vol_move_z"]},
                "Euro Area": {"growth state (z)": rg_ea.loc[d, "growth_state"] if d in rg_ea.index else np.nan, "inflation state (z)": rg_ea.loc[d, "inflation_state"] if d in rg_ea.index else np.nan,
                              "quadrant": ql(rg_ea.loc[d, "quadrant"]) if d in rg_ea.index else "n/a", "growth surprise": rg_ea.loc[d, "growth_news"] if d in rg_ea.index else np.nan,
                              "inflation surprise": rg_ea.loc[d, "inflation_news"] if d in rg_ea.index else np.nan, "policy repricing z": w["policy_repricing_EUR"], "real-rate change z": w["realrate_chg_EA_proxy"],
                              "credit level z": w["fincond_level_EA"], "credit stress z": w["fincond_stress_EA"], "VIX z": np.nan, "MOVE z": np.nan}})
            X.table(env.T, {c: "{:+.2f}" for c in env.index if c != "quadrant"})
        if d in b1.index:
            r = b1.loc[d]
            st.markdown(f"**BL 1.0 regime (Phase 4, four regions):** {ql(r['regime']) if isinstance(r['regime'], str) else 'unavailable'} — growth score {r['growth_score']:+.2f} ({r['growth_state']}), inflation score "
                        f"{r['inflation_score']:+.2f} ({r['inflation_state']}), strength {r['regime_strength']:.2f}; regional growth z: US {r['US_growth_z']:+.2f}, EA {r['EA_growth_z']:+.2f}, UK {r['UK_growth_z']:+.2f}, JP {r['JP_growth_z']:+.2f}.")
        X.note("States and surprises are REVISED_DATA_PROXY; market fields are point-in-time. In BL 2.0 none of these influenced the weights; in BL 1.0 the Phase 4 regime entered six sleeves' views (tab I–K).", "warn")
        X.section("D · Trend signals", "per sleeve at the decision close")
        X.table(pd.DataFrame({"composite_z": tz["composite_z"], "z̃ (BL 2.0)": tz["composite_unit"], "relative": tz["cs_relative_z"], "common": tz["cs_common_z"], "tanh T (BL 1.0)": tz["trend_score_tanh"],
                              "1m": tz["z_1m"], "3m": tz["z_3m"], "12m": tz["z_12m"], "rank": tz["cs_rank"]}),
                {c: "{:+.2f}" for c in ["composite_z", "z̃ (BL 2.0)", "relative", "common", "tanh T (BL 1.0)", "1m", "3m", "12m"]} | {"rank": "{:.0f}"})
        X.source_note(store, ["bl2_macro_regimes", "bl2_macro_wide", "p4_regime_history", "bl2_trend_signals"])

    # ------------------------------------------------------------------------------------------------------- weights
    with tabs[1]:
        X.section("E–G · Benchmark, BL 1.0 and BL 2.0 weights; H · active deviations", "")
        cats = [f"{a} · {meta.loc[a, 'ticker'].split(' ')[0]}" for a in R.ASSETS]
        c1, c2 = st.columns(2)
        c1.plotly_chart(X.grouped_bar(cats, {R.BL1: t1["target_weight"].to_numpy(), R.BL2: t2["target_weight"].to_numpy(), R.BENCHMARK: b.to_numpy()}, {k: X.strategy_color(k) for k in R.MAIN_STRATEGIES},
                                      "Target weights", ".1%", 440), use_container_width=True, key="dc_w")
        c2.plotly_chart(X.grouped_bar(cats, {R.BL1: (t1["active_weight"] * 100).to_numpy(), R.BL2: (t2["active_weight"] * 100).to_numpy()}, {R.BL1: X.strategy_color(R.BL1), R.BL2: X.strategy_color(R.BL2)},
                                      "Active weights (pp)", "+.1f", 440), use_container_width=True, key="dc_a")
        X.table(pd.DataFrame({"ETF": meta["etf_name"], "benchmark": b, "BL 1.0 pre-trade": t1["pretrade_weight"], "BL 1.0 target": t1["target_weight"], "BL 1.0 active (pp)": t1["active_weight"] * 100,
                              "BL 2.0 pre-trade": t2["pretrade_weight"], "BL 2.0 target": t2["target_weight"], "BL 2.0 active (pp)": t2["active_weight"] * 100, "BL 2.0 − BL 1.0 (pp)": (t2["target_weight"] - t1["target_weight"]) * 100}),
                {"benchmark": "{:.2%}", "BL 1.0 pre-trade": "{:.2%}", "BL 1.0 target": "{:.2%}", "BL 2.0 pre-trade": "{:.2%}", "BL 2.0 target": "{:.2%}", "BL 1.0 active (pp)": "{:+.2f}", "BL 2.0 active (pp)": "{:+.2f}", "BL 2.0 − BL 1.0 (pp)": "{:+.2f}"})
        X.source_note(store, ["p6_target_weights", "bl2_targets_long"])

    # ------------------------------------------------------------------------------------------------------- expected returns
    with tabs[2]:
        X.section("I · Equilibrium prior, J · active views, K · posterior", "both models at this date (annualized excess returns)")
        c1, c2 = st.columns(2)
        with c1:
            st.markdown(f"**BL 1.0** — {int(v1['view_status'].eq('ACTIVE').sum())} active views (trend + macro where mapped); κ = 0.30, diagonal Ω, λ = 1")
            X.table(pd.DataFrame({"Π": v1["prior_expected_return"], "T": v1["trend_T"], "M": v1["macro_M"], "S": v1["signal_S"], "Δ": v1["raw_view_adjustment"], "d": v1["posterior_adjustment"], "μ": v1["posterior_expected_return"], "status": v1["view_status"]}),
                    {"Π": "{:.2%}", "T": "{:+.2f}", "M": "{:+.2f}", "S": "{:+.2f}", "Δ": "{:+.2%}", "d": "{:+.2%}", "μ": "{:.2%}"})
        with c2:
            st.markdown(f"**BL 2.0** — {int(v2['view_status'].eq('ACTIVE').sum())} active trend views; κ = 0.416, full Ω, λ = 1; macro inactive")
            X.table(pd.DataFrame({"Π": v2["prior_Pi"], "z̃": v2["signal_unit_clipped"], "Δ rel": v2["Delta_trend_relative"], "Δ com": v2["Delta_trend_common"], "Δ": v2["Delta"], "d": v2["posterior_adjustment"], "μ": v2["posterior_expected_return"]}),
                    {"Π": "{:.2%}", "z̃": "{:+.2f}", "Δ rel": "{:+.2%}", "Δ com": "{:+.2%}", "Δ": "{:+.2%}", "d": "{:+.2%}", "μ": "{:.2%}"})
        X.plot(X.grouped_bar(SHORT, {"Π": (v2["prior_Pi"] * 1e4).to_numpy(), R.BL1: (v1["posterior_adjustment"].fillna(0) * 1e4).to_numpy(), R.BL2: (v2["posterior_adjustment"] * 1e4).to_numpy()},
                             {"Π": X.MUTED, R.BL1: X.strategy_color(R.BL1), R.BL2: X.strategy_color(R.BL2)}, "Prior Π and posterior adjustments d (bp, annualized)", ".0f", 360, orientation="v",
                             labels={"Π": "Π (prior)", R.BL1: "BL 1.0 d", R.BL2: "BL 2.0 d"}), key="dc_d")
        X.source_note(store, ["p5_views", "p5_posterior", "bl2_view_register", "bl2_posterior"])

    # ------------------------------------------------------------------------------------------------------- constraints
    with tabs[3]:
        X.section("L · Binding constraints, M · transaction costs, N · turnover, O · tracking error", "")
        rows = []
        for name, r, t in ((R.BL1, r1, t1), (R.BL2, r2, t2)):
            if r is None:
                continue
            rows.append({"Model": X.strategy_label(name), "ex-ante TE": r["exante_tracking_error"], "TE cap": r["te_cap"], "cap binding": bool(r["te_cap_binding"]), "sleeves at a box": int(r["n_bounds_binding"]),
                         "at upper": ", ".join(R.ASSET_SHORT[a] for a in R.ASSETS if bool(t.loc[a, "at_upper_bound"])) or "—", "at lower": ", ".join(R.ASSET_SHORT[a] for a in R.ASSETS if bool(t.loc[a, "at_lower_bound"])) or "—",
                         "untraded sleeves": int(r["n_notrade"]), "planned turnover": r["planned_turnover"], "planned cost (bp)": r["planned_cost_bp"], "ex-ante volatility": r["exante_volatility"],
                         "expected active return (ann.)": r["expected_active_return_annual"], "transfer coefficient": r.get("transfer_coefficient", np.nan), "cost horizon h": r.get("h_months", 1.0)})
        X.table(pd.DataFrame(rows).set_index("Model"), {"ex-ante TE": "{:.2%}", "TE cap": "{:.0%}", "planned turnover": "{:.2%}", "planned cost (bp)": "{:.2f}", "ex-ante volatility": "{:.2%}", "expected active return (ann.)": "{:+.2%}", "transfer coefficient": "{:.2f}", "cost horizon h": "{:.0f}"})
        if tr2 is not None:
            st.markdown(f"**BL 2.0 transmission:** TE of the unconstrained tilt {X.fmt_pct(tr2['te_unconstrained'], 1)} → budget-neutral {X.fmt_pct(tr2['te_budget_neutral'], 1)} → certified {X.fmt_pct(tr2['te_final'], 2)}; "
                        f"corr(a, d) {tr2['corr_final_vs_d']:.2f}; range(d) {tr2['range_d_bp']:.0f} bp vs the {tr2['band_bp']:.0f} bp no-trade band; largest sleeve unconstrained: {tr2['largest_unconstrained_sleeve']}, final: {tr2['largest_final_sleeve']}.")
        pve = store.read("p7_planned_vs_executed")
        if pve is not None:
            sub = pve[pve["decision_date"] == d].set_index("asset_class").reindex(R.ASSETS)
            if not sub.empty and sub["trade_executed"].notna().any():
                st.markdown(f"**BL 1.0 planned vs executed trades** (execution {pd.Timestamp(sub['execution_date'].iloc[0]).date()}; the difference is the one-session drift between the decision close and the execution close)")
                X.table(sub[["target_weight", "pretrade_weight_planned", "pretrade_weight_executed", "drift_t_to_tplus", "trade_planned", "trade_executed", "cost_planned_bp", "cost_executed_bp"]],
                        {"target_weight": "{:.2%}", "pretrade_weight_planned": "{:.2%}", "pretrade_weight_executed": "{:.2%}", "drift_t_to_tplus": "{:+.3%}", "trade_planned": "{:+.3%}", "trade_executed": "{:+.3%}", "cost_planned_bp": "{:.2f}", "cost_executed_bp": "{:.2f}"})
                st.caption(f"Planned one-way turnover {0.5 * sub['trade_planned'].abs().sum():.2%} vs executed {0.5 * sub['trade_executed'].abs().sum():.2%}; executed cost "
                           f"{sub['cost_executed_bp'].sum():.2f} bp vs planned {sub['cost_planned_bp'].sum():.2f} bp.")
        mf = store.read("p6_monitoring_flags")
        if mf is not None:
            mf = mf.copy()
            mf["date"] = pd.to_datetime(mf["date"])
            row = mf[mf["date"] == d]
            if not row.empty:
                r = row.iloc[0]
                flags = [f for f, v in (("turnover warning", r["turnover_flag"]), ("group exposure warning", r["group_flag"])) if isinstance(v, str) and v]
                st.caption("BL 1.0 monitoring flags at this date: " + (", ".join(f"{f} ({r['turnover_flag'] if 'turnover' in f else r['group_flag']})" for f in flags) if flags else "none") + f"; group active exposure equity-like {r['group_equitylike_active'] * 100:+.1f} pp, rates {r['group_rates_active'] * 100:+.1f} pp.")
        X.source_note(store, ["p6_portfolio_summary", "bl2_portfolio_summary", "bl2_transmission", "p7_planned_vs_executed", "p6_monitoring_flags"])

    # ------------------------------------------------------------------------------------------------------- changes
    with tabs[4]:
        X.section("P · Changes from the previous allocation", f"previous decision {prev.date() if prev is not None else 'n/a'} → this decision")
        if prev is None:
            st.info("This is the first decision date: the portfolio is deployed into the benchmark and the first tilt is decided here.")
        else:
            chg = pd.DataFrame({"BL 1.0 previous target": pt1["target_weight"], "BL 1.0 pre-trade (drifted)": t1["pretrade_weight"], "BL 1.0 new target": t1["target_weight"],
                                "BL 1.0 Δ target (pp)": (t1["target_weight"] - pt1["target_weight"]) * 100, "BL 1.0 planned trade (pp)": t1["planned_trade"] * 100,
                                "BL 2.0 previous target": pt2["target_weight"], "BL 2.0 pre-trade (drifted)": t2["pretrade_weight"], "BL 2.0 new target": t2["target_weight"],
                                "BL 2.0 Δ target (pp)": (t2["target_weight"] - pt2["target_weight"]) * 100, "BL 2.0 planned trade (pp)": t2["planned_trade"] * 100})
            X.table(chg, {c: ("{:+.2f}" if "pp" in c else "{:.2%}") for c in chg.columns})
            X.plot(X.grouped_bar(SHORT, {R.BL1: (t1["planned_trade"] * 100).to_numpy(), R.BL2: (t2["planned_trade"] * 100).to_numpy()}, {R.BL1: X.strategy_color(R.BL1), R.BL2: X.strategy_color(R.BL2)},
                                 "Planned trades at this decision (pp of NAV; the trade also absorbs the drift since the previous execution)", "+.1f", 340, orientation="v"), key="dc_trades")
            st.caption("Trade = new target − pre-trade weight, where the pre-trade weight is the previous target drifted by realized returns up to the decision close. A target that equals the "
                       "pre-trade weight means the sleeve was left untraded inside the cost band.")
        X.source_note(store, ["p6_target_weights", "bl2_targets_long"])

    # ------------------------------------------------------------------------------------------------------- explain
    with tabs[5]:
        X.section("Why did the model deviate from the benchmark on this date?", "deterministic explanations built from the published fields, sleeve by sleeve")
        X.note("<b>Reading guide.</b> Each explanation traces prior → signal → view → posterior → weight and separates what is attributable to (i) the equilibrium prior, (ii) trend, "
               "(iii) macro (BL 1.0 only), (iv) the covariance structure (cross-view spill-over in BL 1.0; Σ⁻¹ routing in the optimizer), (v) the constraints (budget, TE cap, boxes), "
               "(vi) transaction costs (no-trade band) and (vii) drift of the previous position. Where the artifacts do not identify a unique cause, the text says so.", "info")
        mp = M.view_mapping_bl1(store)
        focus = st.multiselect("ETFs to explain", R.ASSETS, default=R.ASSETS, key="dc_focus", format_func=lambda a: f"{a} — {meta.loc[a, 'etf_name']}")
        for a in focus:
            with st.expander(f"{a} — {meta.loc[a, 'etf_name']}  ·  BL 1.0 {t1.loc[a, 'active_weight'] * 100:+.2f} pp  ·  BL 2.0 {t2.loc[a, 'active_weight'] * 100:+.2f} pp", expanded=(a == focus[0])):
                c1, c2 = st.columns(2)
                with c1:
                    st.markdown(f"**BL 2.0** ({X.badge('trend views only', 'info')})", unsafe_allow_html=True)
                    for line in N.explain_bl2(store, d, a, v2, t2, r2, tr2, pt2):
                        st.markdown(f"- {line}", unsafe_allow_html=True)
                with c2:
                    st.markdown(f"**BL 1.0** ({X.badge('trend + macro views', 'info')})", unsafe_allow_html=True)
                    for line in N.explain_bl1(store, d, a, v1, t1, r1, av, pt1, mp):
                        st.markdown(f"- {line}", unsafe_allow_html=True)
        X.source_note(store, ["bl2_view_register", "bl2_posterior", "bl2_targets_long", "bl2_portfolio_summary", "p5_views", "p5_attribution_summary", "p6_target_weights", "p6_active_vs_view_sign"])

    # ------------------------------------------------------------------------------------------------------- outcome
    with tabs[6]:
        X.section("What happened next (outcome, not an input)", "net return of each strategy over the holding period that followed this decision")
        ex = trip["execution"]
        if ex is not None and not pd.isna(ex):
            rows = []
            for k in R.MAIN_STRATEGIES:
                m = M.monthly(store, k)
                mm = store.read("bl2_monthly_returns")
                per = mm[(mm["strategy"] == k) & (mm["start"] == pd.Timestamp(ex))]
                if not per.empty:
                    p = per.iloc[0]
                    rows.append({"Strategy": X.strategy_label(k), "holding period": f"{pd.Timestamp(p['start']).date()} → {pd.Timestamp(p['end']).date()}", "gross return": p["gross_return"], "cost": p["cost_term"], "net return": p["net_return"], "cash return": p["cash_return"]})
            if rows:
                X.table(pd.DataFrame(rows).set_index("Strategy"), {"gross return": "{:+.2%}", "cost": "{:+.4%}", "net return": "{:+.2%}", "cash return": "{:+.2%}"})
                r_b = next((r for r in rows if r["Strategy"] == "Strategic Benchmark"), None)
                if r_b:
                    st.caption("Active return of the period = net return − benchmark net return: " + "; ".join(f"{r['Strategy']} {r['net return'] - r_b['net return']:+.2%}" for r in rows if r["Strategy"] != "Strategic Benchmark") + ".")
            lv = M.etf_levels(store)
            if lv is not None:
                exd = M.execution_dates(store)
                nxt = exd[exd > pd.Timestamp(ex)]
                if len(nxt):
                    r_etf = (lv.loc[nxt[0]] / lv.loc[pd.Timestamp(ex)] - 1.0).reindex(R.ASSETS)
                    X.plot(X.bar_chart(SHORT, r_etf.to_numpy(), f"ETF total returns over the holding period {pd.Timestamp(ex).date()} → {nxt[0].date()}", "+.1%", 320), key="dc_out")
            st.caption("These returns were realized after the decision and never entered it. One period is one observation: it says nothing about whether the decision was 'right'.")
        X.source_note(store, ["bl2_monthly_returns", "m0_weights_history"])
