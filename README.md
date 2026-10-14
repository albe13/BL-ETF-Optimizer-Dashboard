# BL ETF Optimizer — private Streamlit deployment package

Quantitative multi-asset portfolio allocation using Black-Litterman, trend and macroeconomic analysis. This repository is the
self-contained, presentation-ready dashboard of the **BL ETF Optimizer** research project: it compares the Black-Litterman
allocation models **BL 1.0** and **BL 2.0** with the **Strategic Rebalanced Benchmark** on a universe of ten UCITS ETFs
(EUR, total return), over 84 monthly decision dates (2019-10-31 → 2026-09-30) and 83 holding periods (2019-11-01 → 2026-10-01).

The application reads **precomputed, hash-verified artifacts** of the frozen model runs that are bundled under `artifacts/`.
It recomputes no model quantity, needs no database, no Bloomberg Terminal, no network access and no credentials. Everything it
shows is a historical, in-sample research result: it is not investment advice and no forecast of future performance.

## Dashboard overview (ten pages)

| # | Page | Content |
|---|---|---|
| 1 | Executive Overview | performance comparison, growth of EUR 10,000, active performance, current allocation, key findings |
| 2 | Portfolio Allocation | target weights of BL 1.0 and BL 2.0 vs the benchmark at any decision date, active weights, history, attribution |
| 3 | ETF Market Performance | all ten ETFs by default: normalized EUR total-return chart, ten individual panels, drawdowns, rolling volatility, correlations, identities and data audit |
| 4 | Performance Analytics | cumulative and annual returns, monthly distributions, rolling metrics, drawdowns, turnover and costs, statistical tests, attribution, diagnostic paths |
| 5 | Black-Litterman Engine | equilibrium prior Π, trend views, P/Q/Ω, posterior, posterior − prior, active weights, signal-to-weight transmission for BL 2.0 and BL 1.0 |
| 6 | Macro Regime & Economic Outlook | growth/inflation regimes (quadrant and timeline), macro surprises, policy and rates, financial conditions, historical reconstruction at a date |
| 7 | Trend & Signal Analytics | trend signals, composite z-scores, dispersion, persistence, signal-to-view mapping |
| 8 | Historical Portfolio Decisions | per-ETF deterministic explanation of every decision: prior → signal → view → posterior → weight, BL 1.0 and BL 2.0 side by side |
| 9 | Model Methodology | the twelve steps of BL 1.0 and the BL 2.0 changes, equations, parameter status |
| 10 | Limitations & Future Improvements | what is implemented, proposed, experimental or not validated |

A sidebar **decision-date selector** (84 published rebalance dates) is synchronized across pages 2, 5, 6, 7 and 8. The dashboard
compares **only** BL 1.0, BL 2.0 and the Strategic Rebalanced Benchmark; there is no Buy & Hold path and no S&P 500 / MSCI World
comparator.

## Repository layout

```
streamlit_app.py            Streamlit entry point (Community Cloud "main file"), at the repository root
requirements.txt            pinned dependencies
.streamlit/config.toml      theme and server settings (no secrets)
.gitignore
bldash/                     application modules: core/ (registry, hash-verified store, cached model accessors, derived metrics,
                            design system, state, widgets, narratives) and views/ (the ten pages)
artifacts/                  the data bundle: 103 verified CSV/JSON/YAML files (17.7 MB) + ARTIFACT_MANIFEST.json
docs/                       DEPLOYMENT_MANIFEST.md (classification of every table), DASHBOARD_DATA_CONTRACT.md (field inventory and
                            derived-metric conventions), PACKAGE_INVENTORY.md, STANDALONE_VALIDATION_REPORT.md, STANDALONE_VALIDATION_RESULTS.json
tools/verify_package.py     standalone verification of this package (integrity, reconciliation, rendering, security)
tools/build_bundle.py       maintainer tool: rebuilds artifacts/ from the source project (not needed to run or deploy)
DEPLOYMENT_CHECKLIST.md     the exact manual upload and deployment steps
```

## Data integrity

