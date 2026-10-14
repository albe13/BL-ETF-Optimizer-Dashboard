"""Page 6 — Macro Regime & Economic Outlook (Phase 4.2 measurement engine of BL 2.0; Phase 4 regime of BL 1.0)."""

from __future__ import annotations

from typing import Dict, Optional

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from bldash.core import design as X, model as M, registry as R, state
from bldash.core.store import get_store

VINTAGE_WARN = ("<b>Data vintage.</b> Growth and inflation <i>states</i> and <i>surprises</i> are built from Bloomberg ACTUAL values that are revised history, against point-in-time "
                "consensus medians: they are labelled <b>REVISED_DATA_PROXY</b> and cannot be validated point-in-time. Market-based factors (OIS, yields, swaps, spreads, VIX, MOVE) "
                "are point-in-time verified end-of-day quotes. In BL 2.0 none of these fields enters the production weights; in BL 1.0 the Phase 4 regime (industrial production and "
                "CPI accelerations, also latest-revised) entered the views of six sleeves.")
FAMILY_LABEL = {"growth_US": "US growth", "growth_EA": "Euro Area growth", "inflation_US": "US inflation", "inflation_EA": "Euro Area inflation"}


def _z_word(z: float, pos: str = "above", neg: str = "below") -> str:
    if z is None or (isinstance(z, float) and np.isnan(z)):
        return "unavailable"
    a = abs(z)
    strength = "far " if a >= 2 else "clearly " if a >= 1 else "slightly " if a >= 0.3 else "about "
    return f"{strength}{pos if z > 0 else neg} normal (z {z:+.2f})" if a >= 0.3 else f"close to normal (z {z:+.2f})"


def _quadrant_fig(g: pd.DataFrame, region: str, d: pd.Timestamp) -> go.Figure:
    fig = go.Figure()
    lim = max(2.5, float(np.nanmax(np.abs(g[["growth_state", "inflation_state"]].to_numpy()))) + 0.3)
    for (x0, x1, y0, y1, q) in ((0, lim, -lim, 0, "GOLDILOCKS"), (0, lim, 0, lim, "REFLATION"), (-lim, 0, 0, lim, "STAGFLATION"), (-lim, 0, -lim, 0, "DISINFLATIONARY_SLOWDOWN")):
        fig.add_shape(type="rect", x0=x0, x1=x1, y0=y0, y1=y1, fillcolor=X.QUADRANT_COLORS[q], opacity=0.08, line_width=0, layer="below")
        fig.add_annotation(x=(x0 + x1) / 2, y=y1 - 0.25 if y1 > 0 else y0 + 0.25, text=X.QUADRANT_LABELS[q], showarrow=False, font=dict(size=11, color=X.QUADRANT_COLORS[q]))
    gg = g.dropna(subset=["growth_state", "inflation_state"])
    fig.add_trace(go.Scatter(x=gg["growth_state"], y=gg["inflation_state"], mode="lines", line=dict(color=X.GRID, width=1), hoverinfo="skip", showlegend=False))
    fig.add_trace(go.Scatter(x=gg["growth_state"], y=gg["inflation_state"], mode="markers", marker=dict(color=[X.QUADRANT_COLORS.get(q, X.MUTED) for q in gg["quadrant"]], size=7, line=dict(width=1, color=X.SURFACE)),
                             text=[i.strftime("%Y-%m") for i in gg.index], hovertemplate="%{text}: growth %{x:+.2f}, inflation %{y:+.2f}<extra></extra>", showlegend=False))
    if d in gg.index:
        fig.add_trace(go.Scatter(x=[gg.loc[d, "growth_state"]], y=[gg.loc[d, "inflation_state"]], mode="markers+text", marker=dict(color=X.INK, size=14, symbol="diamond"),
                                 text=[d.strftime("%Y-%m")], textposition="top center", textfont=dict(size=11, color=X.INK), hovertemplate="selected date<extra></extra>", showlegend=False))
    fig.add_hline(y=0, line=dict(color=X.AXIS, width=1))
    fig.add_vline(x=0, line=dict(color=X.AXIS, width=1))
    X.finish(fig, 480, f"{region}: growth × inflation state (standardized, 3-month level vs the prior 60 months)", "inflation state (z)", ".1f", "growth state (z)", hover="closest", legend=False)
    fig.update_xaxes(range=[-lim, lim], showgrid=True, gridcolor=X.GRID)
    fig.update_yaxes(range=[-lim, lim])
    return fig


