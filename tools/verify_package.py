"""Standalone verification of this deployment package (no access to the source project is needed or used).

    python -m pip install -r requirements.txt
    python tools/verify_package.py            # from the package root; exit code 0 only if every check passes

Checks: package structure; bundle integrity (every file re-hashed against ARTIFACT_MANIFEST.json, unredacted copies pinned to the frozen contracts,
no EXCLUDE_FROM_DEPLOYMENT table, no required table missing); reconciliation of the displayed metrics with the stored ones; alignment of the 84
decision dates; ETF universe (ten identities, ten total-return series, ten panel charts); headless rendering of all ten pages (and of the entry
point) in bundle mode on several decision dates; no model/solver/Bloomberg/network imports; dependency pins; security hygiene (no credentials,
absolute paths, dot-env files, caches, symbolic links or Git metadata). Writes docs/STANDALONE_VALIDATION_RESULTS.json and docs/PACKAGE_INVENTORY.md.
"""

from __future__ import annotations

import hashlib
import importlib.metadata as im
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

APP = Path(__file__).resolve().parents[1]
os.environ["BL_DASHBOARD_SOURCE"] = "bundle"
sys.path.insert(0, str(APP))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from bldash.core import derived as D, registry as R  # noqa: E402
from bldash.core.store import ArtifactStore, IntegrityError, sha256_file  # noqa: E402

PAGES = ["p01_overview", "p02_allocation", "p03_etf", "p04_performance", "p05_engine", "p06_macro", "p07_trend", "p08_decisions", "p09_methodology", "p10_limitations"]
DATE_PAGES = ["p02_allocation", "p05_engine", "p06_macro", "p07_trend", "p08_decisions"]
HIST_DATES = ["2019-10-31", "2020-03-31", "2022-09-30"]
RESULTS = []
SKIP_DIRS = {"__pycache__", ".pytest_cache", ".git", ".venv", "venv"}
TEXT_EXT = {".py", ".md", ".txt", ".toml", ".json", ".yaml", ".yml", ".csv", ".sh", ".cfg", ".ini", ""}


def check(cat: str, name: str, ok: bool, detail: str = "") -> None:
    RESULTS.append({"category": cat, "check": name, "status": "PASS" if ok else "FAIL", "detail": detail})
    print(f"[{'PASS' if ok else 'FAIL'}] {cat}: {name}{(' — ' + detail) if detail else ''}")


def package_files():
    for p in sorted(APP.rglob("*")):
        if any(part in SKIP_DIRS for part in p.relative_to(APP).parts):
            continue
        if p.is_file() or p.is_symlink():
            yield p


def render(pages, dates):
    code = (
        "import os, sys, json\nos.environ['BL_DASHBOARD_SOURCE'] = 'bundle'\nsys.path.insert(0, %r)\nfrom streamlit.testing.v1 import AppTest\nout = {}\n"
        "for page in %r:\n    for d in %r:\n"
        "        script = 'import os, sys; os.environ[\"BL_DASHBOARD_SOURCE\"] = \"bundle\"; sys.path.insert(0, %%r)\\nimport streamlit as st\\n' %% %r\n"
        "        script += ('st.session_state[\"bl_decision_date\"] = __import__(\"pandas\").Timestamp(%%r)\\n' %% d) if d else ''\n"
        "        script += 'from bldash.views import ' + page + ' as P\\nP.render()\\n'\n"
        "        at = AppTest.from_string(script, default_timeout=600); at.run()\n"
        "        out[page + '@' + (d or 'default')] = {'exceptions': [e.message[:300] for e in at.exception], 'errors': [e.value[:200] for e in at.error],\n"
        "                                              'n_plotly': len(at.get('plotly_chart')), 'n_dataframes': len(at.dataframe), 'n_markdown': len(at.markdown)}\n"
        "at = AppTest.from_file(%r, default_timeout=600); at.run()\n"
        "out['streamlit_app.py@default'] = {'exceptions': [e.message[:300] for e in at.exception], 'errors': [e.value[:200] for e in at.error], 'n_plotly': len(at.get('plotly_chart')),\n"
        "                                   'n_dataframes': len(at.dataframe), 'n_markdown': len(at.markdown)}\n"
        "print('@@' + json.dumps(out))\n") % (str(APP), pages, dates, str(APP), str(APP / "streamlit_app.py"))
    env = {k: v for k, v in os.environ.items() if k not in ("PYTHONPATH",)}
    env["BL_DASHBOARD_SOURCE"] = "bundle"
    proc = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, cwd=str(APP), env=env)
    line = [l for l in proc.stdout.splitlines() if l.startswith("@@")]
    if not line:
        return None, (proc.stderr or proc.stdout)[-1200:]
    return json.loads(line[-1][2:]), ""


