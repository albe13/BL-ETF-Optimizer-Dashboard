# Standalone validation report — BL_ETF_OPTIMIZER_STREAMLIT_DEPLOY

Date: 2026-10-14. Package built from the completed `bl_dashboard/` presentation dashboard of the BL GMP Optimization project (ten pages,
45/45 validation checks and 34/34 tests in the source project). This report records the independent validation of the **standalone**
package, performed on a copy of the folder placed outside the project, with a freshly created virtual environment and nothing of the
source project on the import path.

## 1. Environment

| item | value |
|---|---|
| Python | 3.9.6 (local; cloud recommendation 3.11 or 3.12; 3.13 unsupported by numpy 2.0.2) |
| Virtual environment | `python3 -m venv` (clean), `pip install -r requirements.txt` from PyPI: exit 0 |
| Installed pins | streamlit 1.50.0 · plotly 7.1.0 · pandas 2.3.3 · numpy 2.0.2 · PyYAML 6.0.3 · pyarrow 21.0.0 (all equal to `requirements.txt`) |
| Source project importable from the test copy | no (`src`, `bl2` not importable; project path absent from `sys.path`) |
| Entry point | `streamlit run streamlit_app.py` from the package root (port 8510 in the test) |
| Data source reported by the app | "deployment bundle" (sidebar) |

## 2. Automated checks — `tools/verify_package.py` (47/47 PASS)

Results in `docs/STANDALONE_VALIDATION_RESULTS.json`; the inventory of every file with size and sha256 in `docs/PACKAGE_INVENTORY.md`.

| category | checks | outcome |
|---|---|---|
| structure | entry point at the root, required files present, no symbolic links, no Git metadata or virtual environment | PASS |
| integrity | bundle manifest consistent with the registry; 103 files re-hashed against their pins, 0 mismatches; only the 17 EXCLUDE_FROM_DEPLOYMENT tables absent; no required table missing; relative bundle paths; ten frozen sources pinned (contract sha256 + manifest sha256, status FROZEN / pinned); tiers SAFE_TO_PUBLISH + REQUIRES_LICENSE_REVIEW only, nothing redacted | PASS |
| reconciliation | displayed volatility / Sharpe / CAGR / max drawdown / tracking error / information ratio reproduce the stored metrics (max abs difference 1.1e-16); BL 1.0 and benchmark metrics of the BL 2.0 run equal the frozen Phase 7 backtest; headline CAGR 8.69 % / 8.55 % / 7.07 %; compared strategies restricted to BL 1.0, BL 2.0 and the strategic benchmark | PASS |
| alignment | 84 decision dates equal the execution calendar; BL 1.0 and BL 2.0 weights sum to one, long-only, on all 84 dates; views, posterior, trend and macro tables share the 84 dates; macro vintage statement (REVISED_DATA_PROXY) present | PASS |
| ETF universe | ten identities (name, ticker, ISIN, group); ten EUR total-return series (2,491 dates, 2016-10-06 → 2026-10-05, no gaps); monthly ETF returns from the bundled levels equal the stored sleeve returns bitwise (10 × 83); ETF page renders 14 Plotly figures (comparative chart, ten panels, drawdowns, rolling volatility, correlation matrix) | PASS |
| rendering | ten pages and the entry point render headless in bundle mode without exception; pages 1–8 each carry Plotly figures (3 / 9 / 14 / 17 / 17 / 17 / 20 / 4); the five date-aware pages render on 2019-10-31, 2020-03-31 and 2022-09-30 | PASS |
| isolation | no import of model engines, solvers, Bloomberg or network libraries; no reference to the original namespace or to paths outside the package | PASS |
| dependencies | exact pins; installed versions equal the pins | PASS |
| security | no dot-env / key / certificate / token files; no .DS_Store, caches, logs; no credentials or API keys in any text file; no absolute local paths in any text file; usage statistics disabled; no secrets file | PASS |

## 3. Interactive verification in a browser (isolated server)

| requirement | observation |
|---|---|
| 1 successful startup | server started; "You can now view your Streamlit app"; no Python error in the log |
| 2 no missing imports · 3 no missing files · 4 no broken relative paths · 5 no integrity errors | app started in bundle mode; sidebar shows the BL 2.0 run and the BL 1.0 backtest identifiers |
| 6 all ten ETF charts | ETF Market Performance: comparative chart with ten lines; ten panels (iShares Core MSCI World, Xtrackers II Global Government Bond, iShares Global Corp Bond EUR Hedged, Invesco Physical Gold, Xtrackers LPX Private Equity, iShares J.P. Morgan $ EM Bond EUR Hedged, iShares US MBS, SPDR Dow Jones Global Real Estate, iShares Global Inflation Linked, convertibles) each with full name, ticker, ISIN, hedging and income treatment, CAGR, volatility, Sharpe, drawdown and total return; risk tabs populated |
| 7 BL 1.0 · 8 BL 2.0 · 9 benchmark | Executive Overview: CAGR 8.69 % / 8.55 % / 7.07 %, Sharpe 0.78 / 0.81 / 0.64, max drawdown −22.3 % / −20.7 % / −22.5 %, growth of EUR 10,000 to 17,792 / 17,632 / 16,038 |
| 10 historical date selection | sidebar selector set to 2020-03-31: caption "Decision 2020-03-31 (close) · execution 2020-04-01 · return observed to 2020-05-04"; Historical Portfolio Decisions followed (TE cap binding for BL 2.0, planned turnover 2.0 % / 7.2 %, regime Disinflationary slowdown) |
| 11 macro regime charts | Macro Regime & Economic Outlook renders with the data-vintage note and the four tabs |
| 12 trend analytics | Trend & Signal Analytics renders (measure → standardize → … flow and tabs) |
| 13 Black-Litterman diagnostics | Black-Litterman Engine renders for BL 2.0 and BL 1.0 (prior Π, views, posterior, weights) |
| 14 historical decision explanations | Historical Portfolio Decisions renders the one-view summary and the A–P sections at the latest and at a historical date |
| 15 methodology and limitations | both reference pages render |
| 16 no model recomputation | app code imports no engine, solver or Bloomberg library; every figure is read from the bundle; derived display metrics reconcile with the stored ones |
| 17 no original repository file modified | protected-artifact hash verification PASS (8,425 files; 0 added, 0 removed, 0 changed); `bl_dashboard/` byte-identical except the verification record rewritten by the verification command itself |

Browser console: the only entries are two `404` probes per deep link (`/<page>/_stcore/health`, `/<page>/_stcore/host-config`) that Streamlit issues before
retrying at the root; they are a known behaviour of Streamlit multipage deep links and not application errors.

## 4. Differences from the source dashboard

The application modules are byte-identical copies of `bl_dashboard/bldash/` except `bldash/core/store.py`, where three standalone adaptations were made:
the bundle under `artifacts/` takes precedence over a source repository when both exist (the package must never depend on the project), the source
project root can be set with `BL_DASHBOARD_REPO_ROOT` for the maintainer rebuild tool, and the bundle manifest is checked for consistency with the
registry at start-up (every unredacted copy must carry the contract pin of the published file, no EXCLUDE table may be listed) with an `IntegrityError`
on violation. The entry point differs only in its docstring. Hash verification of every file before parsing is unchanged.

## 5. Open items (user actions)

- Upload the contents of the folder to the private repository and deploy privately as described in `DEPLOYMENT_CHECKLIST.md` (not performed).
- Keep the repository and the application private; invite authorized viewers only.
- Choose Python 3.11 or 3.12 in the Streamlit Community Cloud advanced settings.
