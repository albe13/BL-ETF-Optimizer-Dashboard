"""Deterministic, data-grounded explanations of a historical decision (Page 8). Every sentence is built from published fields; where a
contribution cannot be identified uniquely from the artifacts the text says so instead of inventing a cause."""

from __future__ import annotations

from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from bldash.core import design as X, model as M, registry as R

KAPPA_BL1 = 0.30


def _pos(x: float) -> str:
    return "overweight" if x > 1e-9 else "underweight" if x < -1e-9 else "neutral"


def _label(z: float) -> str:
    a = abs(z)
    return "strong" if a >= 1.5 else "moderate" if a >= 0.75 else "weak" if a >= 0.25 else "near-neutral"


def _rank_of(series: pd.Series, a: str) -> int:
    return int(series.rank(ascending=False)[a])


def explain_bl2(store, d: pd.Timestamp, a: str, v: pd.DataFrame, t: pd.DataFrame, ps_row: Optional[pd.Series], tr_row: Optional[pd.Series], prev_t: Optional[pd.DataFrame]) -> List[str]:
    r, w = v.loc[a], t.loc[a]
    act = float(w["active_weight"]) * 100
    pre = float(w["pretrade_weight"]) * 100
    b = float(w["benchmark_weight"]) * 100
    tgt = float(w["target_weight"]) * 100
    out = []
    out.append(f"<b>Prior.</b> Equilibrium excess return Π = {X.fmt_pct(r['prior_Pi'])} (rank {_rank_of(v['prior_Pi'], a)} of 10 among the sleeves).")
    z = float(r["signal_unit_clipped"])
    out.append(f"<b>Signal.</b> Unit-scale trend z̃ = {z:+.2f} ({_label(z)} {'positive' if z > 0 else 'negative' if z < 0 else ''} trend{'; clipped at ±3' if bool(r['clipped']) else ''}): "
               f"relative component {float(r['signal_relative_unit']):+.2f}, common (market-direction) component {float(r['signal_common_unit']):+.2f}.")
    out.append(f"<b>View.</b> Δ = σ·κ·z̃ = {X.fmt_bp(r['Delta'], 0, sign=True)} (σ_LW {X.fmt_pct(r['sigma_view'], 1)}; relative part {X.fmt_bp(r['Delta_trend_relative'], 0, sign=True)}, common part "
               f"{X.fmt_bp(r['Delta_trend_common'], 0, sign=True)}); Q = Π + Δ = {X.fmt_pct(r['Q'])}. No macro view enters production (Δ_macro = 0).")
    out.append(f"<b>Posterior.</b> d = μ − Π = {X.fmt_bp(r['posterior_adjustment'], 0, sign=True)} = Δ/(1+λ) with λ = 1 (the full-Ω structure makes this exact; no cross-view sign reversal).")
    status = "at the upper box" if bool(w["at_upper_bound"]) else "at the lower box" if bool(w["at_lower_bound"]) else "untraded (inside the cost band)" if bool(w["untraded"]) else "interior"
    cap = bool(ps_row["te_cap_binding"]) if ps_row is not None else False
    out.append(f"<b>Allocation.</b> Pre-trade (drifted) weight {pre:.2f} % → target {tgt:.2f} % vs benchmark {b:.2f} %: <b>{_pos(act)} {act:+.2f} pp</b>; planned trade "
               f"{float(w['planned_trade']) * 100:+.2f} pp; constraint status: {status}; TE cap {'binding' if cap else 'not binding'} on this date"
               + (f"; {int(ps_row['n_bounds_binding'])} of 10 sleeves at a box, {int(ps_row['n_notrade'])} untraded" if ps_row is not None else "") + ".")
    # attribution sentence
    same = (act > 0 and r["posterior_adjustment"] > 0) or (act < 0 and r["posterior_adjustment"] < 0)
    if bool(w["untraded"]) and abs(float(w["planned_trade"])) < 1e-9:
        out.append("<b>Why.</b> The position was <b>left at its drifted previous weight</b>: the expected gain from moving it did not cover the transaction-cost band (2·12c/h = 80 bp of expected "
                   "return), so this date's active weight reflects <b>portfolio drift and the previous decision</b>, not a new view-driven trade.")
    elif bool(w["at_upper_bound"]) or bool(w["at_lower_bound"]):
        out.append(f"<b>Why.</b> The {'positive' if r['posterior_adjustment'] > 0 else 'negative'} view pushes the sleeve to its <b>position limit</b> ({'upper' if bool(w['at_upper_bound']) else 'lower'} box "
                   f"{float(w['upper_bound' if bool(w['at_upper_bound']) else 'lower_bound']) * 100:+.1f} pp): the <b>direction</b> comes from the view, the <b>magnitude</b> from the approved limit, not from the size of Δ."
                   + ("" if same else " The sign of the active weight does not match the sign of d: the budget constraint and the tracking-error cap route expected returns through the covariance "
                      "structure, so a unique attribution of this position to its own view is not identifiable from the artifacts."))
    elif same:
        out.append(f"<b>Why.</b> The {_pos(act)} is consistent with the sign of the view (d {X.fmt_bp(r['posterior_adjustment'], 0, sign=True)}); its size is interior to the boxes and shaped jointly by the "
                   f"risk penalty (δ/2·a′Σa), the tracking-error cap{' (binding)' if cap else ''} and the cost band. The exact share of each constraint is not published for this date.")
    else:
        out.append(f"<b>Why.</b> The active weight ({act:+.2f} pp) has the <b>opposite sign</b> to the own view (d {X.fmt_bp(r['posterior_adjustment'], 0, sign=True)}): under the budget constraint (1′a = 0) and the "
                   "tracking-error cap the optimizer funds the strongest views by selling the sleeves with the lowest marginal risk contribution (Σ⁻¹ routing); Government Bonds and IG Credit are the usual "
                   "funding legs. A unique causal attribution to a single signal is not identifiable.")
    if prev_t is not None and a in prev_t.index:
        chg = (tgt - float(prev_t.loc[a, "target_weight"]) * 100)
        out.append(f"<b>Change from the previous decision.</b> Target moved {chg:+.2f} pp (previous target {float(prev_t.loc[a, 'target_weight']) * 100:.2f} %); the planned trade of {float(w['planned_trade']) * 100:+.2f} pp "
                   f"also absorbs the drift {(pre - float(prev_t.loc[a, 'target_weight']) * 100):+.2f} pp of the position since the previous execution.")
    return out