def main() -> int:
    t0 = time.time()
    # ------------------------------------------------------------------------------------------ structure
    for rel in ("streamlit_app.py", "requirements.txt", "README.md", "DEPLOYMENT_CHECKLIST.md", ".gitignore", ".streamlit/config.toml", "artifacts/ARTIFACT_MANIFEST.json",
                "bldash/__init__.py", "bldash/core/store.py", "bldash/views/p01_overview.py"):
        check("structure", f"{rel} present at the expected location", (APP / rel).is_file())
    check("structure", "entry point is at the package root (no nested app folder)", (APP / "streamlit_app.py").is_file() and not list(APP.glob("*/streamlit_app.py")))
    check("structure", "no symbolic links in the package", not [str(p.relative_to(APP)) for p in package_files() if p.is_symlink()])
    check("structure", "no Git metadata or virtual environment in the package", not [d for d in (".git", ".venv", "venv") if (APP / d).exists()])
    # ------------------------------------------------------------------------------------------ integrity
    try:
        store = ArtifactStore(mode="bundle")
        check("integrity", "bundle manifest loads; every listed table is registered, unredacted copies are pinned to the frozen contracts, no EXCLUDE table listed", bool(store.report["ok"]), str(store.report["problems"]))
    except IntegrityError as exc:
        check("integrity", "bundle manifest consistent with the registry", False, str(exc))
        return finish(t0)
    v = store.verify_all()
    excl = {e.key for e in R.ENTRIES if e.tier == R.EXCLUDE}
    check("integrity", "every bundled file hashes to its manifest pin", v["ok"], f"{v['checked']} files checked; mismatched {v['mismatched']}")
    check("integrity", "the only absent tables are the EXCLUDE_FROM_DEPLOYMENT ones (never shipped)", set(v["absent"]) <= excl, f"absent {len(v['absent'])}: {sorted(set(v['absent']) - excl) or 'all EXCLUDE tier'}")
    check("integrity", "no required table missing", not store.missing_required(), str(store.missing_required()))
    man = json.loads((APP / "artifacts" / "ARTIFACT_MANIFEST.json").read_text())
    rel_ok = all(not Path(f["bundle_path"]).is_absolute() and ".." not in Path(f["bundle_path"]).parts for f in man["files"].values())
    check("integrity", "all bundle paths are relative and inside artifacts/", rel_ok)
    srcs = man["sources"]
    check("integrity", "ten frozen sources pinned (contract sha256 + manifest sha256) with FROZEN / pinned status",
          len(srcs) == 10 and all(s.get("contract_sha256") or k == "cfg" for k, s in srcs.items()) and all(s.get("manifest_sha256") or k == "cfg" for k, s in srcs.items())
          and all(s.get("contract_status") in ("FROZEN", "PINNED_BY_BL2_CONTRACT", "") for s in srcs.values()), str({k: s.get("contract_status") for k, s in srcs.items()}))
    tiers = {f["tier"] for f in man["files"].values()}
    check("integrity", "bundle tiers are SAFE_TO_PUBLISH and REQUIRES_LICENSE_REVIEW only (EXCLUDE never, nothing redacted)", tiers <= {"SAFE_TO_PUBLISH", "REQUIRES_LICENSE_REVIEW"} and not any(f["redacted"] for f in man["files"].values()), str(sorted(tiers)))
    # ------------------------------------------------------------------------------------------ reconciliation
    sm = store.read("bl2_summary_metrics").set_index("strategy")
    mr = store.read("bl2_monthly_returns")
    nav = store.read("bl2_nav_daily")
    p7 = store.read("p7_summary_metrics").set_index("strategy")
    bench = mr[mr.strategy == R.BENCHMARK].set_index("end")["net_return"]
    cash = mr[mr.strategy == R.BENCHMARK].set_index("end")["cash_return"]
    worst = 0.0
    for strat in R.MAIN_STRATEGIES:
        r = mr[mr.strategy == strat].set_index("end")["net_return"]
        n = nav[nav.strategy == strat].set_index("date")["nav_net"]
        diffs = [abs(D.annualized_vol_monthly(r) - sm.loc[strat, "annualized_volatility"]), abs(D.sharpe_excess(r, cash) - sm.loc[strat, "sharpe_excess_over_cash"]),
                 abs(D.cagr(n) - sm.loc[strat, "cagr_net"]), abs(D.max_drawdown(n)["max_drawdown"] - sm.loc[strat, "max_drawdown"])]
        if strat != R.BENCHMARK:
            diffs += [abs(D.tracking_error(r, bench) - sm.loc[strat, "tracking_error_realized"]), abs(D.information_ratio(r, bench) - sm.loc[strat, "information_ratio"])]
        worst = max(worst, max(diffs))
    check("reconciliation", "displayed vol / Sharpe / CAGR / max drawdown / TE / IR reproduce the stored metrics for BL 1.0, BL 2.0 and the benchmark", worst < 1e-9, f"max abs difference {worst:.2e}")
    same = all(abs(sm.loc[a, c] - p7.loc[b, c]) < 1e-12 for a, b in ((R.BL1, "S1_BL"), (R.BENCHMARK, "S2_GMP_REBALANCED")) for c in ("cagr_net", "annualized_volatility", "sharpe_excess_over_cash", "max_drawdown", "annual_turnover"))
    check("reconciliation", "BL 1.0 and benchmark metrics in the BL 2.0 run equal the frozen Phase 7 backtest (S1_BL, S2_GMP_REBALANCED)", same)
    check("reconciliation", "headline CAGR 8.69 % (BL 1.0), 8.55 % (BL 2.0), 7.07 % (benchmark)",
          abs(sm.loc[R.BL1, "cagr_net"] - 0.0869) < 5e-4 and abs(sm.loc[R.BL2, "cagr_net"] - 0.0855) < 5e-4 and abs(sm.loc[R.BENCHMARK, "cagr_net"] - 0.0707) < 5e-4,
          ", ".join(f"{s}: {sm.loc[s, 'cagr_net']:.2%}" for s in R.MAIN_STRATEGIES))
    check("reconciliation", "only BL 1.0, BL 2.0 and the strategic benchmark are the compared strategies (no Buy & Hold, S&P 500 or MSCI World series)",
          R.MAIN_STRATEGIES == [R.BL1, R.BL2, R.BENCHMARK] and not any(s in {"BUY_AND_HOLD", "SPX", "MSCI_WORLD"} for s in sm.index), str(list(sm.index)))
    dates = [pd.Timestamp(d) for d in store.meta["model_dates"]]
    cal = store.read("p7_execution_calendar")
    check("alignment", "84 decision dates in the bundle metadata equal the Phase 7 execution calendar", len(dates) == 84 and list(pd.to_datetime(cal["decision_date"])) == dates)
    t2 = store.read("bl2_targets_long"); t2 = t2[t2.label == R.BL2]
    t1 = store.read("p6_target_weights")
    w2 = t2.pivot(index="date", columns="asset_class", values="target_weight")[R.ASSETS]
    w1 = t1.pivot(index="date", columns="asset_class", values="target_weight")[R.ASSETS]
    bw = pd.Series({k: float(v) for k, v in store.meta["benchmark_weights"].items()}).reindex(R.ASSETS)
    check("alignment", "BL 1.0 and BL 2.0 target weights on every decision date sum to one and are long-only; benchmark weights sum to one",
          len(w1) == 84 and len(w2) == 84 and abs(w2.sum(axis=1) - 1).max() < 1e-9 and abs(w1.sum(axis=1) - 1).max() < 1e-9 and (w2 >= -1e-12).all().all() and (w1 >= -1e-12).all().all() and abs(bw.sum() - 1) < 1e-12)
    check("alignment", "views, posterior, trend and macro tables carry the same 84 decision dates",
          sorted(pd.to_datetime(store.read("bl2_posterior")["date"]).unique()) == dates and sorted(pd.to_datetime(store.read("bl2_trend_signals")["estimation_date"]).unique()) == dates
          and sorted(pd.to_datetime(store.read("bl2_macro_wide")["date"]).unique()) == dates)
    mm = store.read("bl2_macro_metadata")
    check("alignment", "macro vintage statement present (ACTUAL revised, surprise REVISED_DATA_PROXY) so the vintage warning stays visible", mm["vintage"]["surprise_status"] == "REVISED_DATA_PROXY" and mm["vintage"]["actual"] == "REVISED")
    # ------------------------------------------------------------------------------------------ ETF universe
    from bldash.core import model as M
    meta = M.etf_meta(store)
    check("etf", "ten ETF identities with full name, ticker, ISIN and asset-class group", len(meta) == 10 and meta["etf_name"].notna().all() and meta["ticker"].notna().all() and meta["isin"].str.len().eq(12).all() and list(meta.index) == R.ASSETS)
    lv = M.etf_levels(store)
    check("etf", "ten EUR total-return series bundled (M0 levels, 2016-10-06 onward, no gaps on the valuation calendar)",
          lv is not None and list(lv.columns) == R.ASSETS and lv.index.min() == pd.Timestamp("2016-10-06") and lv.notna().all().all() and len(lv) > 2400,
          f"{0 if lv is None else len(lv)} dates" + (f", {lv.index.min().date()} → {lv.index.max().date()}" if lv is not None else ""))
    if lv is not None and store.available("bl2_att_trend_active"):
        ex = pd.DatetimeIndex(pd.to_datetime(cal["execution_date"]))
        att = store.read("bl2_att_trend_active")
        md2 = 0.0
        for a in R.ASSETS:
            jj = pd.concat([D.returns_on_calendar(lv[a], ex).rename("d"), att[att.asset_class == a].set_index("end")["sleeve_return"].rename("s")], axis=1).dropna()
            md2 = max(md2, (jj.d - jj.s).abs().max())
        check("etf", "ETF monthly returns from the bundled levels equal the stored sleeve returns of the backtest (10 ETFs × 83 periods)", md2 < 1e-12, f"max abs difference {md2:.2e}")
    # ------------------------------------------------------------------------------------------ rendering
    t = time.time()
    out, err = render(PAGES, [None])
    if out is None:
        check("rendering", "ten pages render headless in bundle mode", False, err)
    else:
        bad = {k: v for k, v in out.items() if v["exceptions"] or v["errors"]}
        check("rendering", f"all ten pages and the entry point render without exception in bundle mode ({len(out)} runs, {time.time() - t:.0f}s)", not bad, json.dumps(bad)[:800] if bad else "")
        n3 = out.get("p03_etf@default", {}).get("n_plotly", 0)
        check("etf", "ETF Market Performance page renders the comparative chart, the ten individual ETF panels and the risk charts (14 Plotly figures)", n3 >= 14, f"{n3} Plotly figures")
        check("rendering", "every analytical page carries at least one Plotly figure (pages 1–8)", all(out.get(f"{p}@default", {}).get("n_plotly", 0) >= 1 for p in PAGES[:8]), str({p: out.get(f"{p}@default", {}).get("n_plotly") for p in PAGES[:8]}))
        check("rendering", "entry point builds the navigation and renders the default page", out.get("streamlit_app.py@default", {}).get("n_markdown", 0) > 0)
    t = time.time()
    out2, err2 = render(DATE_PAGES, HIST_DATES)
    if out2 is None:
        check("rendering", "date-aware pages render on historical decision dates", False, err2)
    else:
        bad2 = {k: v for k, v in out2.items() if v["exceptions"] or v["errors"]}
        check("rendering", f"date-aware pages (allocation, engine, macro, trend, decisions) render on {len(HIST_DATES)} historical decision dates ({len(out2) - 1} runs, {time.time() - t:.0f}s)", not bad2, json.dumps(bad2)[:800] if bad2 else "")
    # ------------------------------------------------------------------------------------------ no recomputation / no external dependencies
    code_files = list((APP / "bldash").rglob("*.py")) + [APP / "streamlit_app.py"]
    forbidden = [str(p.relative_to(APP)) for p in code_files if re.search(r"^\s*(import|from)\s+(src\b|bl2\b|blpapi|xbbg|cvxpy|scipy|sklearn|statsmodels|requests|urllib|httpx|socket)", p.read_text(), re.M)]
    check("isolation", "no import of the model engines, solvers, Bloomberg or network libraries in the app code", not forbidden, str(forbidden))
    check("isolation", "app imports resolve from the package alone (no reference to the original bl_dashboard namespace, no sys.path entry outside the package)",
          not [str(p.relative_to(APP)) for p in code_files if re.search(r"bl_dashboard\b|sys\.path\.(insert|append)\([^)]*(parents\[3\]|\.parent\.parent|\.\./)", p.read_text())])
    # ------------------------------------------------------------------------------------------ dependencies
    req = (APP / "requirements.txt").read_text()
    pinned = dict(re.findall(r"^([A-Za-z]+)==([0-9.]+)", req, re.M))
    check("dependencies", "requirements pinned (==) for streamlit, plotly, pandas, numpy, PyYAML, pyarrow", all(k in pinned for k in ("streamlit", "plotly", "pandas", "numpy", "PyYAML", "pyarrow")))
    try:
        vers = {pkg: im.version(pkg) for pkg in pinned}
        check("dependencies", f"installed versions equal the pins (Python {sys.version.split()[0]})", all(vers[k] == pinned[k] for k in vers), str(vers))
    except Exception as exc:  # pragma: no cover
        check("dependencies", "installed versions equal the pins", False, str(exc))
    # ------------------------------------------------------------------------------------------ security hygiene
    files = list(package_files())
    names = [p.name for p in files]
    check("security", "no dot-env, key, certificate, token or secrets files", not [n for n in names if n.startswith(".env") or n.endswith((".pem", ".key", ".p12", ".pfx")) or n.startswith("id_rsa") or n == "secrets.toml"])
    check("security", "no .DS_Store, cache, log or temporary files", not [n for n in names if n in (".DS_Store", "Thumbs.db") or n.endswith((".pyc", ".log", ".tmp"))])
    caches = [str(d.relative_to(APP)) for d in APP.rglob("*") if d.is_dir() and d.name in ("__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache")]
    for d in caches:   # byte-code caches created by this verification run are removed again so that the package is uploaded without them
        import shutil
        shutil.rmtree(APP / d, ignore_errors=True)
    check("security", "no byte-code or test cache directories left in the package (caches created by this run were removed)", not list(APP.rglob("__pycache__")), f"removed: {caches}" if caches else "")
    sec_pat = re.compile(r"(api[_-]?key|password|passwd|secret|token|bearer|aws_access|private[_-]?key)\s*[:=]\s*['\"][^'\"]{4,}", re.I)
    path_pat = re.compile("(" + "/Users" + "/|" + "/home" + "/|" + "/mnt/c" + "/|[A-Z]:" + "\\\\" + ")")
    hits, path_hits = [], []
    for p in files:
        if p.suffix.lower() not in TEXT_EXT or p.name in ("verify_package.py",):
            continue
        txt = p.read_text(encoding="utf-8", errors="ignore")
        if sec_pat.search(txt):
            hits.append(str(p.relative_to(APP)))
        if path_pat.search(txt):
            path_hits.append(str(p.relative_to(APP)))
    check("security", "no hard-coded credentials, API keys or tokens in any text file of the package", not hits, str(hits))
    check("security", "no absolute local paths in any text file of the package", not path_hits, str(path_hits))
    check("security", "config.toml collects no usage statistics and needs no secrets", 'gatherUsageStats = false' in (APP / ".streamlit" / "config.toml").read_text() and not (APP / ".streamlit" / "secrets.toml").exists())
    # ------------------------------------------------------------------------------------------ inventory
    inv = [(str(p.relative_to(APP)), p.stat().st_size, sha256_file(p)) for p in files if p.relative_to(APP).as_posix() not in ("docs/PACKAGE_INVENTORY.md", "docs/STANDALONE_VALIDATION_RESULTS.json")]
    total = sum(s for _, s, _ in inv)
    lines = ["# Package inventory — BL_ETF_OPTIMIZER_STREAMLIT_DEPLOY\n", f"Generated {datetime.now(timezone.utc).isoformat(timespec='seconds')} by `tools/verify_package.py` · {len(inv)} files · {total / 1e6:.1f} MB "
             f"(plus this inventory and `docs/STANDALONE_VALIDATION_RESULTS.json`, generated by the same tool).\n", "| file | bytes | sha256 |", "|---|---:|---|"]
    lines += [f"| `{rel}` | {size:,} | `{sha}` |" for rel, size, sha in inv]
    by_dir = {}
    for rel, size, _ in inv:
        by_dir.setdefault(rel.split("/")[0] if "/" in rel else "(root)", [0, 0])
        by_dir[rel.split("/")[0] if "/" in rel else "(root)"][0] += 1
        by_dir[rel.split("/")[0] if "/" in rel else "(root)"][1] += size
    lines += ["\n| directory | files | MB |", "|---|---:|---:|"] + [f"| `{d}` | {n} | {b / 1e6:.2f} |" for d, (n, b) in sorted(by_dir.items())]
    (APP / "docs").mkdir(exist_ok=True)
    (APP / "docs" / "PACKAGE_INVENTORY.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    check("inventory", f"package inventory written ({len(inv)} files, {total / 1e6:.1f} MB)", True)
    return finish(t0)


def finish(t0: float) -> int:
    n_pass = sum(1 for r in RESULTS if r["status"] == "PASS")
    summary = {"generated": datetime.now(timezone.utc).isoformat(timespec="seconds"), "python": sys.version.split()[0], "package_root": "BL_ETF_OPTIMIZER_STREAMLIT_DEPLOY",
               "passed": n_pass, "total": len(RESULTS), "elapsed_s": round(time.time() - t0, 1), "results": RESULTS}
    (APP / "docs").mkdir(exist_ok=True)
    (APP / "docs" / "STANDALONE_VALIDATION_RESULTS.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
    print(f"\n{n_pass}/{len(RESULTS)} checks passed in {summary['elapsed_s']}s -> docs/STANDALONE_VALIDATION_RESULTS.json")
    return 0 if n_pass == len(RESULTS) else 1


if __name__ == "__main__":
    sys.exit(main())