def _timeline(series: Dict[str, pd.Series], title: str, labels: Dict[str, str], height: int = 260) -> go.Figure:
    fig = go.Figure()
    rows = list(series.keys())
    for i, name in enumerate(rows):
        s = series[name]
        for q in [v for v in s.unique() if isinstance(v, str)]:
            sub = s[s == q]
            fig.add_trace(go.Bar(x=sub.index, y=[1] * len(sub), base=[i] * len(sub), width=26 * 24 * 3600 * 1000, marker=dict(color=X.QUADRANT_COLORS.get(q, X.MUTED), line=dict(width=0)),
                                 name=labels.get(q, q), legendgroup=q, showlegend=(i == 0), hovertemplate=f"{name} · %{{x|%Y-%m}}: {labels.get(q, q)}<extra></extra>"))
    X.finish(fig, height, title, hover="closest")
    fig.update_yaxes(tickvals=[i + 0.5 for i in range(len(rows))], ticktext=rows, showgrid=False, range=[0, len(rows)])
    fig.update_layout(barmode="overlay", bargap=0)
    return fig


def _reconstruction(store, d: pd.Timestamp) -> None:
    W = M.macro_wide(store)
    rg = store.read("bl2_macro_regimes").copy()
    rg["date"] = pd.to_datetime(rg["date"])
    r_us = rg[(rg["region"] == "US") & (rg["date"] == d)]
    r_ea = rg[(rg["region"] == "EA") & (rg["date"] == d)]
    prev = M.previous_date(store, d)
    p_us = rg[(rg["region"] == "US") & (rg["date"] == prev)] if prev is not None else pd.DataFrame()
    p_ea = rg[(rg["region"] == "EA") & (rg["date"] == prev)] if prev is not None else pd.DataFrame()
    bl1 = M.regime_bl1(store)
    b1 = bl1.loc[d] if d in bl1.index else None
    b1p = bl1.loc[prev] if prev is not None and prev in bl1.index else None
    w = W.loc[d] if d in W.index else None
    X.section("Historical economic reconstruction", f"the macro picture as measured at the decision close of {d.date()}")
    if w is None or r_us.empty:
        st.info("No macro measurement is published for this date.")
        return
    us, ea = r_us.iloc[0], r_ea.iloc[0] if not r_ea.empty else None
    ql = lambda q: X.QUADRANT_LABELS.get(str(q), str(q))
    X.cards([{"label": "US growth · inflation state", "value": f"{us['growth_state']:+.2f} · {us['inflation_state']:+.2f}", "sub": f"quadrant: {ql(us['quadrant'])}", "color": X.QUADRANT_COLORS.get(str(us["quadrant"]), X.MUTED)},
             {"label": "Euro Area growth · inflation state", "value": (f"{ea['growth_state']:+.2f} · {ea['inflation_state']:+.2f}" if ea is not None else "n/a"), "sub": f"quadrant: {ql(ea['quadrant']) if ea is not None else 'n/a'}",
              "color": X.QUADRANT_COLORS.get(str(ea["quadrant"]), X.MUTED) if ea is not None else X.MUTED},
             {"label": "Policy repricing z(Δ3m OIS 1Y) USD · EUR", "value": f"{w['policy_repricing_USD']:+.2f} · {w['policy_repricing_EUR']:+.2f}", "sub": f"real-rate change z: US {w['realrate_chg_US']:+.2f}, EA proxy {w['realrate_chg_EA_proxy']:+.2f}"},
             {"label": "Credit level z US · EA", "value": f"{w['fincond_level_US']:+.2f} · {w['fincond_level_EA']:+.2f}", "sub": f"credit stress z: US {w['fincond_stress_US']:+.2f}, EA {w['fincond_stress_EA']:+.2f}" + (" · STRESS FLAG" if bool(us["stress_flag"]) else "")},
             {"label": "VIX z · MOVE z", "value": f"{w['vol_vix_z']:+.2f} · {w['vol_move_z']:+.2f}", "sub": "implied volatility vs the prior 60 months"},
             {"label": "BL 1.0 regime (Phase 4)", "value": ql(b1["regime"]) if b1 is not None and isinstance(b1["regime"], str) else "unavailable",
              "sub": (f"growth {b1['growth_score']:+.2f} · inflation {b1['inflation_score']:+.2f} · strength {b1['regime_strength']:.2f}" if b1 is not None else ""),
              "color": X.QUADRANT_COLORS.get(str(b1["regime"]) if b1 is not None else "nan", X.MUTED)}])
    # narrative
    lines = []
    lines.append(f"<b>Observed macroeconomic state (REVISED_DATA_PROXY).</b> US growth indicators are {_z_word(us['growth_state'])} and US inflation indicators {_z_word(us['inflation_state'])}; "
                 f"the latest US growth surprise composite is {_z_word(us['growth_news'], 'a positive surprise', 'a negative surprise')} and the inflation surprise {_z_word(us['inflation_news'], 'a positive surprise', 'a negative surprise')}.")
    if ea is not None:
        lines.append(f"In the Euro Area growth is {_z_word(ea['growth_state'])} and inflation {_z_word(ea['inflation_state'])}; growth surprise {_z_word(ea['growth_news'], 'positive', 'negative')}, "
                     f"inflation surprise {_z_word(ea['inflation_news'], 'positive', 'negative')}.")
    pol = w["policy_repricing_USD"]
    lines.append(f"<b>Market-implied expectations (point-in-time).</b> Over the prior three months USD policy expectations were repriced {'towards tighter policy' if pol > 0.3 else 'towards easier policy' if pol < -0.3 else 'little'} "
                 f"(z {pol:+.2f}; EUR z {w['policy_repricing_EUR']:+.2f}); the US 10-year real yield change is {_z_word(w['realrate_chg_US'], 'higher', 'lower')}; 2-year inflation-swap repricing US z {w['iexp_repricing_US']:+.2f}, "
                 f"EA (French proxy) z {w['iexp_repricing_EA_proxyFR']:+.2f}; 5y5y anchoring z US {w['anchoring_5y5y_US']:+.2f}, EA {w['anchoring_5y5y_EA']:+.2f}.")
    lines.append(f"<b>Financial conditions.</b> US credit spreads are {_z_word(w['fincond_level_US'], 'wider', 'tighter')} and Euro Area HY spreads {_z_word(w['fincond_level_EA'], 'wider', 'tighter')}; "
                 f"one-month spread stress z US {w['fincond_stress_US']:+.2f} / EA {w['fincond_stress_EA']:+.2f}{' (stress flag active)' if bool(us['stress_flag']) else ''}; VIX {_z_word(w['vol_vix_z'], 'elevated', 'subdued')}, MOVE {_z_word(w['vol_move_z'], 'elevated', 'subdued')}.")
    chg = []
    if not p_us.empty and str(p_us.iloc[0]["quadrant"]) != str(us["quadrant"]):
        chg.append(f"US quadrant moved from {ql(p_us.iloc[0]['quadrant'])} to {ql(us['quadrant'])}")
    if ea is not None and not p_ea.empty and str(p_ea.iloc[0]["quadrant"]) != str(ea["quadrant"]):
        chg.append(f"Euro Area quadrant moved from {ql(p_ea.iloc[0]['quadrant'])} to {ql(ea['quadrant'])}")
    if b1 is not None and b1p is not None and str(b1p["regime"]) != str(b1["regime"]):
        chg.append(f"the BL 1.0 four-region regime moved from {ql(b1p['regime'])} to {ql(b1['regime'])}")
    lines.append(f"<b>Model-generated classification.</b> BL 2.0 labels the US {ql(us['quadrant'])}" + (f" and the Euro Area {ql(ea['quadrant'])}" if ea is not None else "") +
                 f" (sign quadrant of the two states, a label only); BL 1.0's Phase 4 engine classifies the four-region acceleration regime as {ql(b1['regime']) if b1 is not None and isinstance(b1['regime'], str) else 'unavailable'}"
                 + (f" (previous month: {ql(b1p['regime'])})" if b1p is not None and isinstance(b1p['regime'], str) else "") + ". " + ("Changes since the previous decision: " + "; ".join(chg) + "." if chg else "No regime label changed since the previous decision."))
    lines.append("<b>Potential asset-class implications (general intuition, not a model input).</b> Accelerating growth with contained inflation tends to favour equity-like and credit assets; "
                 "accelerating inflation with slowing growth tends to favour inflation-linked bonds and gold over nominal bonds; widening credit spreads and elevated implied volatility signal "
                 "higher expected volatility and drawdown risk rather than a direction for next month's return. The audit of these relationships on 2019–2026 found no monthly return "
                 "predictability distinguishable from a placebo, and volatility predictability only (VIX, MOVE, spreads).")
    v1 = M.views_bl1(store, d)
    mm = v1["macro_M"].dropna()
    if len(mm):
        parts = ", ".join(f"{a} {mm[a]:+.2f}" for a in R.ASSETS if a in mm.index)
        lines.append(f"<b>Actual contribution to portfolio views at this date.</b> BL 2.0: none — no macro field enters its production views. BL 1.0: the mapped macro score M entered six sleeves' "
                     f"signals S = (T + M)/2 with M = {parts}; its contribution to each view is κσM/2 (shown on Page 5 and Page 8).")
    else:
        lines.append("<b>Actual contribution to portfolio views at this date.</b> BL 2.0: none. BL 1.0: the macro axis was unavailable on this date, so the affected views were trend-only or unavailable.")
    for l in lines:
        st.markdown(f"- {l}", unsafe_allow_html=True)
    X.source_note(store, ["bl2_macro_regimes", "bl2_macro_wide", "p4_regime_history", "p5_views"])