def explain_bl1(store, d: pd.Timestamp, a: str, v: pd.DataFrame, t: pd.DataFrame, ps_row: Optional[pd.Series], av: Optional[pd.DataFrame], prev_t: Optional[pd.DataFrame], mp: pd.DataFrame) -> List[str]:
    r, w = v.loc[a], t.loc[a]
    act = float(w["active_weight"]) * 100
    pre = float(w["pretrade_weight"]) * 100
    b = float(w["benchmark_weight"]) * 100
    tgt = float(w["target_weight"]) * 100
    out = []
    out.append(f"<b>Prior.</b> Π = {X.fmt_pct(r['prior_expected_return'])} (shared with BL 2.0).")
    if str(r.get("view_status")) != "ACTIVE":
        out.append(f"<b>Signal and view.</b> No active view on this date ({r.get('unavailability_reason')}): the posterior equals the prior for this sleeve; any active weight comes from drift, "
                   "the other views through the covariance structure, and the constraints.")
    else:
        T, Mm, S = float(r["trend_T"]), r["macro_M"], float(r["signal_S"])
        mapped = not pd.isna(Mm)
        sig = f"<b>Signal.</b> Trend T = tanh(composite) = {T:+.2f} ({_label(T / 0.55)} on the bounded scale)"
        if mapped:
            sig += (f"; macro M = {float(Mm):+.2f} from the Phase 4 regime through the sign map (growth {int(mp.loc[a, 'b_growth']):+d}, inflation {int(mp.loc[a, 'b_inflation']):+d}); "
                    f"S = (T + M)/2 = {S:+.2f}.")
        else:
            sig += "; this sleeve has no macro mapping, so S = T."
        out.append(sig)
        delta = float(r["raw_view_adjustment"])
        dt = KAPPA_BL1 * float(r["sigma"]) * (T / 2.0 if mapped else T)
        dm = KAPPA_BL1 * float(r["sigma"]) * (float(Mm) / 2.0) if mapped else 0.0
        out.append(f"<b>View.</b> Δ = κσS = {X.fmt_bp(delta, 0, sign=True)} with κ = 0.30 and σ {X.fmt_pct(r['sigma'], 1)}: trend contributes {X.fmt_bp(dt, 0, sign=True)}"
                   + (f", macro {X.fmt_bp(dm, 0, sign=True)}" if mapped else "") + f"; Q = {X.fmt_pct(r['view_target_Q'])}.")
        own, cross = float(r["own_view_contribution"]), float(r["cross_view_contribution"])
        out.append(f"<b>Posterior.</b> d = {X.fmt_bp(r['posterior_adjustment'], 0, sign=True)} = own view {X.fmt_bp(own, 0, sign=True)} (gain K_ii {float(r['own_gain_K_ii']):.2f} × Δ) + spill-over from the other "
                   f"views {X.fmt_bp(cross, 0, sign=True)} through Σ (largest +: {r['largest_positive_cross_contributor']}; largest −: {r['largest_negative_cross_contributor']}); sign of d vs Δ: {r['sign_agreement']}.")
    status = "at the upper box" if bool(w["at_upper_bound"]) else "at the lower box" if bool(w["at_lower_bound"]) else "untraded (inside the ±120 bp band)" if bool(w["untraded"]) else "interior"
    cap = bool(ps_row["te_cap_binding"]) if ps_row is not None else False
    out.append(f"<b>Allocation.</b> Planned pre-trade weight {pre:.2f} % → target {tgt:.2f} % vs benchmark {b:.2f} %: <b>{_pos(act)} {act:+.2f} pp</b>; planned trade {float(w['planned_trade']) * 100:+.2f} pp; "
               f"status: {status}; TE cap {'binding' if cap else 'not binding'}" + (f"; transfer coefficient {float(ps_row['transfer_coefficient']):.2f}" if ps_row is not None and not pd.isna(ps_row.get('transfer_coefficient', np.nan)) else "") + ".")
    dval = float(r["posterior_adjustment"]) if not pd.isna(r.get("posterior_adjustment", np.nan)) else 0.0
    same = (act > 0 and dval > 0) or (act < 0 and dval < 0)
    unc = None
    if av is not None and a in av.index:
        unc = float(av.loc[a, "unconstrained_tilt"])
    if bool(w["untraded"]) and abs(float(w["planned_trade"])) < 1e-9:
        out.append("<b>Why.</b> Left <b>untraded</b>: with h = 1 the cost band is ±120 bp of expected return around the budget multiplier, wider than most posterior adjustments; the active weight "
                   "is the <b>drift of the previous position</b> inside the band (the Phase 8 audit attributes most of BL 1.0's persistent Equity overweight to this mechanism), not a new decision.")
    elif bool(w["at_upper_bound"]) or bool(w["at_lower_bound"]):
        out.append(f"<b>Why.</b> The view drives the sleeve to its <b>position limit</b>: direction from the view, magnitude from the approved box ({float(w['upper_bound' if bool(w['at_upper_bound']) else 'lower_bound']) * 100:+.1f} pp)."
                   + ("" if same else " The active sign differs from the own view's sign, so the position is set by the other views and the constraints rather than by this sleeve's signal."))
    elif same:
        out.append(f"<b>Why.</b> The {_pos(act)} agrees with the own posterior view (d {X.fmt_bp(dval, 0, sign=True)})" + (f"; the unconstrained tilt would have been {unc * 100:+.1f} pp" if unc is not None else "")
                   + "; the realized size reflects the risk penalty, the cap and the cost band jointly (shares not identifiable from the artifacts).")
    else:
        out.append(f"<b>Why.</b> The position ({act:+.2f} pp) runs <b>against</b> the own view (d {X.fmt_bp(dval, 0, sign=True)})" + (f"; the unconstrained tilt was {unc * 100:+.1f} pp" if unc is not None else "")
                   + ": budget neutrality, the Σ⁻¹ routing of the other views and the constraints dominate this sleeve; no unique single-signal attribution exists.")
    if prev_t is not None and a in prev_t.index:
        chg = (tgt - float(prev_t.loc[a, "target_weight"]) * 100)
        out.append(f"<b>Change from the previous decision.</b> Target moved {chg:+.2f} pp from {float(prev_t.loc[a, 'target_weight']) * 100:.2f} %.")
    return out


