"""Rebuild artifacts/ (the hash-verified data bundle) from the verified source project. Maintainer tool; not needed to run or deploy the app.

    python3 tools/build_bundle.py --include-review          # the package's configuration: SAFE_TO_PUBLISH + REQUIRES_LICENSE_REVIEW tables
    python3 tools/build_bundle.py                           # SAFE_TO_PUBLISH only (REVIEW tables as redacted copies where declared)
    BL_DASHBOARD_REPO_ROOT=/path/to/project python3 tools/build_bundle.py --include-review   # when the package does not sit inside the project

Requires the source project (its outputs/ contracts and frozen run directories); reads them only. Writes artifacts/ and docs/DEPLOYMENT_MANIFEST.md.
Classification (bldash/core/registry.py): SAFE_TO_PUBLISH -> copied; REQUIRES_LICENSE_REVIEW -> copied only with --include-review (otherwise a
SAFE_REDACTED copy without the licensed columns where the registry declares `redact`); EXCLUDE_FROM_DEPLOYMENT -> never copied. ARTIFACT_MANIFEST.json
records, for every file, the original contract pin and the sha256 of the bundled copy, so the loader verifies exactly what was published.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

APP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP))
from bldash.core import registry as R  # noqa: E402
from bldash.core.store import REPO_ROOT, ArtifactStore, sha256_file  # noqa: E402

TIER_NAMES = {R.SAFE: "SAFE_TO_PUBLISH", R.REVIEW: "REQUIRES_LICENSE_REVIEW", R.EXCLUDE: "EXCLUDE_FROM_DEPLOYMENT"}
RATIONALE = {
    R.SAFE: "model output, standardized measurement, weight, metric, test statistic or hash: no licensed observation can be recovered from it",
    R.REVIEW: "derived from licensed market data at a resolution that may count as redistribution (ETF total-return levels/returns, raw macro inputs): "
              "included under the user's confirmation that the licence authorizes private hosting for authorized viewers",
    R.EXCLUDE: "raw Bloomberg observations (levels, release actual/survey values): never redistributed",
}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--include-review", action="store_true", help="bundle the REQUIRES_LICENSE_REVIEW tables in full (licence confirmed by the user)")
    ap.add_argument("--out", default=str(APP / "artifacts"))
    args = ap.parse_args(argv)
    out = Path(args.out)
    if not (REPO_ROOT / R.SOURCES["bl2"]["contract"]).exists():
        print(f"source project not found at {REPO_ROOT} (set BL_DASHBOARD_REPO_ROOT)")
        return 1
    store = ArtifactStore(mode="repo")
    ver = store.verify_all()
    if ver["mismatched"]:
        print("refusing to build: hash mismatches", ver["mismatched"])
        return 1
    prev = out / "ARTIFACT_MANIFEST.json"      # clear a previous bundle: only files listed by its manifest, then empty directories
    if prev.exists():
        old = json.loads(prev.read_text())
        for item in old.get("files", {}).values():
            p = out / item["bundle_path"]
            if p.exists():
                p.unlink()
        prev.unlink()
        for d in sorted((p for p in out.rglob("*") if p.is_dir()), key=lambda p: -len(p.parts)):
            if not any(d.iterdir()):
                d.rmdir()
    out.mkdir(parents=True, exist_ok=True)
    files, rows = {}, []
    for e in R.ENTRIES:
        r = store.resolve(e.key)
        tier_name = TIER_NAMES[e.tier]
        if not r.present:
            rows.append({"key": e.key, "source": e.source, "path": e.path, "tier": tier_name, "included": "no (absent in repository)", "bundle_path": "", "bytes": 0, "rationale": RATIONALE[e.tier]})
            continue
        size = r.path.stat().st_size
        include, redacted, bundle_tier = False, False, tier_name
        if e.tier == R.SAFE:
            include = True
        elif e.tier == R.REVIEW:
            if args.include_review:
                include = True
            elif e.redact and e.kind == "csv":
                include, redacted, bundle_tier = True, True, "SAFE_REDACTED"
        if not include:
            rows.append({"key": e.key, "source": e.source, "path": e.path, "tier": tier_name, "included": "no", "bundle_path": "", "bytes": size, "rationale": RATIONALE[e.tier]})
            continue
        rel = Path(e.source) / (Path(e.path).name if e.source == "cfg" else e.path)
        dst = out / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        if redacted:
            df = pd.read_csv(r.path, float_precision="round_trip")
            keep = [c for c in df.columns if c not in e.redact]
            df[keep].to_csv(dst, index=False)
        else:
            shutil.copyfile(r.path, dst)
        files[e.key] = {"bundle_path": rel.as_posix(), "source": e.source, "path": e.path, "kind": e.kind, "tier": bundle_tier, "redacted": redacted,
                        "redacted_columns": list(e.redact) if redacted else [], "sha256_original": r.sha_expected, "sha256_bundle": sha256_file(dst), "bytes": dst.stat().st_size, "run_id": r.run_id}
        rows.append({"key": e.key, "source": e.source, "path": e.path, "tier": tier_name, "included": "yes" + (" (redacted copy, SAFE_REDACTED)" if redacted else ""), "bundle_path": rel.as_posix(),
                     "bytes": dst.stat().st_size, "rationale": RATIONALE[e.tier] + (f"; columns removed: {', '.join(e.redact)}" if redacted else "")})
    sources = {}
    for name, s in store.report["sources"].items():
        sources[name] = {"label": s["label"], "run_id": s.get("run_id", ""), "contract": s.get("contract", ""), "contract_sha256": s.get("contract_sha256", ""), "contract_status": s.get("contract_status", ""),
                         "manifest_sha256": s.get("manifest_sha256_pin", ""), "n_files": sum(1 for f in files.values() if f["source"] == name)}
    tiers = ["SAFE_TO_PUBLISH"] + (["REQUIRES_LICENSE_REVIEW"] if args.include_review else ["SAFE_REDACTED"])
    manifest = {"built": datetime.now(timezone.utc).isoformat(timespec="seconds"), "builder": "tools/build_bundle.py (BL_ETF_OPTIMIZER_STREAMLIT_DEPLOY)", "tiers_included": tiers,
                "sources": sources, "files": files, "meta": store.meta, "n_files": len(files), "total_bytes": sum(f["bytes"] for f in files.values())}
    (out / "ARTIFACT_MANIFEST.json").write_text(json.dumps(manifest, indent=1, default=str), encoding="utf-8")
    doc = APP / "docs" / "DEPLOYMENT_MANIFEST.md"
    doc.parent.mkdir(exist_ok=True)
    lines = ["# Deployment manifest — BL ETF Optimizer dashboard (standalone package)\n",
             f"Built {manifest['built']} · tiers included: {', '.join(tiers)} · {len(files)} data files · {manifest['total_bytes'] / 1e6:.1f} MB · "
             f"bundle `artifacts/` · manifest sha256 `{sha256_file(out / 'ARTIFACT_MANIFEST.json')[:16]}…`\n",
             "Classification of every artifact the dashboard can read. SAFE_TO_PUBLISH files are bundled. REQUIRES_LICENSE_REVIEW files are bundled in this package because the user "
             "confirmed that the applicable licence authorizes hosting the historical Bloomberg-derived series in a private GitHub repository and a private Streamlit application "
             "for authorized viewers. EXCLUDE_FROM_DEPLOYMENT files (raw Bloomberg market levels and release-level actual/survey values) are never bundled. Raw Bloomberg workbooks, "
             "the ETF price workbook, ECB files, research folders, model source code, tests of the frozen models and the original dashboards are not part of the package.\n",
             "| key | source | path in the frozen run | classification | included | bundle path | bytes | rationale |", "|---|---|---|---|---|---|---|---|"]
    for r in rows:
        lines.append(f"| `{r['key']}` | {r['source']} | `{r['path']}` | {r['tier']} | {r['included']} | `{r['bundle_path']}` | {r['bytes']:,} | {r['rationale']} |")
    inc = {t: sum(1 for r in rows if r["tier"] == t and r["included"].startswith("yes")) for t in TIER_NAMES.values()}
    tot = {t: sum(1 for r in rows if r["tier"] == t) for t in TIER_NAMES.values()}
    lines.append(f"\nSummary: SAFE_TO_PUBLISH {inc['SAFE_TO_PUBLISH']}/{tot['SAFE_TO_PUBLISH']} bundled · REQUIRES_LICENSE_REVIEW {inc['REQUIRES_LICENSE_REVIEW']}/{tot['REQUIRES_LICENSE_REVIEW']} bundled "
                 f"({sum(1 for r in rows if 'redacted' in r['included'])} as redacted copies) · EXCLUDE_FROM_DEPLOYMENT {inc['EXCLUDE_FROM_DEPLOYMENT']}/{tot['EXCLUDE_FROM_DEPLOYMENT']} bundled.\n")
    lines.append("Frozen runs pinned by the bundle manifest:\n")
    lines.append("| source | label | run id | contract | contract sha256 | manifest sha256 pin | files bundled |")
    lines.append("|---|---|---|---|---|---|---|")
    for name, s in sources.items():
        lines.append(f"| {name} | {s['label']} | `{s['run_id']}` | `{s['contract']}` | `{str(s['contract_sha256'])[:16]}…` | `{str(s['manifest_sha256'])[:16]}…` | {s['n_files']} |")
    lines.append("\nVerification chain preserved in the package: frozen OUTPUT CONTRACT (sha256 recorded above) → run MANIFEST (sha256 pin recorded above) → FILE HASH "
                 "(`sha256_original` = the manifest's pin, `sha256_bundle` = the bundled copy; identical for every unredacted file) → DATA LOADER (`bldash/core/store.py` "
                 "re-hashes every file before parsing it and refuses any mismatch).\n")
    doc.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"bundle: {len(files)} files, {manifest['total_bytes'] / 1e6:.1f} MB -> {out}; ARTIFACT_MANIFEST.json and {doc.relative_to(APP)} written")
    return 0


if __name__ == "__main__":
    sys.exit(main())
