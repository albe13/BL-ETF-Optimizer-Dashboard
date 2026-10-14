"""Page 9 — Model Methodology (penultimate page): BL 1.0 in twelve steps, then what BL 2.0 changed and why."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from bldash.core import design as X, model as M, registry as R
from bldash.core.store import get_store


def _process_diagram() -> None:
    X.flow([{"h": "Data", "b": "Ten UCITS ETFs · EUR total-return levels · ECB FX and cash"},
            {"h": "Risk model Σ", "b": "Ledoit-Wolf 3Y daily covariance, monthly"},
            {"h": "Equilibrium prior Π", "b": "Π = δΣb from the strategic benchmark b"},
            {"h": "Signals", "b": "Trend (1/3/12 m) · macro regime"},
            {"h": "Views Q, P, Ω", "b": "One absolute view per sleeve; confidence λ"},
            {"h": "Posterior μ", "b": "Black-Litterman blend of Π and Q"},
            {"h": "Optimizer", "b": "Benchmark-relative, TE cap, boxes, costs"},
            {"h": "Execution", "b": "Next common session; 10 bp one-way"},
            {"h": "Backtest", "b": "Self-financing ledger, 83 periods, tests"}])


def render() -> None:
    store = get_store()
    X.page_header("Model Methodology", "The complete model in twelve steps — purpose, economic intuition, inputs, outputs and the essential equations — first for BL 1.0, then the changes "
                  "introduced by BL 2.0 and why.", "Page 9 · Reference")
    meta = M.etf_meta(store)
    vp = store.meta.get("view_parameters", {})
    kappa = vp.get("kappa_production", {}).get("trend", 0.4157)
    X.section("Process overview", "from data to a monthly rebalanced portfolio")
    _process_diagram()
    st.markdown("")
    X.note("All model quantities shown in this dashboard were produced by frozen, hash-pinned runs (Phases 1–7 for BL 1.0; the BL 2.0 run). The dashboard displays them and recomputes nothing.", "info")

    # ------------------------------------------------------------------------------------------------------- BL 1.0
    X.section("BL 1.0 — the twelve steps", "")
    X.steps([
        {"n": "STEP 1", "h": "The ten ETFs and the benchmark",
         "b": "<b>Purpose:</b> define the investable universe and the neutral allocation. <b>Intuition:</b> a liquid proxy of the global market portfolio is the natural starting point for an investor with no views. "
              "<b>Input:</b> State Street Global Market Portfolio 2026 (private debt and high yield excluded, weights renormalized). <b>Output:</b> LIQUID_GMP_2026_V1 — ten UCITS ETFs with frozen weights b "
              "(Equity 45.7 %, Government Bonds 20.1 %, IG Credit 8.7 %, Gold 6.2 %, Private Equity proxy 4.9 %, EM Debt 4.8 %, Securitized 4.6 %, Real Estate 3.3 %, Inflation Linked 1.4 %, Convertibles 0.2 %)."},
        {"n": "STEP 2", "h": "Historical return construction",
         "b": "<b>Purpose:</b> one clean EUR total-return history per ETF. <b>Intuition:</b> accumulating and distributing share classes must be compared on reinvested distributions, in one currency. "
              "<b>Input:</b> Bloomberg TOTAL_RETURN series (2016-10-06 →), ECB USD/EUR reference rates for the two USD-listed lines, ECB EONIA→€STR cash. <b>Output:</b> daily EUR total-return levels on the common "
              "valuation calendar (M0 data stage, validated); these are valuation proxies, not executable quotes."},
        {"n": "STEP 3", "h": "Covariance estimation",
         "b": "<b>Purpose:</b> a stable risk model for the prior, the views and the optimizer. <b>Intuition:</b> with ten assets and three years of daily data, shrinkage toward a structured target reduces "
              "estimation noise. <b>Input:</b> daily EUR returns over (t − 3Y, t]. <b>Output:</b> Σ_t (Ledoit-Wolf, annualized × 252) at 84 month-end dates, 2019-10 → 2026-09; EWMA-63 volatilities for the trend scaling."},
        {"n": "STEP 4", "h": "Equilibrium expected returns",
         "b": "<b>Purpose:</b> the prior that the views are blended with. <b>Intuition:</b> if the benchmark is the optimal portfolio of a mean-variance investor, the expected excess returns that justify "
              "it are implied by its weights and Σ (reverse optimization). <b>Input:</b> b, Σ_t, an assumed equilibrium Sharpe ratio of 0.30. <b>Output:</b> Π_t = δ_t Σ_t b with δ_t = 0.30 / σ_B,t (annualized excess returns over cash)."},
        {"n": "STEP 5", "h": "Trend measurement",
         "b": "<b>Purpose:</b> a systematic, point-in-time signal of recent excess-return momentum per ETF. <b>Intuition:</b> time-series momentum is the best-documented systematic signal across asset classes. "
              "<b>Input:</b> trailing 1-, 3- and 12-month total returns minus the realized cash return, EWMA-63 volatility. <b>Output:</b> z_h = (R_h − c_h)/(σ√(h/12)); composite = mean of the legs; "
              "BL 1.0 score T = tanh(composite) ∈ [−1, 1]."},
        {"n": "STEP 6", "h": "Macroeconomic regimes",
         "b": "<b>Purpose:</b> a growth × inflation context inspired by the public Bridgewater framework. <b>Intuition:</b> asset classes behave differently when growth or inflation accelerate. "
              "<b>Input:</b> industrial-production and headline-CPI month-on-month changes for the US, Euro Area, UK and Japan; MA3 − MA6 acceleration standardized on the prior 60 months; publication lags M+1/M+2. "
              "<b>Output:</b> growth and inflation scores, a regime label (Goldilocks, Reflation, Stagflation, Disinflationary slowdown) and, in BL 1.0, a mapped macro signal M per sleeve."},
        {"n": "STEP 7", "h": "View construction",
         "b": "<b>Purpose:</b> turn signals into statements about expected returns. <b>Intuition:</b> the view is the prior plus a signal-proportional adjustment scaled by the asset's volatility. "
              "<b>Input:</b> T, M, Π, σ_i. <b>Output:</b> one absolute view per sleeve: S = (T + M)/2 on the six macro-mapped sleeves (else S = T); Δ_i = κ σ_i S_i with κ = 0.30; Q = Π + Δ; P = unit rows."},
        {"n": "STEP 8", "h": "View confidence",
         "b": "<b>Purpose:</b> state how much to trust each view relative to the prior. <b>Intuition:</b> a noisier view should move the posterior less. <b>Input:</b> P, Σ, a structural convention. "
              "<b>Output:</b> Ω = λ τ diag(PΣP′) with λ = 1 — an isolated view is trusted exactly as much as the prior and halves; τ cancels from the posterior mean and is left unspecified."},
        {"n": "STEP 9", "h": "Black-Litterman posterior",
         "b": "<b>Purpose:</b> combine prior and views consistently. <b>Intuition:</b> Bayesian blending weighted by precision; correlated assets share the information. <b>Input:</b> Π, Σ, P, Q, Ω. "
              "<b>Output:</b> μ_BL = Π + ΣP′(PΣP′ + Ω/τ·τ)⁻¹(Q − PΠ); d = μ_BL − Π; full own/cross attribution; 828 active views over 84 dates."},
        {"n": "STEP 10", "h": "Portfolio optimization",
         "b": "<b>Purpose:</b> translate expected returns into a portfolio close to the benchmark. <b>Intuition:</b> deviate from b only where the expected gain pays for the active risk and the trading cost. "
              "<b>Input:</b> d, Σ, δ, the drifted previous weights, policy limits. <b>Output:</b> w = b + a maximizing a′d − (δ/2)a′Σa − (12/h)c′|w − ŵ⁻| subject to 1′a = 0, hybrid boxes "
              "(10 pp / 2 pp / 0.5 × b_i), long-only and an ex-ante tracking-error cap of 2 %; h = 1, c = 10 bp; certified by an exact KKT polish."},
        {"n": "STEP 11", "h": "Monthly rebalancing",
         "b": "<b>Purpose:</b> implement the targets realistically. <b>Intuition:</b> a decision taken after the close can only be executed the next session. <b>Input:</b> targets at the last common date of each month. "
              "<b>Output:</b> execution at the next common session t⁺ at EUR total-return valuation proxies; 10 bp one-way cost on every trade; exact self-financing fixed-point rebalance."},
        {"n": "STEP 12", "h": "Backtesting and validation",
         "b": "<b>Purpose:</b> measure the historical outcome and its uncertainty under identical accounting for every strategy. <b>Intuition:</b> compare like with like. <b>Input:</b> targets, prices, cash, costs. "
              "<b>Output:</b> daily NAV, 83 monthly holding periods (2019-11-01 → 2026-10-01), metrics, Cariño attribution, HAC and bootstrap tests, 24 blocking tests, frozen hash-pinned contract."},
    ], cols=3)
    with st.expander("Essential equations"):
        c1, c2 = st.columns(2)
        with c1:
            st.latex(r"\Pi_t = \delta_t \Sigma_t b,\qquad \delta_t = \frac{S^\star}{\sigma_{B,t}},\quad S^\star = 0.30")
            st.latex(r"z_h = \frac{R_h - c_h}{\sigma_{\text{EWMA}}\sqrt{h/12}},\qquad \text{composite} = \tfrac{1}{3}\sum_{h\in\{1,3,12\}} z_h")
            st.latex(r"\text{BL 1.0: } T=\tanh(\text{composite}),\; S=\tfrac{T+M}{2},\; \Delta_i=\kappa\,\sigma_i S_i,\; \kappa=0.30")
            st.latex(r"Q = \Pi + \Delta,\qquad P = I_{\text{active}},\qquad \Omega = \lambda\tau\,\mathrm{diag}(P\Sigma P')")
        with c2:
            st.latex(r"\mu_{BL} = \Pi + \Sigma P'\left(P\Sigma P' + \Omega/\tau\right)^{-1}(Q - P\Pi),\qquad d=\mu_{BL}-\Pi")
            st.latex(r"\max_a\; a'd - \tfrac{\delta}{2}a'\Sigma a - \tfrac{12}{h}\,c'\,|b+a-\hat w^-| \quad\text{s.t. } 1'a=0,\; lo\le a\le hi,\; \sqrt{a'\Sigma a}\le 2\%")
            st.latex(r"\text{net period return } R_n = (1+R_g)(1-x_{\text{end}})-1,\qquad x = c'\,|w(1-x)-w_{\text{pre}}|")
            st.latex(r"\text{Sharpe} = \sqrt{12}\,\frac{\overline{R - c}}{\mathrm{sd}(R-c)},\qquad \text{IR} = \frac{12\,\overline{R - R_B}}{\sqrt{12}\,\mathrm{sd}(R-R_B)}")

    # ------------------------------------------------------------------------------------------------------- BL 2.0
    X.section("BL 2.0 — what changed and why", "research configuration; parameters provisional pending ratification")
    X.steps([
        {"n": "CHANGE 1", "h": "Revised trend representation",
         "b": "The measurement (Step 5) is reproduced bitwise, but the production field is the <b>unbounded</b> standardized composite instead of tanh(composite): bounding compressed 22 % of sleeve-dates "
              "below 42 % of their marginal information. The tanh score is kept only as a comparability convention. <b>Why:</b> magnitude belongs to the view, not to the measurement."},
        {"n": "CHANGE 2", "h": "Unbounded, unit-scale signals with a common/relative split",
         "b": "z̃ = composite_z / 0.80 (the structural standard deviation of the mean of three overlapping legs) gives a unit-variance signal; it is decomposed exactly into a common (date-mean, market-direction) "
              "and a relative component, both published. <b>Why:</b> Grinold's forecast rule needs a unit-variance signal, and a fully invested budget-neutral mandate cannot express a common view "
              "except as a volatility tilt — the split makes that visible."},
        {"n": "CHANGE 3", "h": "Macro measurement architecture (Phase 4.2)",
         "b": "The four-region acceleration regime is replaced by a measurement engine: US and Euro Area growth/inflation <b>states</b> (z of the 3-month level), <b>surprises</b> (actual vs consensus, "
              "MAD-scaled, clipped ±4), policy repricing z(Δ3m OIS 1Y), real-rate and inflation-expectation changes, credit level and stress, VIX and MOVE. <b>Why:</b> the BL 1.0 regime had no "
              "monthly return information and changed label 45 times in 84 months. <b>Consequence:</b> no macro family is point-in-time eligible as a production view (surprises are REVISED_DATA_PROXY), "
              "so BL 2.0 production views are trend only; macro fields are diagnostics and an experimental scenario."},
        {"n": "CHANGE 4", "h": "Revised view calibration",
         "b": f"Δ = √12 · IC · σ · z̃ with a literature trend IC of 0.12 ⇒ κ = {kappa:.3f} on the unit-variance signal; adopted with gain ½ (λ = 1) ⇒ effective IC 0.06; families combined by the "
              "correlation-aware rule w = R⁻¹ρ (policy repricing is dropped because it is spanned by the Government-Bonds trend). <b>Why:</b> BL 1.0's κ = 0.30 on a score with sd 0.55 implied a monthly "
              "IC of only 0.048 (0.024 after halving) — κ = √12·IC, not κ = IC. <b>Consequence:</b> views roughly 2.5 times larger; the TE cap binds on 43 % of dates."},
        {"n": "CHANGE 5", "h": "Full Ω",
         "b": "Ω = λτ·PΣP′ (full) instead of its diagonal: view errors inherit the return correlations. With a view on every sleeve this gives d = Δ/(1+λ) exactly — no cross-view contamination and "
              "<b>zero sign reversals</b>, against 8–9 % of reversed views under the diagonal convention. <b>Why:</b> consistency with Grinold's framework; chosen on theory before the run."},
        {"n": "CHANGE 6", "h": "Updated transaction-cost treatment",
         "b": "The one-way cost is amortized over the signal's expected persistence: h = 3 months (band ±40 bp of expected return) instead of h = 1 (±120 bp). <b>Why:</b> h = 1 acted as a regularizer that "
              "also created the drift tilt. <b>Consequence:</b> turnover rose from 10 % to 70 % per year (the band and the larger views each explain about a third of the increase) with a cost drag of 14 bp per year."},
        {"n": "CHANGE 7", "h": "Portfolio transmission diagnostics",
         "b": "Every decision publishes the ex-ante tracking error of the unconstrained tilt, of the budget-neutral tilt and of the certified allocation, the correlation between the final tilt and d, the "
              "number of binding boxes and untraded sleeves, and synthetic strong-signal scenarios. <b>Why:</b> to show where information is lost between the view and the weight. "
              "<b>Finding:</b> the mandate, not the views, sizes most positions."},
        {"n": "UNCHANGED", "h": "Frozen foundations",
         "b": "Benchmark, data stage, Σ (Ledoit-Wolf 3Y), Π, model dates, execution calendar, ledger, 2 % TE cap, hybrid boxes, 10 bp one-way cost, Sharpe over realized cash. BL 1.0's frozen results are reproduced "
              "bitwise inside the BL 2.0 run, so every comparison in this dashboard uses identical accounting."},
        {"n": "RESULT", "h": "Did the changes improve performance?",
         "b": "Not observably. BL 2.0 − BL 1.0 = −0.19 % per year (HAC t −0.43), Sharpe 0.81 vs 0.78, max drawdown −20.7 % vs −22.3 %, IR 0.72 vs 1.42, turnover 7× higher. The changes improve the internal "
              "consistency and transparency of the model; they do not demonstrate predictive value, and several of them (larger views, h = 3) are the documented cause of higher turnover."},
    ], cols=3)
    with st.expander("BL 2.0 equations"):
        c1, c2 = st.columns(2)
        with c1:
            st.latex(r"\tilde z_i = \frac{\text{composite\_z}_i}{0.80},\qquad \text{composite\_z}_i = \underbrace{\bar z_t}_{\text{common}} + \underbrace{(\text{composite\_z}_i - \bar z_t)}_{\text{relative}}")
            st.latex(r"\Delta_i = \sigma_i^{LW}\,\kappa\,\mathrm{clip}(\tilde z_i,\pm 3),\qquad \kappa = \sqrt{12}\cdot IC = " + f"{kappa:.3f}")
            st.latex(r"\Omega = \lambda\tau\,P\Sigma P',\; \lambda = 1 \;\Rightarrow\; d = \frac{\Delta}{1+\lambda} = \tfrac{1}{2}\Delta \text{ (all ten views active)}")
        with c2:
            st.latex(r"\text{surprise}_j = \mathrm{clip}\!\left(\frac{\text{actual}_j - \text{survey}_j}{1.4826\,\mathrm{MAD}_{60}},\pm 4\right),\quad \text{news} = \bar s\sqrt{n}")
            st.latex(r"\max_a\; a'd - \tfrac{\delta}{2}a'\Sigma a - \tfrac{12}{h}c'|b+a-\hat w^-|,\qquad h = 3 \;(\text{band } \pm 40\text{ bp})")
            st.latex(r"w = R^{-1}\rho \text{ (family weights)},\qquad R_{\text{trend,policy}} = 0.65 \Rightarrow w_{\text{policy}} \le 0 \Rightarrow \text{dropped}")
    X.section("Parameter status", "what is final, what is provisional")
    pol2 = store.meta.get("policy_bl2", {})
    X.table(pd.DataFrame([
        {"parameter": "Benchmark, Σ estimator, Π calibration (Sharpe 0.30), model dates", "BL 1.0": "frozen", "BL 2.0": "frozen (identical)", "status": "FINAL"},
        {"parameter": "Trend horizons", "BL 1.0": "{1, 3, 12} equal-weight", "BL 2.0": "{1, 3, 12} (alternative {3, 6, 12} published as diagnostic)", "status": "PROVISIONAL (T1)"},
        {"parameter": "Signal representation", "BL 1.0": "tanh(composite)", "BL 2.0": "composite_z / 0.80, clip ±3 in the view", "status": "FINAL removal of tanh / PROVISIONAL constant"},
        {"parameter": "Macro in views", "BL 1.0": "regime score via sign map on 6 sleeves", "BL 2.0": "none (diagnostics; experimental scenario)", "status": "FINAL (M2–M9) / UNRESOLVED PIT validity (M3)"},
        {"parameter": "κ (view scale)", "BL 1.0": "0.30", "BL 2.0": f"{kappa:.3f} = √12 × 0.12", "status": "PROVISIONAL (B5; effective-IC 0.03–0.10 ablations published)"},
        {"parameter": "Ω structure, λ", "BL 1.0": "diagonal, λ = 1", "BL 2.0": "full PΣP′, λ = 1", "status": "FINAL structure / PROVISIONAL λ"},
        {"parameter": "Cost horizon h, cost c", "BL 1.0": "h = 1, 10 bp", "BL 2.0": f"h = {pol2.get('h_months', 3):.0f}, 10 bp", "status": "PROVISIONAL h (O1); c assumed"},
        {"parameter": "TE cap, boxes", "BL 1.0": "2 %, (10 pp, 2 pp, 0.5)", "BL 2.0": "2 %, (10 pp, 2 pp, 0.5)", "status": "FINAL (approved policy); tension with the view scale documented (O3)"},
    ]), hide_index=True)
    X.source_note(store, ["bl2_view_parameters", "cfg_benchmark"])
    st.caption("References: docs/PHASE1–7 methodology reports, docs/BL1_methodology_report, research/bl2/implementation (BL 2.0 methodology, κ calibration, Ω methodology, optimizer methodology, "
               "transmission audit), research/bl2/regime_turnover_audit.")