def date_summary(store, d: pd.Timestamp, v1: pd.DataFrame, v2: pd.DataFrame, t1: pd.DataFrame, t2: pd.DataFrame) -> List[str]:
    a1, a2 = t1["active_weight"] * 100, t2["active_weight"] * 100
    agree = [a for a in R.ASSETS if np.sign(a1[a]) == np.sign(a2[a]) and abs(a1[a]) > 0.5 and abs(a2[a]) > 0.5]
    opp = [a for a in R.ASSETS if np.sign(a1[a]) == -np.sign(a2[a]) and abs(a1[a]) > 0.5 and abs(a2[a]) > 0.5]
    top2 = a2.abs().sort_values(ascending=False).index[:3]
    top1 = a1.abs().sort_values(ascending=False).index[:3]
    out = [f"<b>BL 2.0</b> deviates most on {', '.join(f'{a} ({a2[a]:+.1f} pp)' for a in top2)}; <b>BL 1.0</b> on {', '.join(f'{a} ({a1[a]:+.1f} pp)' for a in top1)}.",
           f"Same direction (|active| > 0.5 pp in both): {', '.join(agree) or 'none'}. Opposite direction: {', '.join(opp) or 'none'}."]
    m = v1["macro_M"].dropna()
    if len(m):
        strongest = m.abs().idxmax()
        out.append(f"BL 1.0's macro component is non-zero on {len(m)} sleeves (largest |M| on {strongest}: {m[strongest]:+.2f}); BL 2.0 uses no macro input.")
    else:
        out.append("BL 1.0's macro axis was unavailable on this date; BL 2.0 uses no macro input.")
    corr = np.corrcoef(v2["posterior_adjustment"].astype(float), v1["posterior_adjustment"].fillna(0).astype(float))[0, 1]
    out.append(f"Cross-sectional correlation between the two models' posterior adjustments: {corr:+.2f}; between their active weights: {np.corrcoef(a1, a2)[0, 1]:+.2f}.")
    return out
