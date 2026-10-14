"""Page 5 — Black-Litterman Engine: prior → views → confidence → posterior → weights, at any decision date, for BL 1.0 and BL 2.0."""

from __future__ import annotations

import numpy as np
import pandas as pd
import streamlit as st

from bldash.core import design as X, model as M, registry as R, state
from bldash.core.store import get_store

SHORT = [R.ASSET_SHORT[a] for a in R.ASSETS]


def _p_matrix(active: pd.Series) -> pd.DataFrame:
    rows = [a for a in R.ASSETS if bool(active.get(a, False))]
    P = pd.DataFrame(0.0, index=rows, columns=R.ASSETS)
    for a in rows:
        P.loc[a, a] = 1.0
    return P


def _bl2_block(store, d: pd.Timestamp) -> None:
    v = M.views_bl2(store, d)
    vp = store.meta.get("view_parameters", {})
    pol = store.meta.get("policy_bl2", {})
    t = M.targets_at(store, R.BL2, d)
    b = M.benchmark_weights(store)
    ps = M.portfolio_summary(store, R.BL2)
    row = ps.loc[d] if d in ps.index else None
    tr = M.transmission_bl2(store)
    trow = tr.loc[d] if d in tr.index else None
    kappa, ic, lam = vp.get("kappa_production", {}).get("trend", float("nan")), vp.get("ic", {}).get("trend", float("nan")), vp.get("lambda", float("nan"))
    X.flow([{"h": "Equilibrium prior Π", "b": "Π = δ·Σ·b: excess returns implied by the strategic benchmark under the Ledoit-Wolf covariance (Phase 2, frozen)."},
            {"h": "Trend view", "b": f"Δ_i = σ_i · κ · clip(z̃_i, ±3) with κ = √12·IC = {kappa:.3f} (IC {ic:.2f}); z̃ = unbounded composite / 0.80, split into relative + common parts."},
            {"h": "Confidence Ω", "b": f"Ω = λ·τ·PΣP′ (full), λ = {lam:.0f}: view errors inherit the return correlations; with a view on every sleeve d = Δ/(1+λ) exactly."},
            {"h": "Posterior μ", "b": "μ = Π + ΣP′(PΣP′ + Ω)⁻¹(Q − PΠ); d = μ − Π is the posterior adjustment (relative + common components published)."},
            {"h": "Allocation", "b": f"max a′d − (δ/2)a′Σa − (12/h)c′|b + a − ŵ⁻|, h = {pol.get('h_months', 3):.0f}; TE ≤ {pol.get('te_cap', 0.02):.0%}, hybrid boxes, long-only, fully invested (certified)."}])
    X.note("<b>Production status.</b> BL 2.0's production views are trend views only. Growth and inflation surprise fields are REVISED_DATA_PROXY measurements and enter only the "
           "labelled EXPERIMENTAL scenario (shown separately below); policy repricing, real rates and financial conditions are diagnostics. No posterior change on this page is "
           "attributable to a macro signal.", "warn")
    X.section("A · Equilibrium expected returns", "annualized excess returns over EUR cash implied by the benchmark")
    dh = M.delta_history(store)
    drow = dh.loc[d] if d in dh.index else None
    c1, c2 = st.columns([2, 1])
    c1.plotly_chart(X.bar_chart(SHORT, (v["prior_Pi"] * 1e4).to_numpy(), f"Π at {d.date()} (bp, annualized)", ".0f", 320, signed=True), use_container_width=True, key="en2_pi")
    if drow is not None:
        c2.markdown(f"**Calibration at {d.date()}**")
        c2.markdown(f"- Risk aversion δ_t = {drow['delta']:.2f} = 0.30 / σ_B,t\n- Benchmark volatility σ_B,t = {drow['sigma_benchmark']:.2%}\n- Equilibrium Sharpe assumed 0.30 → benchmark premium {0.3 * drow['sigma_benchmark']:.2%}")
    X.section("B · Trend view adjustments", "signal → view: the only production view family")
    tb = pd.DataFrame({"z̃ (clipped)": v["signal_unit_clipped"], "relative z̃": v["signal_relative_unit"], "common z̃": v["signal_common_unit"], "σ (LW)": v["sigma_view"],
                       "Δ relative": v["Delta_trend_relative"], "Δ common": v["Delta_trend_common"], "Δ total": v["Delta"], "Q = Π + Δ": v["Q"]})
    X.table(tb, {"z̃ (clipped)": "{:+.2f}", "relative z̃": "{:+.2f}", "common z̃": "{:+.2f}", "σ (LW)": "{:.1%}", "Δ relative": "{:+.2%}", "Δ common": "{:+.2%}", "Δ total": "{:+.2%}", "Q = Π + Δ": "{:.2%}"})
    X.section("C · Macro view adjustments", "not active in production")
    st.markdown(f"Production Δ_macro = **0 bp** on every sleeve at {d.date()} (no macro view family is point-in-time eligible). The experimental revised-data scenario is shown in the "
                "'Experimental macro scenario' expander below and never feeds the published BL 2.0 weights.")
    X.section("D · P matrix, E · Q vector, F · Ω", "the Black-Litterman inputs at this date")
    c1, c2 = st.columns([1, 1])
    P = _p_matrix(pd.Series({a: v.loc[a, "view_status"] == "ACTIVE" for a in R.ASSETS}))
    c1.plotly_chart(X.heatmap(P, f"P: {len(P)} unit rows (one absolute view per sleeve)", 360, zmid=None, fmt=".0f", colorscale=X.SEQUENTIAL, zmin=0, zmax=1, xlabels=SHORT, ylabels=[R.ASSET_SHORT[a] for a in P.index]), use_container_width=True, key="en2_P")
    c2.plotly_chart(X.bar_chart(SHORT, (v["Q"] * 1e4).to_numpy(), "Q = Π + Δ (bp, annualized)", ".0f", 360, signed=True), use_container_width=True, key="en2_Q")
    cov = M.covariance(store, d)
    with st.expander("F · Ω / τ = λ·PΣP′ (full matrix, annualized variance units) and Σ_t correlation"):
        st.caption("τ is not specified in either model (it cancels from the posterior mean); the normalized matrix Ω/τ = λ·Σ_t is shown because P = I when all ten views are active.")
        om = lam * cov
        X.plot(X.heatmap(om * 1e4, "Ω / τ (×10⁴)", 420, zmid=None, fmt=".1f", colorscale=X.SEQUENTIAL, xlabels=SHORT, ylabels=SHORT, text=True), key="en2_om")
        corr = M.correlation_at(store, d)
        if corr is not None:
            X.plot(X.heatmap(corr, f"Correlation implied by Σ_t at {d.date()}", 420, zmid=0.0, fmt=".2f", zmin=-1, zmax=1, xlabels=SHORT, ylabels=SHORT, text=True), key="en2_corr")
    X.section("G · Posterior expected returns and H · posterior minus prior", "μ = Π + d, with d split into its relative and common trend components")
    c1, c2 = st.columns(2)
    c1.plotly_chart(X.grouped_bar(SHORT, {"Π (prior)": (v["prior_Pi"] * 1e4).to_numpy(), "μ (posterior)": (v["posterior_expected_return"] * 1e4).to_numpy()},
                                  {"Π (prior)": X.MUTED, "μ (posterior)": X.strategy_color(R.BL2)}, "Prior vs posterior (bp, annualized)", ".0f", 360, orientation="v",
                                  labels={"Π (prior)": "Π (prior)", "μ (posterior)": "μ (posterior)"}), use_container_width=True, key="en2_mu")
    c2.plotly_chart(X.grouped_bar(SHORT, {"relative": (v["adjustment_trend_relative"] * 1e4).to_numpy(), "common": (v["adjustment_trend_common"] * 1e4).to_numpy()},
                                  {"relative": X.strategy_color(R.BL2), "common": X.BLUE_RAMP[300]}, "d = μ − Π by component (bp)", ".0f", 360, orientation="v",
                                  labels={"relative": "relative trend", "common": "common trend"}), use_container_width=True, key="en2_d")
    X.section("I · Resulting active weights and J · transmission", "how much of the view survives the budget, the tracking-error cap and the boxes")
    a = t["active_weight"]
    c1, c2 = st.columns(2)
    c1.plotly_chart(X.bar_chart(SHORT, (v["posterior_adjustment"] * 1e4).to_numpy(), "Posterior adjustment d (bp)", ".0f", 320), use_container_width=True, key="en2_dbar")
    c2.plotly_chart(X.bar_chart(SHORT, (a * 100).to_numpy(), "Active weight a = w − b (pp)", "+.1f", 320), use_container_width=True, key="en2_abar")
    if trow is not None and row is not None:
        X.cards([{"label": "TE of the unconstrained tilt", "value": X.fmt_pct(trow["te_unconstrained"], 1), "sub": "Σ⁻¹d scaled by δ, no constraints"},
                 {"label": "TE after the budget constraint", "value": X.fmt_pct(trow["te_budget_neutral"], 1), "sub": "1′a = 0 imposed"},
                 {"label": "TE of the certified allocation", "value": X.fmt_pct(trow["te_final"], 2), "sub": f"cap {X.fmt_pct(row['te_cap'], 0)} binding: {'yes' if bool(row['te_cap_binding']) else 'no'}"},
                 {"label": "corr(a, d)", "value": X.fmt_num(trow["corr_final_vs_d"]), "sub": f"{int(row['n_bounds_binding'])} sleeves at a box · {int(row['n_notrade'])} untraded"},
                 {"label": "range(d) vs band", "value": f"{trow['range_d_bp']:.0f} / {trow['band_bp']:.0f} bp", "sub": "cross-sectional range of d vs the no-trade band 2·12c/h"}])
    tbl = pd.DataFrame({"Π": v["prior_Pi"], "Δ": v["Delta"], "d": v["posterior_adjustment"], "benchmark": b, "pre-trade": t["pretrade_weight"], "target": t["target_weight"], "active (pp)": a * 100,
                        "at bound": t.apply(lambda r: "upper" if bool(r["at_upper_bound"]) else "lower" if bool(r["at_lower_bound"]) else "", axis=1), "untraded": t["untraded"]})
    X.table(tbl, {"Π": "{:.2%}", "Δ": "{:+.2%}", "d": "{:+.2%}", "benchmark": "{:.2%}", "pre-trade": "{:.2%}", "target": "{:.2%}", "active (pp)": "{:+.2f}"})
    X.section("View confidence and posterior sensitivity", "what changes if the confidence assumption changes")
    c1, c2 = st.columns(2)
    pdg = store.read("bl2_posterior_diag")
    if pdg is not None:
        pdg["date"] = pd.to_datetime(pdg["date"])
        dd = pdg[pdg["date"] == d].set_index("asset_class").reindex(R.ASSETS)["posterior_adjustment"]
        c1.plotly_chart(X.grouped_bar(SHORT, {"full": (v["posterior_adjustment"] * 1e4).to_numpy(), "diag": (dd * 1e4).to_numpy()}, {"full": X.strategy_color(R.BL2), "diag": X.MUTED},
                                      "d under the full Ω (production) vs the diagonal Ω (ablation), bp", ".0f", 340, orientation="v", labels={"full": "full Ω", "diag": "diagonal Ω"}), use_container_width=True, key="en2_omcmp")
    rows = {}
    for lab, name in (("ABL_IC_EFF_LOW", "effective IC 0.03"), ("BL2_TREND_ONLY", "effective IC 0.06 (production)"), ("ABL_IC_EFF_HIGH", "effective IC 0.10")):
        w = M.ablation_targets_wide(store, lab) if lab != R.BL2 else M.targets_wide(store, R.BL2)
        if d in w.index:
            rows[name] = (w.loc[d] - b) * 100
    if rows:
        c2.plotly_chart(X.grouped_bar(SHORT, {k: s.to_numpy() for k, s in rows.items()}, {"effective IC 0.03": X.BLUE_RAMP[250], "effective IC 0.06 (production)": X.strategy_color(R.BL2), "effective IC 0.10": X.BLUE_RAMP[650]},
                                      "Active weights (pp) under three confidence levels", "+.1f", 340, orientation="v", labels={k: k for k in rows}), use_container_width=True, key="en2_ic")
    st.caption("With Ω = λτPΣP′ and λ = 1 the posterior moves exactly half-way from the prior to the view (effective IC = IC/2 = 0.06). Because the 2 % tracking-error cap and the boxes "
               "bind on most dates, halving or nearly doubling the confidence changes the allocation far less than it changes d: the portfolio expresses direction and rank, not magnitude.")
    with st.expander("Experimental macro scenario (REVISED_DATA_PROXY; never production)"):
        ve = store.read("bl2_view_register_experimental")
        pe = store.read("bl2_posterior_experimental")
        if ve is not None and pe is not None:
            ve["date"], pe["date"] = pd.to_datetime(ve["date"]), pd.to_datetime(pe["date"])
            e1 = ve[ve["date"] == d].set_index("asset_class").reindex(R.ASSETS)
            e2 = pe[pe["date"] == d].set_index("asset_class").reindex(R.ASSETS)
            X.table(pd.DataFrame({"macro news exposure (unit)": e1["macro_news_exposure_unit"], "Δ macro news": e1["Delta_macro_news"], "Δ trend": e1["Delta_trend_relative"] + e1["Delta_trend_common"],
                                  "d macro news (experimental)": e2["adjustment_macro_news"], "d total (experimental)": e2["posterior_adjustment"]}),
                    {"macro news exposure (unit)": "{:+.2f}", "Δ macro news": "{:+.2%}", "Δ trend": "{:+.2%}", "d macro news (experimental)": "{:+.2%}", "d total (experimental)": "{:+.2%}"})
            st.caption("Growth/inflation surprises are revised actuals against point-in-time consensus: a proxy that cannot be validated point-in-time. The experimental path earned −0.29 % per "
                       "year relative to production (t −0.9): macro news adds nothing detectable.")
    with st.expander("Diagnostics through time: posterior adjustments, dual-volatility ratio, transmission chain"):
        dm = M.views_bl2(store).pivot(index="date", columns="asset_class", values="posterior_adjustment")[R.ASSETS] * 1e4
        X.plot(X.heatmap(dm.T, "BL 2.0 posterior adjustment d through time (bp)", 380, fmt=".0f", ylabels=SHORT, colorbar_title="bp"), key="en2_dhm")
        sr = store.read("bl2_sigma_ratio")
        if sr is not None:
            sr["date"] = pd.to_datetime(sr["date"])
            X.plot(X.heatmap(sr.set_index("date")[R.ASSETS].T, "σ_LW / σ_EWMA-63 (the σ of the view over the σ of the signal)", 320, zmid=1.0, fmt=".2f", ylabels=SHORT), key="en2_sr")
        c1, c2 = st.columns(2)
        c1.plotly_chart(X.line_chart({"unconstrained": tr["te_unconstrained"], "budget-neutral": tr["te_budget_neutral"], "final (certified)": tr["te_final"]},
                                     colors={"unconstrained": X.MUTED, "budget-neutral": X.BLUE_RAMP[300], "final (certified)": X.strategy_color(R.BL2)},
                                     labels={"unconstrained": "unconstrained", "budget-neutral": "budget-neutral", "final (certified)": "final (certified)"}, yfmt=".1%", height=320,
                                     title="Ex-ante TE of the tilt at each stage (log scale)", log=True, hover_fmt=".2%"), use_container_width=True, key="en2_tr1")
        c2.plotly_chart(X.line_chart({"corr(a, d)": tr["corr_final_vs_d"], "bounds binding": tr["n_bounds_binding"] / 10.0}, colors={"corr(a, d)": X.strategy_color(R.BL2), "bounds binding": X.MUTED},
                                     labels={"corr(a, d)": "corr(final a, d)", "bounds binding": "share of sleeves at a box"}, yfmt=".2f", height=320, title="Transfer of information to the final tilt"), use_container_width=True, key="en2_tr2")
        st.caption(f"TE cap binding on {X.fmt_pct(tr['cap_binding'].mean(), 0)} of dates; mean {tr['n_bounds_binding'].mean():.1f} of 10 sleeves at a box; median range(d) {tr['range_d_bp'].median():.0f} bp against a band of {tr['band_bp'].iloc[0]:.0f} bp.")
    with st.expander("Synthetic strong-signal scenarios (latest frozen date; unit-scale signals; no realized returns)"):
        sc = store.read("bl2_scenarios")
        if sc is not None:
            var = st.selectbox("Variant", sorted(sc["variant"].unique()), index=sorted(sc["variant"].unique()).index("production_h3") if "production_h3" in set(sc["variant"]) else 0, key="en2_scv")
            s2 = sc[sc["variant"] == var].set_index("scenario")
            cols = [c for c in ["range_d_bp", "te_unconstrained", "te_final", "turnover", "cost_bp", "expected_active_return_bp", "n_traded", "cap_binding", "n_bounds_binding", "corr_a_d", "direction_coherent", "macro_missing"] if c in s2.columns]
            X.table(s2[cols], {"range_d_bp": "{:.0f}", "te_unconstrained": "{:.1%}", "te_final": "{:.2%}", "turnover": "{:.1%}", "cost_bp": "{:.1f}", "expected_active_return_bp": "{:.0f}", "corr_a_d": "{:.2f}"})
            acols = [c for c in s2.columns if c.startswith("a_")]
            X.plot(X.heatmap(s2[acols].rename(columns=lambda c: c[2:].replace("_", " ")).T * 100, f"Active weights (pp) by scenario — {var}", 420, fmt="+.1f"), key="en2_schm")
            st.caption("Monetary-tightening, easing and credit-stress scenarios move no weight because policy repricing and credit stress are diagnostics, not views. The missing-macro scenario shows the trend view at full strength.")
    X.source_note(store, ["bl2_view_register", "bl2_posterior", "bl2_targets_long", "bl2_transmission", "p1_covariance_long", "p2_delta_history", "bl2_scenarios"])


