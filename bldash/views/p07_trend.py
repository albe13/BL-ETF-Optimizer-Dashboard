"""Page 7 — Trend & Signal Analytics (Phase 3 measurement shared by BL 1.0 and BL 2.0; Phase 3.2 representation of BL 2.0)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from bldash.core import design as X, model as M, registry as R, state
from bldash.core.store import get_store

SHORT = [R.ASSET_SHORT[a] for a in R.ASSETS]


def _strength(z: float) -> str:
    a = abs(z)
    return "strong" if a >= 1.5 else "moderate" if a >= 0.75 else "weak" if a >= 0.25 else "neutral"


def render() -> None:
    store = get_store()
    d = state.current(store)
    X.page_header("Trend & Signal Analytics", "How trend is measured on the ten ETFs, how it becomes a Black-Litterman view in each model, and how the optimizer responds.", "Page 7 · Model engine")
    X.note(state.date_caption(store, d))
    vp = store.meta.get("view_parameters", {})
    kappa, ic = vp.get("kappa_production", {}).get("trend", float("nan")), vp.get("ic", {}).get("trend", float("nan"))
    X.flow([{"h": "1 · Measure", "b": "For each ETF and horizon h ∈ {1, 3, 12} months: X_h = R_h − c_h, the trailing EUR total return in excess of the realized EUR cash return."},
            {"h": "2 · Standardize", "b": "z_h = X_h / (σ_EWMA63 · √(h/12)); composite_z = mean of the three legs. A standardized trend score, not a return forecast."},
            {"h": "3 · Decompose", "b": "composite_z = common component (date mean across sleeves, market direction) + relative component (the sleeve's deviation)."},
            {"h": "4 · Represent", "b": "BL 1.0: T = tanh(composite) ∈ [−1, 1]; BL 2.0: z̃ = composite_z / 0.80 (unit variance), clipped at ±3 only inside the view."},
            {"h": "5 · View", "b": f"BL 1.0: Δ = 0.30·σ·S with S = (T + M)/2. BL 2.0: Δ = σ·κ·z̃ with κ = √12·IC = {kappa:.3f} (IC {ic:.2f}), split into relative + common parts."},
            {"h": "6 · Confidence & optimizer", "b": "λ = 1 halves the view (d = Δ/2 in BL 2.0); the 2 % TE cap, boxes and the cost band then size the position."}])
    X.note("A trend score measures the strength of the recent excess-return trend in volatility units. It is <b>not</b> an expected return, a probability or a weight: the view magnitude "
           "comes from the calibration constant κ (an assumed information coefficient), the sleeve volatility and the confidence λ.", "info")

    t2 = M.trend_bl2(store, d)
    t1 = M.trend_bl1(store, d)
    X.section("Signals at the selected decision date", f"{d.date()} — the three horizon legs, the composite, its decomposition and both model representations")
    tb = pd.DataFrame({"z 1m": t2["z_1m"], "z 3m": t2["z_3m"], "z 12m": t2["z_12m"], "composite_z": t2["composite_z"], "relative": t2["cs_relative_z"], "common": t2["cs_common_z"],
                       "z̃ = composite/0.80 (BL 2.0)": t2["composite_unit"], "tanh score (BL 1.0 T)": t2["trend_score_tanh"], "directional (−1…+1)": t2["directional_trend"],
                       "σ EWMA-63": t2["volatility"], "rank (1 = strongest)": t2["cs_rank"], "strength": t2["composite_z"].map(_strength), "status": t2["status"]})
    X.table(tb, {"z 1m": "{:+.2f}", "z 3m": "{:+.2f}", "z 12m": "{:+.2f}", "composite_z": "{:+.2f}", "relative": "{:+.2f}", "common": "{:+.2f}", "z̃ = composite/0.80 (BL 2.0)": "{:+.2f}",
                 "tanh score (BL 1.0 T)": "{:+.2f}", "directional (−1…+1)": "{:+.2f}", "σ EWMA-63": "{:.1%}", "rank (1 = strongest)": "{:.0f}"})
    cm = M.trend_common(store)
    if d in cm.index:
        st.caption(f"Common component at this date: {cm.loc[d, 'cs_common_z']:+.2f} (equal-weight) / {cm.loc[d, 'cs_common_z_benchmark_weighted']:+.2f} (benchmark-weighted); cross-sectional dispersion "
                   f"{cm.loc[d, 'cs_dispersion_z']:.2f}; {int(cm.loc[d, 'n_valid_sleeves'])} of 10 sleeves valid ({cm.loc[d, 'cs_status']}). The strength labels (neutral < 0.25 ≤ weak < 0.75 ≤ moderate < 1.5 ≤ strong) are a display convention.")

    tabs = st.tabs(["A · Trend heatmap", "B · Time series", "C · Common vs relative", "D · Signal ranking", "E · Trend vs active weight", "F · Evolution by ETF", "Persistence & calibration"])
    with tabs[0]:
        field = st.selectbox("Field", ["composite_z", "cs_relative_z", "composite_unit", "trend_score_tanh", "z_1m", "z_3m", "z_12m"], key="tr_field",
                             format_func=lambda f: {"composite_z": "composite_z (unbounded, equal-weight mean of the legs)", "cs_relative_z": "relative component", "composite_unit": "z̃ = composite_z / 0.80 (BL 2.0 view input)",
                                                     "trend_score_tanh": "tanh score (BL 1.0 view input T)", "z_1m": "1-month leg", "z_3m": "3-month leg", "z_12m": "12-month leg"}[f])
        Wf = M.trend_wide(store, field)
        X.plot(X.heatmap(Wf.T, f"{field} by sleeve and decision date", 430, fmt="+.2f", ylabels=SHORT, zmin=-3 if field != "trend_score_tanh" else -1, zmax=3 if field != "trend_score_tanh" else 1), key="tr_hm")
        X.source_note(store, ["bl2_trend_signals"])
    with tabs[1]:
        c1, c2 = st.columns([1, 3])
        sl = c1.selectbox("Sleeve", R.ASSETS, key="tr_sleeve")
        g = M.trend_bl2(store)
        g = g[g["asset_class"] == sl].set_index("estimation_date")
        fig = X.line_chart({"z1": g["z_1m"], "z3": g["z_3m"], "z12": g["z_12m"], "c": g["composite_z"], "t": g["trend_score_tanh"]},
                           colors={"z1": X.BLUE_RAMP[250], "z3": X.BLUE_RAMP[400], "z12": X.BLUE_RAMP[650], "c": X.strategy_color(R.BL2), "t": X.strategy_color(R.BL1)}, dash={"t": "dot"},
                           labels={"z1": "1-month leg", "z3": "3-month leg", "z12": "12-month leg", "c": "composite_z (BL 2.0 basis)", "t": "tanh score (BL 1.0 T)"}, yfmt=".1f", height=400, title=f"{sl}: horizon legs, composite and the two representations", width=1.6)
        fig.add_hline(y=0, line=dict(color=X.AXIS, width=1))
        fig.add_vline(x=d, line=dict(color=X.INK2, width=1, dash="dash"))
        X.plot(fig, key="tr_ts")
        all_c = M.trend_wide(store, "composite_z")
        X.plot(X.line_chart({a: all_c[a] for a in R.ASSETS}, colors=X.ETF_COLORS, labels={a: R.ASSET_SHORT[a] for a in R.ASSETS}, yfmt=".1f", height=400, title="composite_z of all ten sleeves", width=1.3), key="tr_all")
        X.source_note(store, ["bl2_trend_signals"])
    with tabs[2]:
        c1, c2 = st.columns(2)
        f = X.line_chart({"eq": cm["cs_common_z"], "bw": cm["cs_common_z_benchmark_weighted"], "disp": cm["cs_dispersion_z"]}, colors={"eq": X.strategy_color(R.BL2), "bw": X.BLUE_RAMP[300], "disp": X.MUTED}, dash={"disp": "dot"},
                         labels={"eq": "common (equal-weight mean)", "bw": "common (benchmark-weighted)", "disp": "cross-sectional dispersion"}, yfmt=".1f", height=360, title="Common (market-direction) component through time")
        f.add_hline(y=0, line=dict(color=X.AXIS, width=1))
        c1.plotly_chart(f, use_container_width=True, key="tr_cm")
        c2.plotly_chart(X.grouped_bar(SHORT, {"rel": t2["cs_relative_z"].to_numpy(), "com": t2["cs_common_z"].to_numpy()}, {"rel": X.strategy_color(R.BL2), "com": X.BLUE_RAMP[300]},
                                      f"Decomposition at {d.date()}: composite = relative + common", "+.2f", 360, orientation="v", labels={"rel": "relative component", "com": "common component"}), use_container_width=True, key="tr_dec")
        sc = store.read("bl2_trend_scale")
        if sc:
            s = sc["scale"]
            st.markdown(f"The common component explains **{s['common_variance_share']:.0%}** of the variance of composite_z (common sd {s['common_sd']:.2f}, relative pooled sd {s['relative_pooled_sd']:.2f}). "
                        "A fully invested, budget-neutral optimizer annihilates any constant added to every sleeve's expected return; a σ-scaled common component survives only as a tilt "
                        "toward high-volatility sleeves (Gold, Convertibles). In production κ_common = κ_relative; the relative-only ablation (common withheld) was better on the sample but "
                        "was not selected because that choice would be performance-based.")
        X.source_note(store, ["bl2_trend_common", "bl2_trend_scale"])
    with tabs[3]:
        rk = t2[["composite_z", "cs_rank"]].sort_values("composite_z", ascending=False)
        c1, c2 = st.columns([1, 1])
        c1.plotly_chart(X.bar_chart([f"{R.ASSET_SHORT[a]}  (#{int(rk.loc[a, 'cs_rank'])})" for a in rk.index], rk["composite_z"].to_numpy(), f"Signal ranking at {d.date()} (composite_z)", "+.2f", 380, orientation="h"), use_container_width=True, key="tr_rank")
        rw = M.trend_wide(store, "cs_rank")
        c2.plotly_chart(X.heatmap(rw.T, "Cross-sectional rank through time (1 = strongest trend)", 380, zmid=None, fmt=".0f", colorscale=X.SEQUENTIAL[::-1] if False else [[0, X.BLUE_RAMP[700]], [1, X.BLUE_RAMP[100]]], zmin=1, zmax=10, ylabels=SHORT), use_container_width=True, key="tr_rankhm")
        st.caption("Ranks are diagnostics (governance item T6): the views use cardinal z values, not ranks. The Phase 8 audit found a cross-sectional rank IC of about 0.10 that disappears once "
                   "the persistent sleeve means are removed — the ranking mostly reflects durable tilts, not month-to-month timing.")
        X.source_note(store, ["bl2_trend_signals"])
    with tabs[4]:
        a2 = M.targets_at(store, R.BL2, d)["active_weight"] * 100
        a1 = M.targets_at(store, R.BL1, d)["active_weight"] * 100
        fig = go.Figure()
        for name, a, col in ((R.BL2, a2, X.strategy_color(R.BL2)), (R.BL1, a1, X.strategy_color(R.BL1))):
            fig.add_trace(go.Scatter(x=t2["composite_z"], y=a, mode="markers+text", text=SHORT, textposition="top center", textfont=dict(size=10, color=col), name=X.strategy_label(name),
                                     marker=dict(color=col, size=10, line=dict(width=1, color=X.SURFACE)), hovertemplate=f"{X.strategy_label(name)} · %{{text}}: z %{{x:+.2f}}, active %{{y:+.1f}} pp<extra></extra>"))
        fig.add_hline(y=0, line=dict(color=X.AXIS, width=1))
        fig.add_vline(x=0, line=dict(color=X.AXIS, width=1))
        X.finish(fig, 420, f"Trend score vs active weight at {d.date()}", "active weight (pp)", "+.0f", "composite_z", hover="closest")
        X.plot(fig, key="tr_scatter")
        W2 = M.targets_wide(store, R.BL2)
        W1 = M.targets_wide(store, R.BL1)
        b = M.benchmark_weights(store)
        Z = M.trend_wide(store, "composite_z")
        corr2 = pd.Series({dd: np.corrcoef(Z.loc[dd], (W2.loc[dd] - b))[0, 1] for dd in Z.index if dd in W2.index and np.nanstd(W2.loc[dd] - b) > 0})
        corr1 = pd.Series({dd: np.corrcoef(Z.loc[dd], (W1.loc[dd] - b))[0, 1] for dd in Z.index if dd in W1.index and np.nanstd(W1.loc[dd] - b) > 0})
        f = X.line_chart({R.BL2: corr2, R.BL1: corr1}, yfmt=".2f", height=320, title="Cross-sectional correlation between composite_z and the active weights, per decision date (display derivation)")
        f.add_hline(y=0, line=dict(color=X.AXIS, width=1))
        X.plot(f, key="tr_corr")
        st.caption("The active weights of both models are positively related to the trend score on most dates, but the relation is bent by the position boxes, the tracking-error cap and the "
                   "no-trade band (BL 1.0 also carries a macro component and the drifted previous position). The correlation is a presentation diagnostic computed from stored signals and weights.")
        X.source_note(store, ["bl2_trend_signals", "bl2_targets_long", "p6_target_weights"])
    with tabs[5]:
        Z = M.trend_wide(store, "composite_z")
        for i in range(0, len(R.ASSETS), 2):
            cols = st.columns(2)
            for col, a in zip(cols, R.ASSETS[i:i + 2]):
                s = Z[a]
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=s.index, y=s.clip(lower=0), mode="lines", line=dict(width=0), fill="tozeroy", fillcolor="rgba(42,120,214,0.18)", hoverinfo="skip", showlegend=False))
                fig.add_trace(go.Scatter(x=s.index, y=s.clip(upper=0), mode="lines", line=dict(width=0), fill="tozeroy", fillcolor="rgba(208,59,59,0.18)", hoverinfo="skip", showlegend=False))
                fig.add_trace(go.Scatter(x=s.index, y=s, mode="lines", line=dict(color=X.ETF_COLORS[a], width=1.8), name=a, hovertemplate="%{x|%Y-%m}: %{y:+.2f}<extra></extra>", showlegend=False))
                fig.add_hline(y=0, line=dict(color=X.AXIS, width=1))
                X.finish(fig, 220, f"{a} · composite_z", "", "+.1f", legend=False)
                fig.update_layout(margin=dict(l=6, r=6, t=30, b=6))
                col.plotly_chart(fig, use_container_width=True, key=f"tr_ev_{a}")
        X.source_note(store, ["bl2_trend_signals"])
    with tabs[6]:
        sc = store.read("bl2_trend_scale")
        c1, c2 = st.columns(2)
        if sc:
            s = sc["scale"]
            c1.markdown("**Scale and persistence (BL 2.0 scale diagnostics)**")
            c1.dataframe(pd.DataFrame({"statistic": ["pooled sd of composite_z", "pooled sd of z̃ (÷0.80)", "theoretical scale constant", "common sd", "common variance share", "relative pooled sd", "mean lag-1 autocorrelation",
                                                     "expected sign-run length (months)", "share |composite_z| > 1", "share |z̃| > 3 (clipped)"],
                                       "value": [s["composite_pooled_sd"], s["composite_unit_pooled_sd"], s["theoretical_scale_constant"], s["common_sd"], s["common_variance_share"], s["relative_pooled_sd"], s["mean_ar1"],
                                                 s["expected_sign_run_months"], s["share_abs_composite_gt_1"], s["share_abs_unit_gt_3"]]}).style.format({"value": "{:.3f}"}), width="stretch", hide_index=True)
            ar = pd.Series(s["composite_ar1_by_sleeve"]).reindex(R.ASSETS)
            c2.plotly_chart(X.bar_chart(SHORT, ar.to_numpy(), "Lag-1 autocorrelation of composite_z by sleeve", ".2f", 340, signed=False), use_container_width=True, key="tr_ar1")
            st.caption(f"Signal persistence of about {s['expected_sign_run_months']:.1f} months anchors BL 2.0's cost horizon h = 3 (the band amortizes the one-way cost over the signal's expected life).")
        sp = store.read("p3_signal_persistence")
        if sp is not None:
            with st.expander("BL 1.0 trend-score persistence (Phase 3 diagnostics)"):
                X.table(sp.set_index("asset_class").reindex(R.ASSETS)[["lag1_autocorr_trend_score", "median_abs_monthly_change", "positive_to_negative_transitions", "negative_to_positive_transitions", "months_positive", "months_negative", "avg_positive_spell_months", "avg_negative_spell_months"]],
                        {"lag1_autocorr_trend_score": "{:.2f}", "median_abs_monthly_change": "{:.2f}", "avg_positive_spell_months": "{:.1f}", "avg_negative_spell_months": "{:.1f}"})
        st.markdown("**How the view magnitude is calibrated.** Grinold's refined forecast gives the expected excess return of a unit-variance signal as IC × σ per period; annualized over "
                    f"one-month views this is Δ = √12 · IC · σ · z̃, so κ = √12 · IC = {kappa:.3f} for the literature trend IC of {ic:.2f}. With λ = 1 the posterior uses half of Δ, an effective IC of "
                    f"{vp.get('effective_ic_production', {}).get('trend', 0.06):.2f}. BL 1.0's κ = 0.30 on a tanh score with sd 0.55 corresponds to an implied monthly IC of "
                    f"{vp.get('bl1_comparison', {}).get('implied_monthly_ic', float('nan')):.3f} (half of it after the same halving) — about 2.5 times smaller than BL 2.0's.")
        st.markdown("**How the optimizer responds.** The posterior adjustment d enters a benchmark-relative mean-variance problem with a transaction-cost band (±120 bp of expected return in BL 1.0 with "
                    "h = 1; ±40 bp in BL 2.0 with h = 3), a 2 % ex-ante tracking-error cap and hybrid position boxes. At BL 2.0's view scale the cap binds on about 43 % of dates and almost seven sleeves "
                    "sit at a box: the portfolio expresses direction and rank rather than magnitude (Page 5).")
        hz = store.read("bl2_trend_horizon_3_6_12")
        if hz is not None and sc:
            st.caption(f"Pre-registered alternative horizon set {{3, 6, 12}} (diagnostic only): correlation with the production composite {sc['horizon_set_correlations'].get('3_6_12', float('nan')):.3f}.")
        md = store.read("bl2_trend_metadata")
        if md:
            with st.expander("Signal semantics and cash provenance (published metadata)"):
                st.json({k: md[k] for k in ("semantics", "decomposition", "production_field", "convention_field", "return_basis", "horizons_months", "sigma_source") if k in md}, expanded=True)
        X.source_note(store, ["bl2_trend_scale", "p3_signal_persistence", "bl2_view_parameters", "bl2_trend_metadata"])