The verification chain of the research project is preserved: **frozen output contract → run manifest → file hash → data loader**.
`artifacts/ARTIFACT_MANIFEST.json` records, for each of the ten frozen sources, the sha256 of the contract and the contract's pin of the
run manifest, and for every bundled file the original pin (`sha256_original`) and the sha256 of the bundled copy (`sha256_bundle`), which
are identical for every file in this package. `bldash/core/store.py` re-hashes every file before parsing it; a mismatch stops the
display of that table, a missing manifest stops the application. Nothing is written at run time.

Data classification (`docs/DEPLOYMENT_MANIFEST.md`): the 95 SAFE_TO_PUBLISH tables and the 8 REQUIRES_LICENSE_REVIEW tables (ETF daily
EUR total-return levels, sleeve-return attribution tables, the equity moving-average diagnostic and the Phase 4 regional macro inputs) are
included under the owner's confirmation that the applicable licence authorizes hosting them in a private repository and a private
application for authorized viewers. The 17 EXCLUDE_FROM_DEPLOYMENT tables (raw Bloomberg market levels and release-level actual/survey
values) are **not** included; the macro page explains their absence where a drill-down would use them. No synthetic data is used anywhere.

## Requirements

- Python **3.9, 3.10, 3.11 or 3.12** (validated locally on Python 3.9.6; use **3.11 or 3.12** on Streamlit Community Cloud).
  Python 3.13 is not supported by the pinned `numpy==2.0.2`.
- `requirements.txt`: streamlit 1.50.0, plotly 7.1.0, pandas 2.3.3, numpy 2.0.2, PyYAML 6.0.3, pyarrow 21.0.0 (exact pins).
- No secrets, environment variables, databases or external services.

## Run locally

```bash
python3 -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
python -m pip install -r requirements.txt
python -m streamlit run streamlit_app.py
```

The app opens at http://localhost:8501. Verify the package at any time with:

```bash
python tools/verify_package.py
```

## Upload to GitHub and deploy on Streamlit Community Cloud

Follow `DEPLOYMENT_CHECKLIST.md` step by step. In short:

1. Upload the **contents** of this folder (not the folder itself) to the root of the private repository
   `albe13/BL-ETF-Optimizer-Dashboard`, branch `main`, so that `streamlit_app.py` sits at the repository root.
   Use the git command line or GitHub Desktop rather than the browser upload, so that the hidden files `.streamlit/config.toml`
   and `.gitignore` are included.
2. On https://share.streamlit.io choose *Create app → Deploy a public app from GitHub* (the wording is the same for private
   repositories), select the repository, branch `main`, main file path `streamlit_app.py`, and in *Advanced settings* set the
   Python version to **3.11** (or 3.12). No secrets are required.
3. After the first build, open the app settings → *Sharing* and make sure that **only invited viewers** can open the app; invite the
   authorized viewers by e-mail. Do not share the URL publicly.

## Privacy requirements

- The GitHub repository must remain **private**; the Streamlit application must remain **private** (viewer access by invitation).
- The package contains Bloomberg-derived historical series under a licence that permits private hosting for authorized viewers only:
  do not fork the repository publicly, do not publish the artifacts elsewhere, do not add raw Bloomberg workbooks or any further data.
- The package contains no credentials, tokens, personal financial information or absolute local paths (checked by
  `tools/verify_package.py`); keep `.streamlit/secrets.toml`, `.env` files and virtual environments out of the repository (they are ignored
  by `.gitignore`).
- The application collects no usage statistics (`gatherUsageStats = false`) and makes no network requests.

## Known limitations

- Historical, in-sample results of a research project (2019-11 → 2026-10): not investment advice, no forecast of future performance.
- BL 2.0 runs in a research configuration whose parameters are provisional and await ratification (see Page 10); BL 2.1 is not implemented.
- Macro surprise series are a REVISED_DATA_PROXY (revised actuals against point-in-time surveys), labelled as such on Page 6; the
  release-level raw values are not part of the package, so the release drill-down on Page 6 shows an explanation instead of the raw table.
- The last decision date (2026-09-30) has no realized holding period inside the frozen backtest window and is displayed as such.
- ETF Sharpe ratios on Page 3 are defined only on the holding-period calendar of the backtest, where the realized EUR cash return is published.
- The dashboard presents frozen artifacts: updating the data requires a new frozen run in the source project and a rebuild of `artifacts/`
  with `tools/build_bundle.py --include-review`.