def _bl1_block(store, d: pd.Timestamp) -> None:
    v = M.views_bl1(store, d)
    t = M.targets_at(store, R.BL1, d)
    b = M.benchmark_weights(store)
    ps = M.portfolio_summary(store, R.BL1)
    row = ps.loc[d] if d in ps.index else None
    mp = M.view_mapping_bl1(store)
    X.flow([{"h": "Equilibrium prior Π", "b": "Π = δ·Σ·b (Phase 2), identical to BL 2.0."},
            {"h": "Signal S", "b": "S = (T + M)/2 where T = tanh(trend composite) ∈ [−1, 1] and M = sign-mapped macro regime score (tanh of growth/inflation acceleration); S = T on sleeves without a macro mapping."},
            {"h": "View", "b": "Δ_i = κ·σ_i·S_i with κ = 0.30; Q = Π + Δ; one absolute view per sleeve (unavailable if a required macro axis is missing)."},
            {"h": "Confidence Ω", "b": "Ω = λ·τ·diag(PΣP′), λ = 1 (diagonal, Phase 5): an isolated view is halved; correlated views interact (own gains 0.30–0.49)."},
            {"h": "Posterior and allocation", "b": "μ = Π + ΣP′(PΣP′ + Ω)⁻¹Δ; optimizer with h = 1 (±120 bp band), TE ≤ 2 %, hybrid boxes (Phase 6, certified)."}])
    X.note("<b>Macro in BL 1.0.</b> The Phase 4 growth × inflation acceleration regime enters the views of six sleeves through the sign map (b_growth, b_inflation): Equity, Private Equity and "
           "Real Estate (+growth), Government Bonds (−growth, −inflation), IG Credit (−inflation), Inflation Linked (−growth). Gold, Emerging Debt, Securitized and Convertibles are trend-only.", "info")
    X.section("A · Equilibrium expected returns", "shared with BL 2.0")
    X.plot(X.bar_chart(SHORT, (v["prior_return"] * 1e4).to_numpy(), f"Π at {d.date()} (bp, annualized)", ".0f", 300), key="en1_pi")
    X.section("B · Trend and C · macro view adjustments", "the two components of the BL 1.0 signal and the resulting view")
    kappa = 0.30
    tbl = pd.DataFrame({"T (trend, tanh)": v["trend_T"], "M (macro, mapped)": v["macro_M"], "S = (T+M)/2 or T": v["signal_S"], "b_growth": mp["b_growth"], "b_inflation": mp["b_inflation"],
                        "σ": v["sigma"], "Δ = κσS": v["raw_view_adjustment"], "Δ from trend": kappa * v["sigma"] * np.where(v["macro_M"].notna(), v["trend_T"] / 2.0, v["trend_T"]),
                        "Δ from macro": kappa * v["sigma"] * v["macro_M"].fillna(0.0) / 2.0, "Q": v["view_target_Q"], "status": v["view_status"].fillna("") + np.where(v["unavailability_reason"].notna(), " (" + v["unavailability_reason"].fillna("") + ")", "")})
    X.table(tbl, {"T (trend, tanh)": "{:+.2f}", "M (macro, mapped)": "{:+.2f}", "S = (T+M)/2 or T": "{:+.2f}", "σ": "{:.1%}", "Δ = κσS": "{:+.2%}", "Δ from trend": "{:+.2%}", "Δ from macro": "{:+.2%}", "Q": "{:.2%}"})
    st.caption("The trend/macro split of Δ is exact: Δ = κσ(T + M)/2 on mapped sleeves. On the sleeves where M is NaN the view is trend-only (S = T).")
    X.section("D · P matrix, E · Q vector, F · Ω", "")
    c1, c2 = st.columns(2)
    P = _p_matrix(pd.Series({a: v.loc[a, "view_status"] == "ACTIVE" for a in R.ASSETS}))
    c1.plotly_chart(X.heatmap(P, f"P: {len(P)} unit rows (active views)", 340, zmid=None, fmt=".0f", colorscale=X.SEQUENTIAL, zmin=0, zmax=1, xlabels=SHORT, ylabels=[R.ASSET_SHORT[a] for a in P.index]), use_container_width=True, key="en1_P")
    c2.plotly_chart(X.bar_chart(SHORT, (v["view_target_Q"] * 1e4).to_numpy(), "Q = Π + Δ (bp)", ".0f", 340), use_container_width=True, key="en1_Q")
    with st.expander("F · Ω / τ = diag(PΣP′) (normalized view uncertainty D, variance units) and Σ_t"):
        U = M.uncertainty_bl1(store, d)
        if U is not None:
            X.plot(X.heatmap(U * 1e4, "D = Ω / τ (×10⁴), diagonal by construction", 400, zmid=None, fmt=".1f", colorscale=X.SEQUENTIAL, xlabels=list(U.columns), ylabels=list(U.index), text=True), key="en1_D")
        cov = M.covariance(store, d)
        X.plot(X.heatmap(cov * 1e4, f"Σ_t (×10⁴) at {d.date()}", 400, zmid=None, fmt=".1f", colorscale=X.SEQUENTIAL, xlabels=SHORT, ylabels=SHORT, text=True), key="en1_cov")
    X.section("G · Posterior, H · posterior minus prior with own/cross attribution", "")
    c1, c2 = st.columns(2)
    c1.plotly_chart(X.grouped_bar(SHORT, {"Π": (v["prior_expected_return"] * 1e4).to_numpy(), "μ": (v["posterior_expected_return"] * 1e4).to_numpy()}, {"Π": X.MUTED, "μ": X.strategy_color(R.BL1)},
                                  "Prior vs posterior (bp)", ".0f", 340, orientation="v", labels={"Π": "Π (prior)", "μ": "μ (posterior)"}), use_container_width=True, key="en1_mu")
    c2.plotly_chart(X.grouped_bar(SHORT, {"own": (v["own_view_contribution"] * 1e4).to_numpy(), "cross": (v["cross_view_contribution"] * 1e4).to_numpy()}, {"own": X.strategy_color(R.BL1), "cross": X.BLUE_RAMP[300]},
                                  "d = own-view + cross-view contributions (bp)", ".0f", 340, orientation="v", labels={"own": "own view (gain K_ii × Δ_i)", "cross": "spill-over from other views"}), use_container_width=True, key="en1_d")
    X.table(pd.DataFrame({"Δ": v["raw_view_adjustment"], "own gain K_ii": v["own_gain_K_ii"], "own contribution": v["own_view_contribution"], "cross contribution": v["cross_view_contribution"], "d total": v["posterior_adjustment"],
                          "largest + cross": v["largest_positive_cross_contributor"], "largest − cross": v["largest_negative_cross_contributor"], "sign": v["sign_agreement"]}),
            {"Δ": "{:+.2%}", "own gain K_ii": "{:.2f}", "own contribution": "{:+.2%}", "cross contribution": "{:+.2%}", "d total": "{:+.2%}"})
    X.section("I · Resulting active weights and J · transmission", "")
    a = t["active_weight"]
    c1, c2 = st.columns(2)
    c1.plotly_chart(X.bar_chart(SHORT, (v["posterior_adjustment"] * 1e4).to_numpy(), "Posterior adjustment d (bp)", ".0f", 320), use_container_width=True, key="en1_dbar")
    c2.plotly_chart(X.bar_chart(SHORT, (a * 100).to_numpy(), "Active weight a = w − b (pp)", "+.1f", 320), use_container_width=True, key="en1_abar")
    if row is not None:
        X.cards([{"label": "Ex-ante TE (certified allocation)", "value": X.fmt_pct(row["exante_tracking_error"], 2), "sub": f"cap 2 % binding: {'yes' if bool(row['te_cap_binding']) else 'no'}"},
                 {"label": "Transfer coefficient", "value": X.fmt_num(row["transfer_coefficient"]), "sub": "correlation between the certified tilt and the unconstrained tilt"},
                 {"label": "Boxes binding", "value": f"{int(row['n_bounds_binding'])} of 10", "sub": f"{int(row['n_notrade'])} sleeves untraded (±120 bp band, h = 1)"},
                 {"label": "Planned turnover / cost", "value": f"{X.fmt_pct(row['planned_turnover'], 1)} · {row['planned_cost_bp']:.1f} bp", "sub": "one-way, at the decision close"},
                 {"label": "Expected active return", "value": X.fmt_bp(row["expected_active_return_annual"]), "sub": "a′d, annualized"}])
    av = M.active_vs_view_bl1(store)
    av = av[av["date"] == d].set_index("asset_class").reindex(R.ASSETS)
    tbl = pd.DataFrame({"d (bp)": av["posterior_adjustment_bp"], "unconstrained tilt": av["unconstrained_tilt"], "benchmark": b, "pre-trade": t["pretrade_weight"], "target": t["target_weight"], "active (pp)": a * 100,
                        "sign a vs d": av["sign_agreement_active_vs_adjustment"], "at bound": av["at_bound"], "traded": av["traded"]})
    X.table(tbl, {"d (bp)": "{:+.0f}", "unconstrained tilt": "{:+.1%}", "benchmark": "{:.2%}", "pre-trade": "{:.2%}", "target": "{:.2%}", "active (pp)": "{:+.2f}"})
    with st.expander("Diagnostics through time: posterior adjustments, sign reversals, binding constraints"):
        dm = M.views_bl1(store).pivot(index="date", columns="asset_class", values="posterior_adjustment")[R.ASSETS] * 1e4
        X.plot(X.heatmap(dm.T, "BL 1.0 posterior adjustment d through time (bp)", 380, fmt=".0f", ylabels=SHORT, colorbar_title="bp"), key="en1_dhm")
        sr = store.read("p5_sign_reversal_aggregate")
        if sr is not None:
            st.markdown("**Sign reversals (d opposite to Δ) — Phase 5 monitoring**")
            X.table(sr, hide_index=True)
        bs = store.read("p6_binding_summary")
        if bs is not None:
            X.table(bs, {"share_dates_binding": "{:.1%}", "share_at_lower": "{:.1%}", "share_at_upper": "{:.1%}"}, hide_index=True)
    X.source_note(store, ["p5_views", "p5_posterior", "p5_attribution_summary", "p5_view_mapping", "p6_target_weights", "p6_portfolio_summary", "p6_active_vs_view_sign", "p1_covariance_long"])


