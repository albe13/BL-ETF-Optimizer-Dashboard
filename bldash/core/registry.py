"""Logical artifact registry of the BL ETF Optimizer dashboard.

Every table the dashboard can read is declared here once: which published run it belongs to, its path inside that run, whether it is
required, and its licensing tier for the deployment package. The repository-mode store resolves keys through the frozen contracts and
run manifests (hash chain: contract -> manifest -> file); the bundle-mode store resolves them through ARTIFACT_MANIFEST.json written by
tools/build_deployment_package.py from this same registry. The dashboard never writes into a run directory.

Tiers:
  SAFE     - model outputs, standardized measurements, weights, metrics, hashes: included in the deployment package by default.
  REVIEW   - derived tables that still carry licensed market observations (ETF levels or returns, raw macro inputs): excluded by
             default; included only with --include-review after the user's licence review.
  EXCLUDE  - raw Bloomberg observations (levels, release actual/survey values): never bundled.
A REVIEW table may declare `redact` columns: the bundle then carries a SAFE copy without those columns (tier SAFE_REDACTED).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

# ----------------------------------------------------------------------------------------------------------------------------- sources
SOURCES: Dict[str, Dict[str, object]] = {
    "bl2": {"label": "BL 2.0 published run", "contract": "outputs/bl2/BL2_OUTPUT_CONTRACT.json", "run_dir_key": "bl2_run_directory",
            "manifest_sha_key": "bl2_manifest_sha256", "run_id_key": "bl2_run_id"},
    "p7": {"label": "Phase 7 historical backtest (BL 1.0)", "contract": "outputs/phase7/PHASE7_OUTPUT_CONTRACT.json", "run_dir_key": "phase7_run_directory",
           "manifest_sha_key": "phase7_manifest_sha256", "run_id_key": "phase7_run_id"},
    "p6": {"label": "Phase 6 portfolio optimizer (BL 1.0)", "contract": "outputs/phase6/PHASE6_OUTPUT_CONTRACT.json", "run_dir_key": "phase6_run_directory",
           "manifest_sha_key": "phase6_manifest_sha256", "run_id_key": "phase6_run_id"},
    "p5": {"label": "Phase 5 Black-Litterman posterior (BL 1.0)", "contract": "outputs/phase5/PHASE5_OUTPUT_CONTRACT.json", "run_dir_key": "phase5_run_directory",
           "manifest_sha_key": "phase5_manifest_sha256", "run_id_key": "phase5_run_id"},
    "p4": {"label": "Phase 4 macro regime (BL 1.0)", "contract": "outputs/phase4/PHASE4_OUTPUT_CONTRACT.json", "run_dir_key": "phase4_run_directory",
           "manifest_sha_key": "phase4_manifest_sha256", "run_id_key": "phase4_run_id"},
    "p3": {"label": "Phase 3 trend signals (BL 1.0)", "contract": "outputs/phase3/PHASE3_OUTPUT_CONTRACT.json", "run_dir_key": "phase3_run_directory",
           "manifest_sha_key": "phase3_manifest_sha256", "run_id_key": "phase3_run_id"},
    "p2": {"label": "Phase 2 equilibrium prior", "contract": "outputs/phase2/PHASE2_OUTPUT_CONTRACT.json", "run_dir_key": "phase2_run_directory",
           "manifest_sha_key": "phase2_manifest_sha256", "run_id_key": "phase2_run_id"},
    "p1": {"label": "Phase 1 risk model", "contract": "outputs/phase1/PHASE2_INPUT_CONTRACT.json", "run_dir_key": "phase1_run_directory",
           "manifest_sha_key": "phase1_manifest_sha256", "run_id_key": "phase1_run_id"},
    # M0 has no downstream contract of its own: its run id and manifest hash are pinned by the BL 2.0 contract.
    "m0": {"label": "M0 data stage (EUR total-return levels)", "contract": None, "run_dir_template": "outputs/M0/runs/{run_id}",
           "run_id_from": ("bl2", "m0_run_id"), "manifest_sha_from": ("bl2", "upstream_source_hashes", "m0_manifest_sha256")},
    "cfg": {"label": "Frozen benchmark and ETF definition", "contract": None, "file": "configs/liquid_gmp_2026_v1.yaml",
            "sha_from": ("p7", "benchmark_config_hash")},
}

SAFE, REVIEW, EXCLUDE = "SAFE", "REVIEW", "EXCLUDE"


@dataclass(frozen=True)
class Entry:
    key: str
    source: str
    path: str                      # relative to the run directory (or the file itself for cfg)
    kind: str = "csv"              # csv | json | yaml
    required: bool = False
    tier: str = SAFE
    description: str = ""
    pages: Tuple[str, ...] = ()
    redact: Tuple[str, ...] = ()   # columns removed in the SAFE_REDACTED bundle copy (REVIEW tables only)
    date_cols: Tuple[str, ...] = ()


def _e(key, source, path, **kw) -> Entry:
    return Entry(key=key, source=source, path=path, **kw)


ENTRIES: List[Entry] = [
    # ------------------------------------------------------------------------------------------------------------------ BL 2.0 run
    _e("bl2_summary_metrics", "bl2", "simulation/summary_metrics.csv", required=True, description="Stored performance and risk metrics of every simulated strategy", pages=("1", "4", "8")),
    _e("bl2_nav_daily", "bl2", "simulation/nav_daily.csv", required=True, description="Daily post-trade NAV (net and gross) and stored drawdown per strategy", pages=("1", "4")),
    _e("bl2_monthly_returns", "bl2", "simulation/monthly_returns.csv", required=True, description="Holding-period gross/net returns, costs and cash return per strategy", pages=("1", "4", "8")),
    _e("bl2_weights_executed", "bl2", "simulation/weights_executed.csv", required=True, description="Executed post-trade weights at every execution date per strategy", pages=("2", "8")),
    _e("bl2_comparison_tests", "bl2", "simulation/comparison_tests.csv", required=True, description="HAC and block-bootstrap tests on monthly active returns", pages=("1", "4")),
    _e("bl2_calendar_year_returns", "bl2", "simulation/calendar_year_returns.csv", required=True, description="Stored calendar-year net returns", pages=("4",)),
    _e("bl2_cost_sensitivity", "bl2", "simulation/cost_sensitivity.csv", description="Frozen targets charged at 5/10/20 bp (accounting only)", pages=("4",)),
    _e("bl2_att_trend_static_dynamic", "bl2", "simulation/attribution/bl2_trend_only_static_dynamic.csv", description="BL 2.0 static vs dynamic active-return split", pages=("4",), date_cols=("end",)),
    _e("bl2_att_bl1_static_dynamic", "bl2", "simulation/attribution/bl1_frozen_static_dynamic.csv", description="BL 1.0 static vs dynamic active-return split", pages=("4",), date_cols=("end",)),
    _e("bl2_att_eq_static_dynamic", "bl2", "simulation/attribution/bl2_equilibrium_only_static_dynamic.csv", description="Equilibrium-only static vs dynamic split", pages=("4",), date_cols=("end",)),
    _e("bl2_att_trend_avg", "bl2", "simulation/attribution/bl2_trend_only_average_active_weights.csv", description="BL 2.0 average active weights and overweight shares", pages=("2", "4")),
    _e("bl2_att_bl1_avg", "bl2", "simulation/attribution/bl1_frozen_average_active_weights.csv", description="BL 1.0 average active weights and overweight shares", pages=("2", "4")),
    _e("bl2_att_eq_avg", "bl2", "simulation/attribution/bl2_equilibrium_only_average_active_weights.csv", description="Equilibrium-only average active weights", pages=("2", "4")),
    _e("bl2_att_trend_active", "bl2", "simulation/attribution/bl2_trend_only_active_attribution.csv", tier=REVIEW, description="BL 2.0 per-period, per-sleeve active attribution (carries sleeve returns)", pages=("4",)),
    _e("bl2_att_bl1_active", "bl2", "simulation/attribution/bl1_frozen_active_attribution.csv", tier=REVIEW, description="BL 1.0 per-period, per-sleeve active attribution (carries sleeve returns)", pages=("4",)),
    _e("bl2_targets_long", "bl2", "allocation/target_weights_long.csv", required=True, description="BL 2.0 (and ablation) target weights, bounds, binding flags, planned trades per decision date", pages=("1", "2", "5", "8")),
    _e("bl2_portfolio_summary", "bl2", "allocation/portfolio_summary.csv", required=True, description="BL 2.0 per-decision optimizer summary: ex-ante TE, binding constraints, planned turnover and cost", pages=("4", "5", "8")),
    _e("bl2_transmission", "bl2", "allocation/transmission_chain_production.csv", required=True, description="BL 2.0 view-to-weight transmission chain per decision date", pages=("5", "8")),
    _e("bl2_transmission_h1", "bl2", "allocation/transmission_chain_h1_ablation.csv", description="Transmission chain of the h = 1 ablation", pages=("5",)),
    _e("bl2_scenarios", "bl2", "allocation/synthetic_scenarios.csv", description="Synthetic strong-signal scenarios on the latest date", pages=("5",), date_cols=("reference_date",)),
    _e("bl2_view_register", "bl2", "views/view_register_production.csv", required=True, description="BL 2.0 production views: signal, sigma, prior, Delta, Q per sleeve and date", pages=("5", "7", "8")),
    _e("bl2_posterior", "bl2", "views/posterior_production.csv", required=True, description="BL 2.0 posterior expected returns and adjustment components", pages=("5", "8")),
    _e("bl2_posterior_diag", "bl2", "views/posterior_diag_omega.csv", description="Posterior under the diagonal-Omega ablation", pages=("5",)),
    _e("bl2_view_register_experimental", "bl2", "views/view_register_experimental.csv", description="EXPERIMENTAL revised-data macro views (not production)", pages=("5",)),
    _e("bl2_posterior_experimental", "bl2", "views/posterior_experimental.csv", description="EXPERIMENTAL posterior (not production)", pages=("5",)),
    _e("bl2_sigma_ratio", "bl2", "views/diagnostics/sigma_lw_over_ewma.csv", description="Dual-volatility diagnostic sigma_LW / sigma_EWMA", pages=("5",)),
    _e("bl2_view_parameters", "bl2", "views/view_parameters.json", kind="json", required=True, description="kappa, IC, lambda, combination weights", pages=("5", "9")),
    _e("bl2_trend_signals", "bl2", "trend/trend_signals.csv", required=True, tier=REVIEW, redact=("excess_return_1m", "excess_return_3m", "excess_return_12m"),
       description="BL 2.0 trend signals per sleeve and date (z legs, composite, common/relative split); the excess-return columns are ETF trailing returns", pages=("7", "8"), date_cols=("estimation_date",)),
    _e("bl2_trend_common", "bl2", "trend/cross_sectional_common.csv", required=True, description="Common (market-direction) trend component per date", pages=("7",), date_cols=("estimation_date",)),
    _e("bl2_composite_z_wide", "bl2", "trend/composite_z_wide.csv", required=True, description="composite_z, wide", pages=("7",), date_cols=("estimation_date",)),
    _e("bl2_cs_relative_z_wide", "bl2", "trend/cs_relative_z_wide.csv", description="relative trend component, wide", pages=("7",), date_cols=("estimation_date",)),
    _e("bl2_composite_unit_wide", "bl2", "trend/composite_unit_wide.csv", description="unit-scale composite (composite_z / 0.80), wide", pages=("7",), date_cols=("estimation_date",)),
    _e("bl2_trend_score_tanh_wide", "bl2", "trend/trend_score_tanh_wide.csv", description="tanh convention (BL 1.0 comparability), wide", pages=("7",), date_cols=("estimation_date",)),
    _e("bl2_trend_horizon_3_6_12", "bl2", "trend/diagnostics/horizon_set_3_6_12.csv", description="Pre-registered alternative horizon set (diagnostic)", pages=("7",), date_cols=("estimation_date",)),
    _e("bl2_trend_scale", "bl2", "trend/diagnostics/scale_diagnostics.json", kind="json", description="Scale and persistence diagnostics of the trend composite", pages=("7", "9")),
    _e("bl2_trend_metadata", "bl2", "trend/signal_metadata.json", kind="json", description="Trend signal semantics and cash provenance", pages=("7",)),
    _e("bl2_equity_ma", "bl2", "trend/diagnostics/equity_moving_average.csv", tier=REVIEW, description="Equity 50/200 moving-average diagnostic (carries ETF levels)", pages=("7",), date_cols=("estimation_date",)),
    _e("bl2_macro_wide", "bl2", "macro/macro_factors_wide.csv", required=True, description="All standardized macro factors per date, wide", pages=("6", "8")),
    _e("bl2_macro_long", "bl2", "macro/macro_factors_long.csv", required=True, description="Macro factors long with status, vintage and role", pages=("6",)),
    _e("bl2_macro_composites", "bl2", "macro/surprise_state_composites.csv", required=True, description="Growth/inflation surprise (news) and state composites per family", pages=("6", "8")),
    _e("bl2_macro_component_audit", "bl2", "macro/component_audit.csv", description="Per-indicator standardized surprise, state z, availability lag and vintage", pages=("6",)),
    _e("bl2_macro_regimes", "bl2", "macro/regimes.csv", required=True, description="Growth/inflation states, quadrant label, momentum and stress flag per region", pages=("6", "8")),
    _e("bl2_market_factors_long", "bl2", "macro/market_factors_long.csv", description="Market-based factors long with vintage and proxy flags", pages=("6",)),
    _e("bl2_macro_correlation", "bl2", "macro/diagnostics/factor_correlation.csv", description="Correlation of macro factors", pages=("6",)),
    _e("bl2_macro_pca", "bl2", "macro/diagnostics/factor_pca.csv", description="PCA of macro factors", pages=("6",)),
    _e("bl2_macro_factor_trend_corr", "bl2", "macro/diagnostics/factor_trend_correlation.csv", description="Correlation of macro factors with the trend composite", pages=("6",)),
    _e("bl2_macro_shadow", "bl2", "macro/diagnostics/surprise_scale_shadow.csv", description="sigma-60 vs MAD scale shadow diagnostic", pages=("6",)),
    _e("bl2_macro_inventory", "bl2", "macro/diagnostics/series_inventory.csv", description="Inventory of the Bloomberg series used (metadata only)", pages=("6", "10")),
    _e("bl2_macro_nonnumeric", "bl2", "macro/diagnostics/nonnumeric_tokens.csv", description="Non-numeric tokens mapped to missing", pages=("10",)),
    _e("bl2_macro_metadata", "bl2", "macro/macro_metadata.json", kind="json", required=True, description="Macro roles, vintage statement, workbook hashes", pages=("6", "9")),
    _e("bl2_market_raw", "bl2", "macro/market_raw_levels.csv", tier=EXCLUDE, description="Raw Bloomberg market levels at decision dates (local mode only)", pages=("6",)),
    _e("bl2_validation", "bl2", "validation_summary.json", kind="json", required=True, description="BL 2.0 validation checks", pages=("10",)),
    # ------------------------------------------------------------------------------------------------------------------ Phase 7 (BL 1.0 backtest)
    _e("p7_summary_metrics", "p7", "primary/summary_metrics.csv", required=True, description="Phase 7 stored metrics (S1 BL 1.0 = BL1_FROZEN; S2 = benchmark) incl. planned no-trade months", pages=("4", "8")),
    _e("p7_rolling_metrics", "p7", "diagnostics/rolling_metrics.csv", description="Stored rolling 12/36-month metrics of S1 and S2 (reconciliation of the dashboard-derived rolling series)", pages=("4",)),
    _e("p7_transaction_costs", "p7", "primary/transaction_costs.csv", required=True, description="Executed turnover and exact cost per execution event (BL 1.0 and benchmark)", pages=("4", "8")),
    _e("p7_planned_vs_executed", "p7", "diagnostics/planned_vs_executed.csv", required=True, description="BL 1.0 planned (decision close) vs executed (next session) trades per sleeve", pages=("8",), date_cols=("decision_date", "execution_date")),
    _e("p7_execution_calendar", "p7", "diagnostics/execution_calendar.csv", required=True, description="Decision date -> execution date -> holding period (the date triplet)", pages=("all",), date_cols=("decision_date", "last_observation_used", "execution_date", "execution_date_planned_phase6", "accrual_start", "accrual_end")),
    _e("p7_drawdown_episodes", "p7", "diagnostics/drawdown_episodes.csv", description="Stored drawdown episodes of S1/S2", pages=("4",), date_cols=("peak_date", "trough_date", "recovery_date")),
    _e("p7_comparison_metrics", "p7", "primary/comparison_metrics.csv", description="Stored benchmark-relative metrics of S1", pages=("4",)),
    _e("p7_regressions", "p7", "diagnostics/regressions.csv", description="Stored factor regressions of S1 - S2", pages=("4",)),
    _e("p7_inference_mean_tests", "p7", "diagnostics/inference_mean_tests.csv", description="Stored HAC tests of S1 vs S2/S3/S4", pages=("4",)),
    _e("p7_cash_returns", "p7", "diagnostics/cash_returns.csv", required=True, description="Realized EUR cash return per holding period (ECB EONIA->ESTR)", pages=("3", "4"), date_cols=("end",)),
    _e("p7_allocation_attribution", "p7", "attribution/allocation_attribution.csv", description="Carino-linked attribution of S1 - S2 by sleeve", pages=("4",)),
    _e("p7_persistent_exposure", "p7", "attribution/persistent_exposure.csv", description="Static vs time-varying split of the S1 active return", pages=("4",)),
    _e("p7_active_contributions", "p7", "attribution/active_contributions.csv", tier=REVIEW, description="BL 1.0 per-period, per-sleeve active contributions (carries sleeve returns)", pages=("4",)),
    _e("p7_sensitivity_scenarios", "p7", "diagnostics/sensitivity_scenarios.csv", description="BL 1.0 diagnostic sensitivities (labelled, never a policy choice)", pages=("4",)),
    _e("p7_data_completeness", "p7", "diagnostics/data_completeness.csv", description="Data completeness checks", pages=("10",)),
    _e("p7_timing_validation", "p7", "diagnostics/timing_validation.csv", description="Timing validation", pages=("10",)),
    _e("p7_lookahead_test", "p7", "diagnostics/lookahead_test.csv", description="Look-ahead test", pages=("10",)),
    # ------------------------------------------------------------------------------------------------------------------ Phase 6 (BL 1.0 optimizer)
    _e("p6_target_weights", "p6", "primary/target_weights.csv", required=True, description="BL 1.0 target weights with bounds, binding flags, planned trades and cost per decision date", pages=("1", "2", "5", "8"), date_cols=("execution_date_planned",)),
    _e("p6_portfolio_summary", "p6", "primary/portfolio_summary.csv", required=True, description="BL 1.0 per-decision optimizer summary (ex-ante TE, binding, turnover, transfer coefficient)", pages=("4", "5", "8"), date_cols=("execution_date_planned",)),
    _e("p6_binding_summary", "p6", "diagnostics/binding_summary.csv", description="Share of dates each BL 1.0 constraint binds", pages=("5",)),
    _e("p6_active_vs_view_sign", "p6", "diagnostics/active_weight_vs_view_sign.csv", description="BL 1.0 posterior adjustment vs active weight and unconstrained tilt per sleeve-date", pages=("5", "8")),
    _e("p6_monitoring_flags", "p6", "diagnostics/monitoring_flags.csv", description="BL 1.0 turnover and group monitoring flags", pages=("8",)),
    _e("p6_persistent_exposures", "p6", "diagnostics/persistent_active_exposures.csv", description="BL 1.0 persistent active exposures (descriptive)", pages=("2",)),
    _e("p6_certification", "p6", "diagnostics/certification.csv", description="BL 1.0 solver certificates per date", pages=("10",)),
    # ------------------------------------------------------------------------------------------------------------------ Phase 5 (BL 1.0 posterior)
    _e("p5_posterior", "p5", "primary/posterior_expected_returns.csv", required=True, description="BL 1.0 prior, posterior and adjustment per sleeve-date", pages=("5", "8")),
    _e("p5_views", "p5", "primary/views.csv", required=True, description="BL 1.0 active views: signal S, trend T, macro M, sigma, Delta, Q, D variance", pages=("5", "7", "8")),
    _e("p5_view_register", "p5", "primary/view_register.csv", required=True, description="BL 1.0 view availability register", pages=("5", "8")),
    _e("p5_view_mapping", "p5", "primary/view_mapping.csv", required=True, description="BL 1.0 sleeve -> view mapping and macro sign map (b_growth, b_inflation)", pages=("5", "6", "9")),
    _e("p5_normalized_uncertainty", "p5", "primary/normalized_uncertainty.csv", description="BL 1.0 D = Omega / tau (diagonal) per date", pages=("5",)),
    _e("p5_attribution_summary", "p5", "primary/attribution_summary.csv", required=True, description="BL 1.0 own vs cross-view contribution to the posterior adjustment", pages=("5", "8")),
    _e("p5_sign_reversal_aggregate", "p5", "diagnostics/sign_reversal_aggregate.csv", description="BL 1.0 sign-reversal statistics", pages=("5",)),
    # ------------------------------------------------------------------------------------------------------------------ Phase 4 (BL 1.0 regime)
    _e("p4_regime_history", "p4", "primary/regime_history.csv", required=True, description="BL 1.0 growth x inflation acceleration regime (4 regions) per model date", pages=("6", "8"), date_cols=("estimation_date",)),
    _e("p4_regional_scores", "p4", "primary/regional_scores.csv", tier=REVIEW, description="Regional inputs, acceleration and z per region/dimension (carries raw IP/CPI inputs)", pages=("6",)),
    _e("p4_regime_changes", "p4", "diagnostics/regime_changes.csv", description="BL 1.0 regime transitions list", pages=("6",), date_cols=("estimation_date",)),
    _e("p4_regime_transitions", "p4", "diagnostics/regime_transitions.csv", description="BL 1.0 regime transition matrix", pages=("6",)),
    _e("p4_regime_frequency", "p4", "diagnostics/regime_frequency.csv", description="BL 1.0 regime occupancy statistics", pages=("6",)),
    # ------------------------------------------------------------------------------------------------------------------ Phase 3 (BL 1.0 trend)
    _e("p3_trend_score", "p3", "common/trend_score.csv", required=True, tier=REVIEW,
       redact=("total_return_1m", "total_return_3m", "total_return_12m", "cash_return_1m", "cash_return_3m", "cash_return_12m", "excess_return_1m", "excess_return_3m", "excess_return_12m"),
       description="BL 1.0 trend legs, composite and tanh score per sleeve-date (return columns are ETF trailing returns)", pages=("7", "8"), date_cols=("estimation_date",)),
    _e("p3_signals_side_by_side", "p3", "asset_specific/signals_side_by_side.csv", description="BL 1.0 common trend vs asset-specific signals", pages=("7",), date_cols=("estimation_date",)),
    _e("p3_signal_persistence", "p3", "diagnostics/signal_persistence.csv", description="BL 1.0 trend persistence diagnostics", pages=("7",)),
    _e("p3_signal_metadata", "p3", "common/signal_metadata.json", kind="json", description="BL 1.0 trend semantics", pages=("7", "9")),
    # ------------------------------------------------------------------------------------------------------------------ Phase 2 / Phase 1
    _e("p2_pi_wide", "p2", "primary_eq_sharpe/pi_excess_wide.csv", required=True, description="Equilibrium excess returns Pi per date (annualized)", pages=("5", "8", "9"), date_cols=("estimation_date",)),
    _e("p2_pi_long", "p2", "primary_eq_sharpe/pi_excess.csv", description="Pi with delta, beta to the benchmark", pages=("5",), date_cols=("estimation_date",)),
    _e("p2_delta_history", "p2", "primary_eq_sharpe/delta_history.csv", required=True, description="Risk aversion delta_t and benchmark volatility", pages=("5", "9"), date_cols=("estimation_date",)),
    _e("p1_covariance_long", "p1", "lw_3y_daily/covariance_long.csv", required=True, description="Ledoit-Wolf 3Y covariance Sigma_t (annualized), long", pages=("5", "8"), date_cols=("estimation_date",)),
    _e("p1_correlation_long", "p1", "lw_3y_daily/correlation_long.csv", description="Correlation implied by Sigma_t, long", pages=("5",), date_cols=("estimation_date",)),
    _e("p1_sleeve_vol", "p1", "lw_3y_daily/sleeve_volatility.csv", required=True, description="sigma_i = sqrt(diag Sigma_t)", pages=("5", "8"), date_cols=("estimation_date",)),
    _e("p1_ewma63_vol", "p1", "ewma_63/sleeve_volatility.csv", description="EWMA-63 sleeve volatility (the trend z scale)", pages=("7",), date_cols=("estimation_date",)),
    _e("p1_core_correlations", "p1", "lw_3y_daily/core_correlations.csv", description="Selected pairwise correlations through time", pages=("5",), date_cols=("estimation_date",)),
    # ------------------------------------------------------------------------------------------------------------------ M0 / config
    _e("m0_weights_history", "m0", "weights_history.csv", tier=REVIEW, description="Daily EUR total-return levels of the ten ETFs (M0 valuation calendar); the only ETF price-like series", pages=("3",)),
    _e("m0_data_audit", "m0", "data_audit_total_return.csv", required=True, description="ETF data audit: identity, income treatment, coverage, FX translation", pages=("3", "10")),
    _e("m0_px_vs_tr", "m0", "px_vs_tr_assets.csv", description="Cumulative price vs total return per ETF (distribution effect)", pages=("3",)),
    _e("cfg_benchmark", "cfg", "configs/liquid_gmp_2026_v1.yaml", kind="yaml", required=True, description="ETF universe: names, tickers, ISINs, benchmark weights", pages=("all",)),
]

ENTRY_BY_KEY: Dict[str, Entry] = {e.key: e for e in ENTRIES}
RELEASE_TICKERS = ["CPEXEMUY", "CPI_CHNG", "CPUPXCHG", "ECCPEST", "EUESEMU", "EUITEMUM", "EUPPEMUM", "IP_CHNG", "NAPMNMI", "NAPMPMI", "NFP_TCH", "PCE_CMOM",
                   "RSSAEMUM", "RSTAMOM", "UMRTEMU", "USURTOT"]
for _t in RELEASE_TICKERS:   # raw release actual/survey values: local mode only
    ENTRIES.append(_e(f"bl2_release_{_t}", "bl2", f"macro/release_fields/{_t}_Index.csv", tier=EXCLUDE, description=f"Release-level actual, survey and surprise of {_t.replace('_', ' ')} Index (raw Bloomberg values)", pages=("6",)))
ENTRY_BY_KEY = {e.key: e for e in ENTRIES}

GENERIC_DATE_COLS = ("date", "end", "start", "decision_date", "execution_date", "estimation_date", "reference_date", "max_drawdown_peak", "max_drawdown_trough",
                     "max_drawdown_recovery", "best_month_date", "worst_month_date", "max_turnover_date", "window_start", "window_end", "peak_date", "trough_date",
                     "recovery_date", "accrual_start", "accrual_end", "first_period_end", "last_period_end", "max_abs_change_date")

# ----------------------------------------------------------------------------------------------------------------------------- universe
ASSETS: List[str] = ["Equity", "Government Bonds", "Investment Grade Credit", "Gold", "Private Equity Proxy", "Emerging Debt", "Securitized",
                     "Real Estate", "Inflation Linked", "Convertibles"]
ASSET_SHORT: Dict[str, str] = {"Equity": "Equity", "Government Bonds": "Gov. Bonds", "Investment Grade Credit": "IG Credit", "Gold": "Gold",
                               "Private Equity Proxy": "Private Eq.", "Emerging Debt": "EM Debt", "Securitized": "Securitized", "Real Estate": "Real Estate",
                               "Inflation Linked": "Infl. Linked", "Convertibles": "Convertibles"}
GROUPS: Dict[str, List[str]] = {"Equity-like": ["Equity", "Private Equity Proxy", "Real Estate", "Convertibles"],
                                "Rates & credit": ["Government Bonds", "Investment Grade Credit", "Securitized", "Inflation Linked"],
                                "Diversifiers": ["Gold", "Emerging Debt"]}

# ----------------------------------------------------------------------------------------------------------------------------- strategies
BENCHMARK = "BENCH_REBALANCED"
BL1 = "BL1_FROZEN"
BL2 = "BL2_TREND_ONLY"
MAIN_STRATEGIES: List[str] = [BL1, BL2, BENCHMARK]
STRATEGY_LABELS: Dict[str, str] = {
    BL1: "BL 1.0", BL2: "BL 2.0", BENCHMARK: "Strategic Benchmark",
    "BL2_EQUILIBRIUM_ONLY": "BL 2.0 equilibrium-only (no views, h = 3)",
    "BL2_EQUILIBRIUM_ONLY_H1": "Equilibrium-only, h = 1 (BL 1.0 policy, no views)",
    "BL2_EXPERIMENTAL_REVISED_MACRO": "EXPERIMENTAL: trend + revised-data macro views",
    "ABL_H1_BL2_VIEWS": "Ablation: BL 2.0 views, h = 1 allocation", "ABL_H6_BL2_VIEWS": "Ablation: BL 2.0 views, h = 6",
    "ABL_BL1_VIEWS_BL2_ALLOCATION": "Ablation: BL 1.0 views, BL 2.0 allocation", "ABL_RELATIVE_ONLY": "Ablation: relative trend only",
    "ABL_COMMON_ONLY": "Ablation: common trend only", "ABL_DIAG_OMEGA": "Ablation: diagonal Omega",
    "ABL_IC_EFF_LOW": "Ablation: effective IC 0.03", "ABL_IC_EFF_HIGH": "Ablation: effective IC 0.10",
}
STRATEGY_LONG: Dict[str, str] = {
    BL1: "Black-Litterman 1.0 — frozen Phase 6 targets simulated by the frozen Phase 7 backtest (trend + macro views, kappa 0.30, diagonal Omega, h = 1)",
    BL2: "Black-Litterman 2.0 — published research configuration (trend views only, full Omega, effective IC 0.06, h = 3)",
    BENCHMARK: "Strategic Rebalanced Benchmark — LIQUID_GMP_2026_V1 weights restored at every monthly execution date (frozen Phase 7 S2)",
}
