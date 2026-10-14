"""Page 2 — Portfolio Allocation."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from bldash.core import design as X, model as M, registry as R, state
from bldash.core.store import get_store

MATERIAL_PP = 2.0


def _active_pp(w: pd.Series, b: pd.Series) -> pd.Series:
    return (w - b) * 100.0


def render() -> None:
    store = get_store()
    d = state.current(store)
    X.page_header("Portfolio Allocation", "Target weights of the ten ETFs for BL 1.0, BL 2.0 and the Strategic Benchmark at any historical rebalance date, with active "
                  "weights in percentage points and the full allocation history.", "Page 2 · Portfolio")
    X.note(state.date_caption(store, d))
    meta = M.etf_meta(store)
    b = M.benchmark_weights(store)
    t1, t2 = M.targets_at(store, R.BL1, d), M.targets_at(store, R.BL2, d)
    w1, w2 = t1["target_weight"], t2["target_weight"]
    a1, a2 = _active_pp(w1, b), _active_pp(w2, b)
    tabs = st.tabs(["Allocation at the selected date", "Allocation history", "Persistent exposures"])

    # ------------------------------------------------------------------------------------------------------- tab 1
    with tabs[0]:
        X.section("A · Grouped allocation", f"decision of {d.date()} — benchmark, BL 1.0 and BL 2.0 target weights")
        cats = [f"{a} · {meta.loc[a, 'ticker'].split(' ')[0]}" for a in R.ASSETS]
        X.plot(X.grouped_bar(cats, {R.BL1: w1.to_numpy(), R.BL2: w2.to_numpy(), R.BENCHMARK: b.to_numpy()}, {k: X.strategy_color(k) for k in R.MAIN_STRATEGIES},
                             yfmt=".1%", height=470), key="al_grouped")
        X.section("B · Active-weight divergence", "target minus benchmark, percentage points; bars beyond ±2 pp are material tilts")
        X.plot(X.grouped_bar(cats, {R.BL1: a1.to_numpy(), R.BL2: a2.to_numpy()}, {R.BL1: X.strategy_color(R.BL1), R.BL2: X.strategy_color(R.BL2)}, yfmt="+.1f", height=440),
               key="al_active")
        over1 = [a for a in R.ASSETS if a1[a] >= MATERIAL_PP]
        under1 = [a for a in R.ASSETS if a1[a] <= -MATERIAL_PP]
        over2 = [a for a in R.ASSETS if a2[a] >= MATERIAL_PP]
        under2 = [a for a in R.ASSETS if a2[a] <= -MATERIAL_PP]
        c1, c2 = st.columns(2)
        with c1:
            st.markdown(f"**BL 1.0** — material overweights: {', '.join(f'{a} ({a1[a]:+.1f} pp)' for a in over1) or 'none'}; underweights: "
                        f"{', '.join(f'{a} ({a1[a]:+.1f} pp)' for a in under1) or 'none'}.")
        with c2:
            st.markdown(f"**BL 2.0** — material overweights: {', '.join(f'{a} ({a2[a]:+.1f} pp)' for a in over2) or 'none'}; underweights: "
                        f"{', '.join(f'{a} ({a2[a]:+.1f} pp)' for a in under2) or 'none'}.")
        X.section("E · Allocation comparison table", "weights, active weights, bounds and trading status at the decision date")
        flag = lambda r: ("at upper bound" if bool(r["at_upper_bound"]) else "at lower bound" if bool(r["at_lower_bound"]) else "untraded" if bool(r["untraded"]) else "interior")
        tbl = pd.DataFrame({"ETF": meta["etf_name"], "Group": meta["group"], "Benchmark": b, "BL 1.0 target": w1, "BL 1.0 active (pp)": a1, "BL 1.0 status": t1.apply(flag, axis=1),
                            "BL 2.0 target": w2, "BL 2.0 active (pp)": a2, "BL 2.0 status": t2.apply(flag, axis=1), "BL 2.0 − BL 1.0 (pp)": (w2 - w1) * 100,
                            "BL 2.0 lower / upper (pp)": [f"{t2.loc[a, 'lower_bound'] * 100:+.1f} / {t2.loc[a, 'upper_bound'] * 100:+.1f}" for a in R.ASSETS]})
        X.table(tbl, {"Benchmark": "{:.2%}", "BL 1.0 target": "{:.2%}", "BL 2.0 target": "{:.2%}", "BL 1.0 active (pp)": "{:+.2f}", "BL 2.0 active (pp)": "{:+.2f}",
                      "BL 2.0 − BL 1.0 (pp)": "{:+.2f}"}, height=420)
        st.caption("Bounds are the approved hybrid active-weight limits u_i = min(10 pp, max(2 pp, 0.5 × b_i)), truncated by long-only; 'untraded' means the "
                   "optimizer left the pre-trade (drifted) weight unchanged because the expected gain did not cover the transaction-cost band.")
        with st.expander("Executed post-trade weights at the execution date (after costs and the one-session drift)"):
            trip = state.triplet(store, d)
            ex = trip["execution"]
            if ex is not None and not pd.isna(ex):
                rows = {}
                for k in R.MAIN_STRATEGIES:
                    we = M.executed_wide(store, k)
                    if pd.Timestamp(ex) in we.index:
                        rows[X.strategy_label(k)] = we.loc[pd.Timestamp(ex)]
                if rows:
                    X.table(pd.DataFrame(rows), {c: "{:.2%}" for c in rows})
                    st.caption(f"Executed at {pd.Timestamp(ex).date()}: post-trade weights equal the targets of the post-cost NAV (exact self-financing rebalance).")
            else:
                st.info("No execution record for this decision date.")
        X.source_note(store, ["p6_target_weights", "bl2_targets_long", "bl2_weights_executed"])

    # ------------------------------------------------------------------------------------------------------- tab 2
    with tabs[1]:
        W1, W2 = M.targets_wide(store, R.BL1), M.targets_wide(store, R.BL2)
        X.section("C · Historical stacked allocation", "target weights at every decision date")
        c1, c2 = st.columns(2)
        c1.plotly_chart(X.stacked_area(W1, "BL 1.0 target weights", 400), use_container_width=True, key="al_stack1")
        c2.plotly_chart(X.stacked_area(W2, "BL 2.0 target weights", 400), use_container_width=True, key="al_stack2")
        X.section("D · Historical active-weight heatmap", "target − benchmark in percentage points (blue = overweight, red = underweight)")
        A1, A2 = (W1.sub(b.to_numpy(), axis=1) * 100).T, (W2.sub(b.to_numpy(), axis=1) * 100).T
        lim = float(max(A1.abs().max().max(), A2.abs().max().max()))
        X.plot(X.heatmap(A1, "BL 1.0 active weights (pp)", 380, fmt="+.1f", zmin=-lim, zmax=lim, ylabels=[R.ASSET_SHORT[a] for a in R.ASSETS], colorbar_title="pp"), key="al_hm1")
        X.plot(X.heatmap(A2, "BL 2.0 active weights (pp)", 380, fmt="+.1f", zmin=-lim, zmax=lim, ylabels=[R.ASSET_SHORT[a] for a in R.ASSETS], colorbar_title="pp"), key="al_hm2")
        X.plot(X.heatmap((W2 - W1).T * 100, "BL 2.0 − BL 1.0 target weights (pp)", 380, fmt="+.1f", ylabels=[R.ASSET_SHORT[a] for a in R.ASSETS], colorbar_title="pp"), key="al_hmd")
        X.section("F · Weight evolution by ETF", "one sleeve through time against its benchmark weight")
        sl = st.selectbox("ETF", R.ASSETS, format_func=lambda a: f"{a} — {meta.loc[a, 'etf_name']}", key="al_sleeve")
        fig = X.line_chart({R.BL1: W1[sl], R.BL2: W2[sl]}, yfmt=".1%", height=340, ytitle="target weight")
        fig.add_hline(y=float(b[sl]), line=dict(color=X.INK2, width=1.2, dash="dash"), annotation_text=f"benchmark {b[sl]:.2%}", annotation_position="top left",
                      annotation_font=dict(size=10, color=X.INK2))
        fig.add_hrect(y0=float(t2.loc[sl, "lower_bound"] + b[sl]), y1=float(t2.loc[sl, "upper_bound"] + b[sl]), fillcolor=X.BLUE_RAMP[100], opacity=0.25, line_width=0,
                      annotation_text="allowed range", annotation_position="bottom right", annotation_font=dict(size=10, color=X.MUTED))
        X.plot(fig, key="al_evol")
        X.source_note(store, ["p6_target_weights", "bl2_targets_long"])

    # ------------------------------------------------------------------------------------------------------- tab 3
    with tabs[2]:
        X.section("Average active weights", "the persistent exposures behind the historical active return")
        a_bl2 = store.read("bl2_att_trend_avg")
        a_bl1 = store.read("bl2_att_bl1_avg")
        a_eq = store.read("bl2_att_eq_avg")
        if a_bl2 is not None and a_bl1 is not None:
            tab = a_bl1.set_index("asset_class").rename(columns={"mean_active_weight": "BL 1.0 mean active", "share_dates_overweight": "BL 1.0 share overweight"})
            tab = tab.join(a_bl2.set_index("asset_class").rename(columns={"mean_active_weight": "BL 2.0 mean active", "share_dates_overweight": "BL 2.0 share overweight"}))
            if a_eq is not None:
                tab = tab.join(a_eq.set_index("asset_class").rename(columns={"mean_active_weight": "Equilibrium-only mean active", "share_dates_overweight": "Equilibrium-only share overweight"}))
            tab = tab.reindex(R.ASSETS)
            for c in [c for c in tab.columns if "mean active" in c]:
                tab[c] = tab[c] * 100
            cats = [R.ASSET_SHORT[a] for a in R.ASSETS]
            groups = {R.BL1: tab["BL 1.0 mean active"].to_numpy(), R.BL2: tab["BL 2.0 mean active"].to_numpy()}
            cols = {R.BL1: X.strategy_color(R.BL1), R.BL2: X.strategy_color(R.BL2)}
            if "Equilibrium-only mean active" in tab.columns:
                groups["BL2_EQUILIBRIUM_ONLY"] = tab["Equilibrium-only mean active"].to_numpy()
                cols["BL2_EQUILIBRIUM_ONLY"] = X.strategy_color("BL2_EQUILIBRIUM_ONLY")
            X.plot(X.grouped_bar(cats, groups, cols, yfmt="+.1f", height=420, labels={"BL2_EQUILIBRIUM_ONLY": "BL 2.0 equilibrium-only (no views)"}), key="al_avg")
            X.table(tab, {c: ("{:+.2f} pp" if "mean active" in c else "{:.0%}") for c in tab.columns})
            st.caption("The equilibrium-only path carries almost the same Equity overweight and Government-Bond underweight as the two view-driven models: the structural "
                       "tilt is produced by cost-aware drift inside the no-trade band and by the position boxes, not by the signals.")
        p6 = store.read("p6_persistent_exposures")
        if p6 is not None:
            with st.expander("BL 1.0 persistent active exposures (Phase 6 monitoring, descriptive)"):
                X.table(p6.set_index("asset_class").reindex(R.ASSETS)[["mean_active_weight", "share_overweight", "share_underweight", "share_at_bound", "longest_overweight_run", "longest_underweight_run"]],
                        {"mean_active_weight": "{:+.2%}", "share_overweight": "{:.0%}", "share_underweight": "{:.0%}", "share_at_bound": "{:.0%}"})
        X.source_note(store, ["bl2_att_trend_avg", "bl2_att_bl1_avg", "bl2_att_eq_avg", "p6_persistent_exposures"])