def render() -> None:
    store = get_store()
    d = state.current(store)
    X.page_header("Macro Regime & Economic Outlook", "Growth and inflation regimes, economic surprises, monetary policy and financial conditions as measured by the Phase 4.2 "
                  "engine — and what, if anything, they contributed to the portfolio.", "Page 6 · Model engine")
    X.note(state.date_caption(store, d))
    X.note(VINTAGE_WARN, "warn")
    _reconstruction(store, d)
    tabs = st.tabs(["A · Growth & inflation regimes", "B · Economic surprises", "C · Monetary policy & rates", "D · Financial conditions"])
    W = M.macro_wide(store)

    # ------------------------------------------------------------------------------------------------------- A
    with tabs[0]:
        X.section("Growth × inflation regimes", "standardized states, momentum, quadrant and the regime timeline")
        X.note("In the authoritative BL 2.0 configuration these states inform neither expected returns, confidence nor risk budgets (governance item M9): they are context. "
               "In BL 1.0 the Phase 4 regime (a different, four-region acceleration measure) entered six sleeves' views through a sign map.", "info")
        region = st.radio("Region (BL 2.0 measurement engine)", ["US", "EA"], horizontal=True, key="mc_region", format_func=lambda r: "United States" if r == "US" else "Euro Area")
        g = M.regimes(store, region)
        c1, c2 = st.columns(2)
        c1.plotly_chart(X.line_chart({"growth": g["growth_state"], "inflation": g["inflation_state"]}, colors={"growth": X.SLOTS[2], "inflation": X.SLOTS[1]}, labels={"growth": "growth state", "inflation": "inflation state"},
                                     yfmt=".1f", height=320, title=f"{region}: growth and inflation state (z of the 3-month level vs the prior 60 months)"), use_container_width=True, key="mc_state")
        c2.plotly_chart(X.line_chart({"growth": g["growth_momentum_12m"], "inflation": g["inflation_momentum_12m"]}, colors={"growth": X.SLOTS[2], "inflation": X.SLOTS[1]},
                                     labels={"growth": "growth momentum (12m change)", "inflation": "inflation momentum (12m change)"}, yfmt=".1f", height=320, title=f"{region}: 12-month momentum of the states"), use_container_width=True, key="mc_mom")
        X.plot(_quadrant_fig(g, "United States" if region == "US" else "Euro Area", d), key="mc_quad")
        tl = {"US (BL 2.0)": M.regimes(store, "US")["quadrant"].astype(str), "EA (BL 2.0)": M.regimes(store, "EA")["quadrant"].astype(str)}
        bl1 = M.regime_bl1(store)
        tl["BL 1.0 (4 regions)"] = bl1["regime"].astype(str)
        X.plot(_timeline(tl, "Regime timeline: BL 2.0 quadrant labels (US, EA) and the BL 1.0 four-region acceleration regime", X.QUADRANT_LABELS, 280), key="mc_tl")
        occ = M.regimes(store).groupby(["region", "quadrant"]).size().unstack(fill_value=0)
        occ.columns = [X.QUADRANT_LABELS.get(c, c) for c in occ.columns]
        c1, c2 = st.columns(2)
        c1.markdown("**Quadrant occupancy (months, BL 2.0 states)**")
        c1.dataframe(occ, width="stretch")
        fr = store.read("p4_regime_frequency")
        if fr is not None:
            c2.markdown("**BL 1.0 regime occupancy (Phase 4)**")
            X.table(fr[["regime", "months", "share_of_classified_months", "spells", "median_duration_months", "longest_duration_months"]].dropna(subset=["regime"]), {"share_of_classified_months": "{:.0%}"}, hide_index=True)
        with st.expander("BL 1.0 regime engine: four-region acceleration scores and transitions"):
            c1, c2 = st.columns(2)
            c1.plotly_chart(X.line_chart({"g": bl1["growth_score"], "i": bl1["inflation_score"]}, colors={"g": X.SLOTS[2], "i": X.SLOTS[1]}, labels={"g": "growth score", "i": "inflation score"}, yfmt=".2f", height=300,
                                         title="Growth and inflation acceleration scores (equal-weight mean of US, EA, UK, JP rolling z)"), use_container_width=True, key="mc_b1s")
            tr = store.read("p4_regime_transitions")
            if tr is not None:
                piv = tr.pivot(index="from_regime", columns="to_regime", values="count").fillna(0)
                piv.index = [X.QUADRANT_LABELS.get(i, i) for i in piv.index]
                piv.columns = [X.QUADRANT_LABELS.get(c, c) for c in piv.columns]
                c2.plotly_chart(X.heatmap(piv, "Transition counts (from row to column)", 300, zmid=None, fmt=".0f", colorscale=X.SEQUENTIAL, xlabels=list(piv.columns), ylabels=list(piv.index), text=True), use_container_width=True, key="mc_b1t")
            rc = store.read("p4_regime_changes")
            if rc is not None:
                X.table(rc[["estimation_date", "from_regime", "to_regime", "growth_score", "inflation_score", "new_regime_lasted_one_month"]], {"growth_score": "{:+.2f}", "inflation_score": "{:+.2f}"}, height=300, hide_index=True)
            st.caption("The Phase 4 engine: MA3 − MA6 acceleration of industrial production (growth) and headline CPI (inflation) month-on-month changes, standardized on the prior 60 months, "
                       "equal-weighted across the US, Euro Area, UK and Japan; the regime is the sign quadrant. It changed label 45 times in 84 months — a noisy measure (regime audit).")
        X.source_note(store, ["bl2_macro_regimes", "p4_regime_history", "p4_regime_frequency", "p4_regime_transitions"])

    # ------------------------------------------------------------------------------------------------------- B
    with tabs[1]:
        X.section("Economic surprises", "actual versus median survey, standardized; REVISED_DATA_PROXY")
        X.note("Surprise = (ACTUAL − MEDIAN SURVEY) / (1.4826 × MAD of the prior 60 surprises), winsorized at ±4; the family composite is the mean of the available components × √n "
               "(unit scale under independence). ACTUAL values are revised history, SURVEY is point-in-time: the composite is a proxy of the real-time surprise and enters only the "
               "labelled EXPERIMENTAL scenario — never the authoritative BL 2.0 portfolio.", "warn")
        fam = st.selectbox("Family", list(FAMILY_LABEL), format_func=lambda f: FAMILY_LABEL[f], key="mc_fam")
        g = M.composites(store, fam)
        c1, c2 = st.columns(2)
        f1 = X.line_chart({"news": g["news"], "ma3": g["news_ma3_diag"]}, colors={"news": X.SLOTS[0], "ma3": X.MUTED}, dash={"ma3": "dot"}, labels={"news": "surprise composite (latest)", "ma3": "3-month average (diagnostic)"},
                          yfmt=".1f", height=320, title=f"{FAMILY_LABEL[fam]}: standardized surprise")
        f1.add_hline(y=0, line=dict(color=X.AXIS, width=1))
        c1.plotly_chart(f1, use_container_width=True, key="mc_news")
        c2.plotly_chart(X.line_chart({"state": g["state"]}, colors={"state": X.SLOTS[2]}, labels={"state": "state (z of the 3-month level)"}, yfmt=".1f", height=320, title=f"{FAMILY_LABEL[fam]}: state"), use_container_width=True, key="mc_stt")
        ca = M.component_audit(store)
        if ca is not None:
            sub = ca[(ca["family"] == fam) & (ca["date"] == d)]
            st.markdown(f"**Components at the selected decision date {d.date()}** — the US and Euro Area indicators behind the composite")
            X.table(sub[["ticker", "reference_month", "availability_lag_months", "status", "surprise_std_clipped", "state_z", "scale_shadow_ratio_mad", "vintage"]].rename(
                columns={"surprise_std_clipped": "standardized surprise (clipped ±4)", "state_z": "state z", "scale_shadow_ratio_mad": "scale shadow ratio", "availability_lag_months": "availability lag (months)"}),
                {"standardized surprise (clipped ±4)": "{:+.2f}", "state z": "{:+.2f}", "scale shadow ratio": "{:.2f}"}, hide_index=True)
            st.caption("Availability lag: a release for reference month M is usable from model month M + k (never M + 0), so no release is used before its publication month.")
            inv = store.read("bl2_macro_inventory")
            if inv is not None:
                with st.expander("Indicator inventory (metadata of the series used; no values)"):
                    X.table(inv[["workbook", "ticker", "kind", "description", "n_obs", "first_obs", "last_obs", "registry_role"]], hide_index=True, height=360)
        rawkey = {"NFP TCH Index": "bl2_release_NFP_TCH", "NAPMPMI Index": "bl2_release_NAPMPMI", "CPI CHNG Index": "bl2_release_CPI_CHNG", "ECCPEST Index": "bl2_release_ECCPEST", "EUESEMU Index": "bl2_release_EUESEMU"}
        if any(store.available(k) for k in rawkey.values()):
            with st.expander("Release-level detail: actual vs median survey (raw Bloomberg values; local mode only)"):
                tick = st.selectbox("Release", [t for t, k in rawkey.items() if store.available(k)], key="mc_rel")
                rf = store.read(rawkey[tick])
                if rf is not None:
                    rf = rf.copy()
                    rf["month"] = pd.to_datetime(rf["reference_month"] + "-01")
                    rf = rf.set_index("month")
                    c1, c2 = st.columns(2)
                    c1.plotly_chart(X.line_chart({"actual": rf["actual"], "survey": rf["survey"]}, colors={"actual": X.SLOTS[0], "survey": X.MUTED}, dash={"survey": "dot"}, labels={"actual": "actual (revised)", "survey": "median survey (point-in-time)"},
                                                 yfmt=",.1f", height=300, title=f"{tick}: actual vs survey"), use_container_width=True, key="mc_rel1")
                    c2.plotly_chart(X.line_chart({"s": rf["surprise_std_clipped"], "s60": rf["surprise_std_sigma60"]}, colors={"s": X.SLOTS[0], "s60": X.SLOTS[7]}, dash={"s60": "dot"}, labels={"s": "MAD-scaled surprise (clipped)", "s60": "σ60-scaled (rejected convention)"},
                                                 yfmt=".1f", height=300, title=f"{tick}: standardized surprise under the two scalings"), use_container_width=True, key="mc_rel2")
        sh = store.read("bl2_macro_shadow")
        if sh is not None:
            with st.expander("Why a robust scale: the 2020 σ-shadow"):
                X.table(sh.set_index("ticker"), {c: "{:.2f}" for c in sh.columns if c != "ticker"})
                st.caption("Under a rolling-σ60 scaling the payroll scale inflates more than twentyfold for five years after May 2020 (max standardized surprise 47σ); the MAD scale keeps the "
                           "ratio below 2 and single surprises are winsorized at ±4.")
        X.source_note(store, ["bl2_macro_composites", "bl2_macro_component_audit", "bl2_macro_shadow"])

    # ------------------------------------------------------------------------------------------------------- C
    with tabs[2]:
        X.section("Monetary policy expectations, real rates and inflation expectations", "point-in-time market factors; diagnostics only")
        X.note("Policy repricing z(Δ3m OIS 1Y) is excluded from the views by the correlation-aware combination rule (its pre-registered information coefficient 0.04 is below 0.65 × the trend's, "
               "and it is 0.65 correlated with the Government-Bonds trend); real-rate and inflation-expectation changes are bond-trend proxies. None of them moves a weight.", "info")
        c1, c2 = st.columns(2)
        f = X.line_chart({"USD": W["policy_repricing_USD"], "EUR": W["policy_repricing_EUR"]}, colors={"USD": X.SLOTS[0], "EUR": X.SLOTS[1]}, labels={"USD": "USD", "EUR": "EUR"}, yfmt=".1f", height=320, title="OIS repricing: z of the 3-month change in the 1-year OIS rate")
        f.add_hrect(y0=1, y1=max(1.01, float(W[["policy_repricing_USD", "policy_repricing_EUR"]].max().max())), fillcolor=X.SLOTS[7], opacity=0.06, line_width=0, annotation_text="tightening repricing", annotation_font=dict(size=10, color=X.MUTED))
        f.add_hrect(y0=min(-1.01, float(W[["policy_repricing_USD", "policy_repricing_EUR"]].min().min())), y1=-1, fillcolor=X.SLOTS[0], opacity=0.06, line_width=0, annotation_text="easing repricing", annotation_position="bottom left", annotation_font=dict(size=10, color=X.MUTED))
        c1.plotly_chart(f, use_container_width=True, key="mc_pol")
        c2.plotly_chart(X.line_chart({"US": W["realrate_chg_US"], "EA": W["realrate_chg_EA_proxy"]}, colors={"US": X.SLOTS[0], "EA": X.SLOTS[1]}, dash={"EA": "dot"}, labels={"US": "US 10Y TIPS real yield", "EA": "EA proxy (Bund − 5y5y)"},
                                     yfmt=".1f", height=320, title="Real-rate change z(Δ3m)"), use_container_width=True, key="mc_rr")
        c3, c4 = st.columns(2)
        c3.plotly_chart(X.line_chart({"US": W["iexp_repricing_US"], "EA": W["iexp_repricing_EA_proxyFR"]}, colors={"US": X.SLOTS[0], "EA": X.SLOTS[1]}, dash={"EA": "dot"}, labels={"US": "US 2Y inflation swap", "EA": "EA (French CPIx proxy)"},
                                     yfmt=".1f", height=320, title="Inflation-expectation repricing z(Δ3m 2Y swap)"), use_container_width=True, key="mc_ie")
        c4.plotly_chart(X.line_chart({"US": W["anchoring_5y5y_US"], "EA": W["anchoring_5y5y_EA"]}, colors={"US": X.SLOTS[0], "EA": X.SLOTS[1]}, labels={"US": "US 5y5y", "EA": "EA 5y5y"},
                                     yfmt=".1f", height=320, title="Anchoring: z of the 5y5y inflation forward level"), use_container_width=True, key="mc_an")
        c5, c6 = st.columns(2)
        c5.plotly_chart(X.line_chart({"US": W["nominal10y_chg_US"], "EA": W["nominal10y_chg_EA"]}, colors={"US": X.SLOTS[0], "EA": X.SLOTS[1]}, labels={"US": "US Treasury 10Y", "EA": "Bund 10Y"}, yfmt=".1f", height=300,
                                     title="Yield-curve change: z(Δ3m 10-year nominal yield)"), use_container_width=True, key="mc_n10")
        c6.plotly_chart(X.line_chart({"d": W["policy_differential_chg_USD_EUR"], "s": W["policy_slope_orth_USD"]}, colors={"d": X.SLOTS[6], "s": X.MUTED}, labels={"d": "USD − EUR policy differential change", "s": "USD OIS slope (orthogonalized, diagnostic)"},
                                     yfmt=".1f", height=300, title="Policy differential and curve slope diagnostics"), use_container_width=True, key="mc_pd")
        pz = W["policy_repricing_USD"]
        cls = pd.Series(np.where(pz > 1, "tightening repricing", np.where(pz < -1, "easing repricing", "neutral")), index=pz.index)
        st.markdown(f"**Tightening / easing diagnostic (USD):** at {d.date()} the 3-month OIS repricing is **{cls.get(d, 'n/a')}** (z {pz.get(d, float('nan')):+.2f}); over the sample: "
                    + ", ".join(f"{k} {v} months" for k, v in cls.value_counts().items()) + ". Thresholds ±1 z are a display convention, not a model rule.")
        raw = M.market_raw(store)
        if raw is not None:
            with st.expander("Underlying market levels at the decision dates (raw Bloomberg observations; local mode only)"):
                c1, c2 = st.columns(2)
                c1.plotly_chart(X.line_chart({"u1": raw["ois1y_USD"], "e1": raw["ois1y_EUR"], "u3": raw["ois3m_USD"], "e3": raw["ois3m_EUR"]}, colors={"u1": X.SLOTS[0], "e1": X.SLOTS[1], "u3": X.BLUE_RAMP[300], "e3": X.SLOTS[3]},
                                             labels={"u1": "OIS 1Y USD", "e1": "OIS 1Y EUR", "u3": "OIS 3M USD", "e3": "OIS 3M EUR"}, yfmt=".1f", height=300, title="OIS rates (%)"), use_container_width=True, key="mc_raw1")
                c2.plotly_chart(X.line_chart({"r": raw["real10y_US"], "b": raw["bund10y"], "f": raw["eur5y5y"]}, colors={"r": X.SLOTS[0], "b": X.SLOTS[1], "f": X.SLOTS[6]},
                                             labels={"r": "US 10Y real (TIPS)", "b": "Bund 10Y", "f": "EUR 5y5y inflation forward"}, yfmt=".1f", height=300, title="Yields (%)"), use_container_width=True, key="mc_raw2")
        else:
            st.caption("Raw market levels are withheld in this deployment (EXCLUDE tier); standardized factors are shown.")
        ft = store.read("bl2_macro_factor_trend_corr")
        if ft is not None:
            with st.expander("Overlap with the trend composite (contemporaneous correlation)"):
                f2 = ft.set_index("factor")
                X.table(f2.loc[[f for f in f2.index if str(f).startswith(("policy", "realrate", "iexp", "nominal", "anchoring"))]], {c: "{:+.2f}" for c in f2.columns})
        X.source_note(store, ["bl2_macro_wide", "bl2_market_factors_long", "bl2_market_raw", "bl2_macro_factor_trend_corr"])

    # ------------------------------------------------------------------------------------------------------- D
    with tabs[3]:
        X.section("Financial conditions", "credit spreads, stress, implied volatility — the risk state")
        X.note("Spread levels measure prospective compensation and vulnerability (a risk state, not a one-month return forecast); spread changes measure stress. VIX and MOVE are risk "
               "variables. None enters a view, a confidence or a risk budget in the authoritative BL 2.0 configuration (governance item M8); the audit found they predict next-month "
               "volatility (ρ 0.46–0.65), which is why the proposed BL 2.1 routes them to the risk budget and the trend-view confidence rather than to return views.", "info")
        c1, c2 = st.columns(2)
        c1.plotly_chart(X.line_chart({"US": W["fincond_level_US"], "EA": W["fincond_level_EA"]}, colors={"US": X.SLOTS[0], "EA": X.SLOTS[1]}, labels={"US": "US (IG + HY OAS)", "EA": "Euro Area (HY OAS)"}, yfmt=".1f", height=320,
                                     title="Credit-spread level z (investment grade and high yield)"), use_container_width=True, key="mc_cl")
        f = X.line_chart({"US": W["fincond_stress_US"], "EA": W["fincond_stress_EA"]}, colors={"US": X.SLOTS[0], "EA": X.SLOTS[1]}, labels={"US": "US", "EA": "Euro Area"}, yfmt=".1f", height=320, title="Credit stress z(Δ1m OAS); |z| > 2 raises the stress flag")
        f.add_hline(y=2, line=dict(color=X.SLOTS[7], width=1, dash="dot"))
        f.add_hline(y=-2, line=dict(color=X.SLOTS[7], width=1, dash="dot"))
        c2.plotly_chart(f, use_container_width=True, key="mc_cs")
        c3, c4 = st.columns(2)
        c3.plotly_chart(X.line_chart({"VIX": W["vol_vix_z"], "MOVE": W["vol_move_z"]}, colors={"VIX": X.SLOTS[0], "MOVE": X.SLOTS[6]}, labels={"VIX": "VIX z", "MOVE": "MOVE z"}, yfmt=".1f", height=320, title="Implied volatility z (equity VIX, rates MOVE)"), use_container_width=True, key="mc_vol")
        rg = M.regimes(store)
        flags = rg[rg["stress_flag"]][["region", "fincond_stress"]].reset_index()
        c4.markdown("**Stress flags (|stress z| > 2)**")
        c4.dataframe(flags.rename(columns={"fincond_stress": "stress z"}), width="stretch", hide_index=True, height=320)
        raw = M.market_raw(store)
        if raw is not None:
            with st.expander("Underlying levels (raw Bloomberg observations; local mode only)"):
                c1, c2 = st.columns(2)
                c1.plotly_chart(X.line_chart({"ig": raw["ig_oas_US"], "hy": raw["hy_oas_US"], "eh": raw["hy_oas_EA"]}, colors={"ig": X.SLOTS[0], "hy": X.SLOTS[7], "eh": X.SLOTS[1]},
                                             labels={"ig": "US IG OAS (%)", "hy": "US HY OAS (%)", "eh": "EUR HY OAS (%)"}, yfmt=".1f", height=300, title="Option-adjusted spreads (%)"), use_container_width=True, key="mc_raw3")
                c2.plotly_chart(X.line_chart({"v": raw["vix"], "m": raw["move"]}, colors={"v": X.SLOTS[0], "m": X.SLOTS[6]}, labels={"v": "VIX", "m": "MOVE"}, yfmt=".0f", height=300, title="VIX and MOVE levels"), use_container_width=True, key="mc_raw4")
        ft = store.read("bl2_macro_factor_trend_corr")
        if ft is not None:
            with st.expander("Overlap with the trend composite"):
                f2 = ft.set_index("factor")
                X.table(f2.loc[[f for f in f2.index if str(f).startswith(("fincond", "vol"))]], {c: "{:+.2f}" for c in f2.columns})
                st.caption("Credit level correlates about −0.55 with the Equity trend composite: a 'risk-off' view built from spreads would restate the trend view and the equity premium already in the prior.")
        X.source_note(store, ["bl2_macro_wide", "bl2_macro_regimes", "bl2_market_raw", "bl2_macro_factor_trend_corr"])