def render() -> None:
    store = get_store()
    d = state.current(store)
    X.page_header("Black-Litterman Engine", "Equilibrium prior + views + confidence → posterior expected returns → optimal portfolio weights, reconstructed from the published artifacts "
                  "for any decision date.", "Page 5 · Model engine")
    X.note(state.date_caption(store, d))
    model = st.segmented_control("Model", [R.BL2, R.BL1], default=R.BL2, format_func=X.strategy_label, key="en_model") or R.BL2
    if model == R.BL2:
        _bl2_block(store, d)
    else:
        _bl1_block(store, d)
    X.section("Side by side at this date", "BL 1.0 vs BL 2.0: view, posterior adjustment and active weight")
    v1, v2 = M.views_bl1(store, d), M.views_bl2(store, d)
    t1, t2 = M.targets_at(store, R.BL1, d), M.targets_at(store, R.BL2, d)
    cmp = pd.DataFrame({"BL 1.0 Δ": v1["raw_view_adjustment"], "BL 1.0 d": v1["posterior_adjustment"], "BL 1.0 active (pp)": t1["active_weight"] * 100,
                        "BL 2.0 Δ": v2["Delta"], "BL 2.0 d": v2["posterior_adjustment"], "BL 2.0 active (pp)": t2["active_weight"] * 100})
    X.table(cmp, {"BL 1.0 Δ": "{:+.2%}", "BL 1.0 d": "{:+.2%}", "BL 1.0 active (pp)": "{:+.2f}", "BL 2.0 Δ": "{:+.2%}", "BL 2.0 d": "{:+.2%}", "BL 2.0 active (pp)": "{:+.2f}"})
    X.plot(X.grouped_bar(SHORT, {R.BL1: (v1["posterior_adjustment"] * 1e4).to_numpy(), R.BL2: (v2["posterior_adjustment"] * 1e4).to_numpy()}, {R.BL1: X.strategy_color(R.BL1), R.BL2: X.strategy_color(R.BL2)},
                         "Posterior adjustment d (bp, annualized): BL 1.0 vs BL 2.0", ".0f", 340, orientation="v"), key="en_cmp")
    st.caption("BL 2.0's adjustments are several times larger (κ = 0.416 on a unit-variance signal vs κ = 0.30 on a tanh-bounded score with sd 0.55); the allocation differences are "
               "smaller than the view differences because the same mandate (2 % TE cap, boxes) constrains both.")
