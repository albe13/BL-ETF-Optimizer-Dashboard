"""Page 10 — Limitations & Future Improvements (final page)."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from bldash.core import design as X, model as M, registry as R
from bldash.core.store import get_store


def _items(items, kind="info"):
    for h, b in items:
        st.markdown(f"- **{h}** {b}")


def render() -> None:
    store = get_store()
    X.page_header("Limitations & Future Improvements", "What the evidence does and does not support for BL 1.0 and BL 2.0, the proposed BL 2.1 research roadmap with its status labels, "
                  "and the open governance decisions.", "Page 10 · Reference")
    X.badges([("IMPLEMENTED = in a frozen run", "good"), ("PROPOSED = research recommendation, not built", "info"), ("EXPERIMENTAL = built, labelled, never production", "warn"),
              ("NOT VALIDATED = no point-in-time or out-of-sample evidence", "bad")])
    st.markdown("")

    # ------------------------------------------------------------------------------------------------------- A
    X.section("A · BL 1.0 limitations", "frozen Phases 1–7; independent economic audit (Phase 8)")
    _items([
        ("Weak incremental trend evidence.", "The views add +0.49 % per year over an equilibrium-only optimizer with the same costs and limits (p ≈ 0.06, not significant after multiple-comparison correction). "
         "Sleeve-level correlations of the trend score with next-month excess returns lie between −0.12 and +0.02 (pooled t −0.66); the cross-sectional rank IC of about 0.10 vanishes once persistent sleeve means are removed."),
        ("Weak macro predictive evidence.", "The Phase 4 regime score shows no return predictability even on latest-revised data (rank IC −0.05); the macro-only counterfactual earns less than equilibrium-only. "
         "Its inputs are revised history, so point-in-time validity is incomplete by construction."),
        ("Signal attenuation.", "tanh bounding, the (T + M)/2 average, κ = 0.30 (an implied monthly IC of 0.048, halved again by λ = 1) and the ±120 bp cost band compress the signal: on an average date 2.2 of 10 sleeves trade "
         "and 78 % of sleeve-dates carry the previous position."),
        ("Structural portfolio tilts.", "The active return is a persistent exposure (Equity +8.1 pp, Gold +2.3 pp, Government Bonds −6.8 pp on average; ten-sleeve regression alpha ≈ 0). Two thirds of the gap to the benchmark "
         "is earned by cost-band drift without any view; an ex-post constant-weight portfolio slightly beats the strategy. Timing added −0.14 % per year."),
        ("View calibration uncertainty.", "κ, λ and the diagonal Ω are structural conventions; they are not identifiable from 84 dates. 8.3 % of views reversed sign through cross-view spill-over (3.6 % of strong views)."),
        ("Regime mapping limitations.", "The exposure sign map was unsupported for growth; the four-region acceleration measure changed label 45 times in 78 classified months; Real Estate was persistently sold as a high-beta hedge "
         "despite a positive own view."),
        ("Sample and power.", "83 months spanning one equity bull market, one rates shock and one gold rally, on the history the methodology was designed on. Minimum detectable active return at 80 % power: 1.15 % per year "
         "vs the benchmark, 0.71 % vs equilibrium-only (about 15 years of data would be needed to confirm the observed +0.49 %)."),
        ("Execution realism.", "Total-return levels are valuation proxies, not executable quotes; a uniform 10 bp one-way cost with no market impact; execution at the next common session; executed turnover exceeds planned "
         "turnover because the whole target vector is executed after one session of drift."),
    ])

    # ------------------------------------------------------------------------------------------------------- B
    X.section("B · BL 2.0 limitations", "published research configuration, parameters provisional")
    s = M.summary(store)
    b2, b1 = s.loc[R.BL2], s.loc[R.BL1]
    _items([
        ("Macro views inactive in production.", "No macro family is point-in-time eligible: growth/inflation surprises are REVISED_DATA_PROXY, policy repricing is spanned by the Government-Bonds trend, states have no monthly return "
         "mechanism. The macro architecture is a measurement and diagnostics layer; the experimental revised-data scenario earned −0.29 % per year relative to production."),
        ("Revised-data limitations.", "ACTUAL macro values are revised history against point-in-time consensus; EA inflation-expectation repricing uses a French swap proxy; EA real rates a Bund − 5y5y proxy; EUR IG OAS is used in changes "
         "only; no release calendar is registered (conservative lags, never M+0)."),
        ("Limited statistical power.", f"BL 2.0 − BL 1.0 = {X.fmt_pct(M.comparison(store, R.BL2, R.BL1)['mean_annualized'], 2, sign=True)} per year (HAC t {X.fmt_num(M.comparison(store, R.BL2, R.BL1)['t_statistic'])}); the value of its views over "
         "equilibrium-only is +0.38 % per year (t 0.9). Nothing is distinguishable from noise, and nothing on 2019–2026 is independent of development."),
        ("View calibration uncertainty.", "IC_lit 0.12 and λ = 1 are literature and structural assumptions (effective-IC range 0.03–0.10 published as ablations); κ_common = κ_relative is a pre-registered choice although the relative-only "
         "ablation is better on the sample; the unit-scale constant 0.80 and the ±3 clip are conventions."),
        ("Elevated turnover.", f"{X.fmt_pct(b2['annual_turnover'], 0)} one-way per year vs {X.fmt_pct(b1['annual_turnover'], 0)} for BL 1.0 (7×): +34 pp from the h = 3 band, +32 pp from the 2.5× larger views (exact Shapley); 85 % of trades follow month-to-month "
         "view changes, half are reversed within three months, and no class of trade agrees with the next month's relative return more often than a coin toss."),
        ("Transaction costs.", f"Cost drag {X.fmt_bp(b2['cost_drag_annualized'])} per year at the assumed 10 bp (28 bp at 20 bp one-way); the band is irrelevant at the view scale (range(d) ≈ 700 bp vs 80 bp); actual broker costs and spreads are unknown "
         "to the project; euro costs are proportional illustrations."),
        ("Structural Equity / Government-Bonds tilt.", "Average active Equity +6.9 pp (88 % of dates), Government Bonds −7.1 pp — the same tilt the equilibrium-only rule produces (+6.8 / −2.7 pp). It is a property of cost-aware "
         "optimization in a bull decade, not of the views, and BL 2.0 does not remove it."),
        ("Tracking-error constraints.", f"At the literature view scale the 2 % cap binds on 43 % of dates and 6.8 of 10 sleeves sit at a box: the portfolio expresses direction and rank, not magnitude; realized TE {X.fmt_pct(b2['tracking_error_realized'])} "
         f"vs {X.fmt_pct(b1['tracking_error_realized'])}. Either the IC assumption or the limits must be revisited by governance (B5/O3) — not decided."),
        ("Unproven incremental alpha.", "The excess return over the benchmark (+1.35 % per year) is static exposure (+1.51 % static vs −0.04 % dynamic); no predictive test survives; the only confirmatory route is forward, "
         "out-of-sample monitoring against the frozen specification."),
    ])

    # ------------------------------------------------------------------------------------------------------- C
    X.section("C · BL 2.1 research roadmap", "from the regime-to-allocation and turnover audit (2026-10-13): CONDITIONALLY READY for technical design")
    road = pd.DataFrame([
        {"Improvement": "Regime-aware risk management", "What": "Time-varying tracking-error cap TE_max,t = clip(2 % · exp(−β_R r_t), 1.5 %, 2.5 %) from a smoothed point-in-time risk state (VIX, MOVE, credit levels); effective cost rises with stress", "Evidence": "VIX/MOVE/credit predict next-month volatility (ρ 0.46–0.65) and drawdowns", "Status": "PROPOSED"},
        {"Improvement": "Regime-conditioned confidence", "What": "λ_t = clip(exp(β_C c_t), 0.5, 3) on the trend view only, from a credit-condition composite; never a multiplier on the signal", "Evidence": "trend IC 0.23 in tight-spread states vs −0.04 wide (1 of 8 conditioners; weak)", "Status": "PROPOSED — shadow rule for 36 forward months first"},
        {"Improvement": "Improved turnover management", "What": "Trade toward the certified optimum at a rate θ_t = 1 − AR1(d) (≈ 0.47) — the aim-portfolio form of Gârleanu–Pedersen; round-trip amortization with a measured holding period H (kc = 24/H)", "Evidence": "θ = ½ halves turnover (70 → 37 %) with corr(a, d) unchanged at 0.60 (in-sample; not a performance case)", "Status": "PROPOSED"},
        {"Improvement": "Planned-trade execution", "What": "Execute the planned trade vector rather than the full target after one session of drift", "Evidence": "−1.4 pp (BL 2.0) / −3.3 pp (BL 1.0) turnover, costless", "Status": "PROPOSED"},
        {"Improvement": "Better transaction-cost estimation", "What": "Register measured spreads and a commission schedule; sensitivity 5–30 bp already published", "Evidence": "no ETF volume or spread data in the repository", "Status": "PROPOSED — data required"},
        {"Improvement": "First-print macroeconomic vintages", "What": "Register first-print ACTUAL series (or a forward revision monitor) so surprise views can be point-in-time validated", "Evidence": "surprise fields are REVISED_DATA_PROXY today", "Status": "NOT VALIDATED — gating item G-RT-4/5"},
        {"Improvement": "Improved geographic exposure mapping", "What": "Registered index country weights to map US/EA factors to the sleeves (conservative conventions used experimentally)", "Evidence": "experimental region weights only", "Status": "PROPOSED — data required"},
        {"Improvement": "Relative regime views", "What": "Direction-only, EWMA-smoothed growth-news views at IC ≤ 0.03", "Evidence": "no next-month predictability distinguishable from a placebo (190 tests)", "Status": "EXPERIMENTAL — gated, not production"},
        {"Improvement": "Live point-in-time monitoring", "What": "Score each new month's signals, views and returns against the frozen specification; revision monitor for macro inputs", "Evidence": "the only confirmatory route", "Status": "PROPOSED"},
        {"Improvement": "Forward out-of-sample validation", "What": "Pre-registered forward test of the frozen BL 2.0 specification; no parameter re-tuned on 2019–2026", "Evidence": "in-sample tests cannot confirm or refute an edge", "Status": "PROPOSED"},
    ])
    X.table(road, hide_index=True, height=420)
    st.caption("Rejected for BL 2.1: regime return views in production, regime multipliers on the trend score, turnover regularisers or hard caps chosen for their in-sample return, re-tuning κ, h or θ on the frozen backtest.")

    # ------------------------------------------------------------------------------------------------------- D
    X.section("D · Research status", "")
    st.markdown("**Technical validation.** BL 1.0: Phases 1–7 frozen with hash-pinned contracts, 24 blocking backtest tests, certified optimizer solves on all 84 dates, byte-identical rebuilds. "
                "BL 2.0: 109/109 validation checks, byte-identical fresh-process rebuild, Phase 3 legs reproduced bitwise, BL 1.0 results reproduced exactly inside the BL 2.0 ledger, 84 tests; "
                "5,874 frozen BL 1.0 files re-hashed unchanged. This dashboard re-verifies every artifact it reads against those pins.")
    st.markdown("**Economic interpretation.** Both models earn a persistent-exposure return (Equity and Gold financed by Government Bonds) that a cost-aware no-view rule largely captures; "
                "the incremental value of the views is positive, small, fragile and trend-driven; the macro block adds no measurable information in either generation; BL 2.0 is more "
                "internally consistent (Grinold-scaled views, full Ω, exact transmission diagnostics) but not better.")
    st.markdown("**Predictive limitations.** No signal family has time-series predictive power on the sample; the trend ranking IC is a persistent-tilt artefact; regimes predict volatility, not returns; "
                "nothing on 2019–2026 is independent of model development.")
    st.markdown("**Open governance decisions (require the user).** T1 horizon set; T4 κ_common = κ_relative vs relative-only; T7 minimum valid sleeves; T10 scale constant; B5 central IC; B6 R and ρ; B7 λ; O1 h; "
                "O3 TE-cap relaxation vs IC reduction; M3 point-in-time validity of surprise views; G4 materiality threshold; G6 index country weights and release calendars; G7 EUR HICPx swap; "
                "regime/turnover audit items G-RT-3 (execution convention), G-RT-7 (time-varying cap), G-RT-8 (confidence rule), G-RT-10 (trading rule), G-RT-11 (cost multiplier), G-RT-13 (IC vs mandate).")
    bl2s = store.meta.get("bl2_status", {})
    if bl2s.get("not_claims"):
        st.markdown("**Published non-claims of the BL 2.0 run:** " + "; ".join(bl2s["not_claims"]) + ".")

    # ------------------------------------------------------------------------------------------------------- E
    X.section("E · Next steps", "a concise roadmap")
    X.steps([
        {"n": "1", "h": "Ratify or amend the provisional BL 2.0 parameters", "b": "Decide the open items (horizons, κ_common, IC, λ, h, cap vs IC) by versioned amendment; never on realized 2019–2026 performance."},
        {"n": "2", "h": "Register the missing data", "b": "First-print macro vintages or a revision monitor; index country weights; measured spreads and commissions; a release calendar."},
        {"n": "3", "h": "Technical design of BL 2.1", "b": "Risk-budget and confidence rules, persistence-anchored trading rate, planned-trade execution; engineer the exact certificate for cap-and-box-saturated solves."},
        {"n": "4", "h": "Shadow and forward testing", "b": "Run BL 2.1 rules as shadow for 36 months; pre-register the forward out-of-sample protocol for the frozen BL 2.0 specification; score monthly."},
        {"n": "5", "h": "Deployment governance", "b": "Private Streamlit deployment of this dashboard after the Bloomberg licence review of derived data; raw levels stay excluded."},
        {"n": "6", "h": "Keep the audit discipline", "b": "Every change is a new frozen run that supersedes the previous one; every claim is traceable to a hash-pinned artifact."},
    ], cols=3)
    with st.expander("Validation, data quality and audit trail of the published runs"):
        v = store.read("bl2_validation")
        if v:
            c1, c2, c3 = st.columns(3)
            c1.metric("BL 2.0 validation checks", f"{v.get('checks_passed')} / {v.get('checks_total')}")
            c2.metric("BL 1.0 blocking backtest tests", f"{sum(1 for x in store.meta.get('bl1_status', {}).get('blocking_tests', {}).values() if x == 'PASS')} / {len(store.meta.get('bl1_status', {}).get('blocking_tests', {}))}")
            c3.metric("Artifacts verified by this dashboard", f"{store.report.get('files', {}).get('checked', 'see start-up')}")
            chk = pd.DataFrame(v.get("checks", []))
            if not chk.empty:
                cat = st.multiselect("Categories", sorted(chk["category"].unique()), default=sorted(chk["category"].unique()), key="lim_cat")
                X.table(chk[chk["category"].isin(cat)][["category", "status", "blocking", "check", "value", "detail"]].astype(str), hide_index=True, height=360)
        for key, lab in (("p7_data_completeness", "Phase 7 data completeness"), ("p7_timing_validation", "Phase 7 timing validation"), ("p7_lookahead_test", "Phase 7 look-ahead test")):
            t = store.read(key)
            if t is not None:
                st.markdown(f"**{lab}**")
                X.table(t.astype(str), hide_index=True, height=200)
        inv = store.read("bl2_macro_inventory")
        nn = store.read("bl2_macro_nonnumeric")
        if inv is not None:
            st.markdown(f"**Macro data quality:** {len(inv)} series inventoried; non-numeric tokens mapped to missing: {len(nn) if nn is not None else 'n/a'}.")
        st.markdown("**Data-quality warnings (BL 2.0 run):** surprise/state fields REVISED_DATA_PROXY; EUR IG OAS definition unverified (changes only); RR10CDE, FDIUFDYO, GDP, EA PMIs, EUNGEZY, NAPMNEWO excluded; "
                    "EA inflation-expectation and real-rate proxies; valuation proxies are EUR total-return levels, not executable quotes.")
        rep = store.report
        st.markdown("**Artifact verification at start-up (this session)**")
        X.table(pd.DataFrame(rep.get("sources", {})).T[["label", "run_id", "contract_status", "manifest_ok", "files_in_manifest", "ok"]].astype(str))
    X.source_note(store, ["bl2_validation", "bl2_summary_metrics", "bl2_comparison_tests"])
