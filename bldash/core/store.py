"""Hash-verified, read-only access to the deployment bundle (bundle mode) or to the source repository's published artifacts (repository mode).

Standalone package (this folder, Streamlit Community Cloud): the files live under artifacts/ and ARTIFACT_MANIFEST.json carries, for every
key, the original contract pin (sha256 of the file as published by the frozen run) and the sha256 of the bundled copy; for an unredacted
copy the two must be identical, and every file must hash to its pin before it is parsed. Repository mode is used only by tools/build_bundle.py
when the package sits next to the source project (contract -> manifest -> file hashes). Nothing is ever written into a run directory; the
dashboard only reads. Missing optional tables are reported as absent, never fabricated.
"""

from __future__ import annotations

import gzip
import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd

from bldash.core import registry as R

APP_DIR = Path(__file__).resolve().parents[2]          # package root (the folder holding streamlit_app.py)
REPO_ROOT = Path(os.environ.get("BL_DASHBOARD_REPO_ROOT", str(APP_DIR.parent)))   # source project root (repository mode only)
BUNDLE_DIR = Path(os.environ.get("BL_DASHBOARD_BUNDLE", str(APP_DIR / "artifacts")))
BUNDLE_MANIFEST = "ARTIFACT_MANIFEST.json"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


class IntegrityError(RuntimeError):
    pass


class ArtifactsMissing(FileNotFoundError):
    pass


@dataclass
class Resolved:
    key: str
    path: Optional[Path]          # None when absent in this mode
    sha_expected: Optional[str]   # pin the file must hash to (None = unpinned redacted copy pinned by the bundle manifest only)
    source: str
    run_id: str
    tier: str
    redacted: bool = False

    @property
    def present(self) -> bool:
        return self.path is not None and self.path.exists()


def detect_mode() -> str:
    """Standalone package: the bundled artifacts take precedence; the source repository is used only when explicitly requested or when no bundle exists."""
    forced = os.environ.get("BL_DASHBOARD_SOURCE", "auto").lower()
    if forced in ("repo", "bundle"):
        return forced
    if (BUNDLE_DIR / BUNDLE_MANIFEST).exists():
        return "bundle"
    if (REPO_ROOT / R.SOURCES["bl2"]["contract"]).exists():
        return "repo"
    return "none"


class ArtifactStore:
    """Resolves logical keys to verified files. Construct once per process (cached by the app)."""

    def __init__(self, mode: Optional[str] = None):
        self.mode = mode or detect_mode()
        self.contracts: Dict[str, dict] = {}
        self.manifests: Dict[str, dict] = {}
        self.run_dirs: Dict[str, Path] = {}
        self.run_ids: Dict[str, str] = {}
        self.report: Dict[str, object] = {"mode": self.mode, "sources": {}, "ok": False, "problems": []}
        self.bundle: Dict[str, dict] = {}
        if self.mode == "repo":
            self._init_repo()
        elif self.mode == "bundle":
            self._init_bundle()
        else:
            raise ArtifactsMissing("No published artifacts found: the deployment bundle (artifacts/ARTIFACT_MANIFEST.json next to streamlit_app.py) "
                                   "is missing and no source repository contracts (outputs/…) are available.")

    # ----------------------------------------------------------------------------------------------------------------- repository mode
    def _load_json(self, p: Path) -> dict:
        return json.loads(p.read_text(encoding="utf-8"))

    def _init_repo(self) -> None:
        problems: List[str] = []
        for name, spec in R.SOURCES.items():
            if spec.get("contract"):
                cpath = REPO_ROOT / str(spec["contract"])
                if not cpath.exists():
                    problems.append(f"{name}: contract {spec['contract']} not found")
                    continue
                c = self._load_json(cpath)
                self.contracts[name] = c
                run_dir = REPO_ROOT / str(c[str(spec["run_dir_key"])])
                man_pin = str(c[str(spec["manifest_sha_key"])])
                self.run_ids[name] = str(c[str(spec["run_id_key"])])
                self._register_run(name, run_dir, man_pin, cpath, problems, contract_status=str(c.get("status", "")))
        # M0: pinned through the BL 2.0 contract
        if "bl2" in self.contracts:
            c = self.contracts["bl2"]
            m0_id = str(c["m0_run_id"])
            self.run_ids["m0"] = m0_id
            run_dir = REPO_ROOT / str(R.SOURCES["m0"]["run_dir_template"]).format(run_id=m0_id)
            man_pin = str(c["upstream_source_hashes"]["m0_manifest_sha256"])
            self._register_run("m0", run_dir, man_pin, REPO_ROOT / str(R.SOURCES["bl2"]["contract"]), problems, contract_status="PINNED_BY_BL2_CONTRACT")
        # benchmark configuration: pinned by the Phase 7 contract
        if "p7" in self.contracts:
            cfg = REPO_ROOT / str(R.SOURCES["cfg"]["file"])
            pin = str(self.contracts["p7"]["benchmark_config_hash"])
            ok = cfg.exists() and sha256_file(cfg) == pin
            self.report["sources"]["cfg"] = {"label": R.SOURCES["cfg"]["label"], "path": str(R.SOURCES["cfg"]["file"]), "sha256_pin": pin, "ok": bool(ok),
                                             "run_id": "configs/liquid_gmp_2026_v1.yaml"}
            if not ok:
                problems.append("cfg: configs/liquid_gmp_2026_v1.yaml does not hash to the Phase 7 contract pin")
        self.report["problems"] = problems
        self.report["ok"] = not problems and all(s.get("ok") for s in self.report["sources"].values())
        c2 = self.contracts.get("bl2", {})
        c7 = self.contracts.get("p7", {})
        self.meta = {"model_dates": c2.get("model_dates", []), "simulation_window": c2.get("simulation_window", {}), "policy_bl2": c2.get("policy", {}),
                     "policy_bl1": c7.get("transaction_costs", {}), "view_parameters": c2.get("view_parameters", {}), "strategies": c2.get("strategies", {}),
                     "bl2_status": {"status": c2.get("status"), "validation_status": c2.get("validation_status"), "configuration_status": c2.get("configuration_status"),
                                    "checks_passed": c2.get("checks_passed"), "checks_total": c2.get("checks_total"), "not_claims": c2.get("not_claims", [])},
                     "bl1_status": {"status": c7.get("status"), "validation_status": c7.get("validation_status"), "blocking_tests": c7.get("blocking_tests", {}),
                                    "known_limitations": c7.get("known_limitations", [])},
                     "benchmark_weights": c7.get("strategic_benchmark_weights", {}), "canonical_assets": c7.get("canonical_asset_order", []),
                     "evaluation_window": c7.get("evaluation_window", {}), "execution_timing": c7.get("execution_timing", {}),
                     "metric_definitions": c7.get("metric_definitions", {}), "upstream_run_ids": c2.get("upstream_run_ids", {})}
        if not self.report["ok"]:
            raise IntegrityError("artifact verification failed: " + "; ".join(problems[:6]))

    def _register_run(self, name: str, run_dir: Path, man_pin: str, cpath: Path, problems: List[str], contract_status: str) -> None:
        entry = {"label": R.SOURCES[name]["label"], "contract": str(cpath.relative_to(REPO_ROOT)) if cpath.is_relative_to(REPO_ROOT) else str(cpath),
                 "contract_sha256": sha256_file(cpath), "contract_status": contract_status, "run_directory": str(run_dir.relative_to(REPO_ROOT)) if run_dir.exists() else str(run_dir),
                 "manifest_sha256_pin": man_pin, "manifest_ok": False, "files_in_manifest": 0, "ok": False, "run_id": self.run_ids.get(name, "")}
        self.report["sources"][name] = entry
        mpath = run_dir / "manifest.json"
        if not mpath.exists():
            problems.append(f"{name}: run directory {run_dir} has no manifest")
            return
        man_ok = sha256_file(mpath) == man_pin
        entry["manifest_ok"] = man_ok
        if not man_ok:
            problems.append(f"{name}: manifest hash differs from the contract pin")
            return
        man = self._load_json(mpath)
        self.manifests[name] = man
        self.run_dirs[name] = run_dir
        entry["files_in_manifest"] = len(man.get("outputs", {}))
        entry["run_id"] = str(man.get("run_id", self.run_ids.get(name, "")))
        entry["ok"] = True

    # ----------------------------------------------------------------------------------------------------------------- bundle mode
    def _init_bundle(self) -> None:
        mpath = BUNDLE_DIR / BUNDLE_MANIFEST
        man = self._load_json(mpath)
        self.bundle = man
        for name, src in man.get("sources", {}).items():
            self.run_ids[name] = str(src.get("run_id", ""))
            self.report["sources"][name] = {"label": src.get("label", name), "contract": src.get("contract", ""), "contract_sha256": src.get("contract_sha256", ""),
                                            "contract_status": src.get("contract_status", ""), "run_directory": "bundle", "manifest_sha256_pin": src.get("manifest_sha256", ""),
                                            "manifest_ok": True, "files_in_manifest": src.get("n_files", 0), "ok": True, "run_id": src.get("run_id", "")}
        self.report["bundle_manifest_sha256"] = sha256_file(mpath)
        self.report["bundle_built"] = man.get("built", "")
        self.report["bundle_tiers"] = man.get("tiers_included", [])
        self.meta = man.get("meta", {})
        # chain consistency: an unredacted copy must carry exactly the contract pin of the published file; no excluded table may be listed
        problems: List[str] = []
        for key, item in man.get("files", {}).items():
            e = R.ENTRY_BY_KEY.get(key)
            if e is None:
                problems.append(f"{key}: not a registered table")
            elif e.tier == R.EXCLUDE:
                problems.append(f"{key}: EXCLUDE_FROM_DEPLOYMENT table listed in the bundle")
            elif not item.get("redacted") and item.get("sha256_bundle") != item.get("sha256_original"):
                problems.append(f"{key}: bundled copy is not pinned to the published file")
        self.report["problems"] = problems
        self.report["ok"] = not problems
        if problems:
            raise IntegrityError("bundle manifest inconsistent with the registry: " + "; ".join(problems[:6]))

    # ----------------------------------------------------------------------------------------------------------------- resolution
    def resolve(self, key: str) -> Resolved:
        e = R.ENTRY_BY_KEY[key]
        if self.mode == "repo":
            if e.source == "cfg":
                return Resolved(key, REPO_ROOT / e.path, str(self.contracts["p7"]["benchmark_config_hash"]), "cfg", "configs/liquid_gmp_2026_v1.yaml", e.tier)
            run_dir = self.run_dirs.get(e.source)
            man = self.manifests.get(e.source, {})
            pin = man.get("outputs", {}).get(e.path)
            if run_dir is None or pin is None:
                return Resolved(key, None, None, e.source, self.run_ids.get(e.source, ""), e.tier)
            return Resolved(key, run_dir / e.path, str(pin), e.source, self.run_ids.get(e.source, ""), e.tier)
        item = self.bundle.get("files", {}).get(key)
        if item is None:
            return Resolved(key, None, None, e.source, self.run_ids.get(e.source, ""), e.tier)
        return Resolved(key, BUNDLE_DIR / str(item["bundle_path"]), str(item["sha256_bundle"]), e.source, self.run_ids.get(e.source, ""), str(item.get("tier", e.tier)),
                        redacted=bool(item.get("redacted", False)))

    def available(self, key: str) -> bool:
        return self.resolve(key).present

    def missing_required(self) -> List[str]:
        return [e.key for e in R.ENTRIES if e.required and not self.available(e.key)]

    def verify_file(self, key: str) -> bool:
        r = self.resolve(key)
        return bool(r.present and r.sha_expected and sha256_file(r.path) == r.sha_expected)

    def verify_all(self, keys: Optional[List[str]] = None) -> Dict[str, object]:
        keys = keys or [e.key for e in R.ENTRIES]
        checked, mismatched, absent = 0, [], []
        for k in keys:
            r = self.resolve(k)
            if not r.present:
                absent.append(k)
                continue
            checked += 1
            if not (r.sha_expected and sha256_file(r.path) == r.sha_expected):
                mismatched.append(k)
        out = {"checked": checked, "mismatched": mismatched, "absent": absent, "ok": not mismatched}
        self.report["files"] = out
        return out

    # ----------------------------------------------------------------------------------------------------------------- reading
    def read(self, key: str):
        """Verified read of one table: DataFrame (csv), dict (json/yaml). Raises IntegrityError on a hash mismatch, returns None when absent."""
        r = self.resolve(key)
        if not r.present:
            return None
        if not (r.sha_expected and sha256_file(r.path) == r.sha_expected):
            raise IntegrityError(f"{key}: {r.path.name} does not hash to its pin; nothing is displayed for this table")
        return _read_file(str(r.path), r.sha_expected, R.ENTRY_BY_KEY[key].kind, tuple(R.ENTRY_BY_KEY[key].date_cols))

    def fingerprint(self) -> str:
        parts = [self.mode] + [f"{k}:{v.get('contract_sha256', '')}:{v.get('manifest_sha256_pin', '')}" for k, v in sorted(self.report["sources"].items())]
        if self.mode == "bundle":
            parts.append(str(self.report.get("bundle_manifest_sha256", "")))
        return hashlib.sha256("|".join(parts).encode()).hexdigest()[:16]


def _parse_dates(df: pd.DataFrame, extra: tuple) -> pd.DataFrame:
    for c in df.columns:
        if c in R.GENERIC_DATE_COLS or c in extra:
            df[c] = pd.to_datetime(df[c], errors="coerce")
    return df


def _read_file(path_str: str, sha: str, kind: str, date_cols: tuple):
    p = Path(path_str)
    if kind == "csv":
        if p.suffix == ".gz":
            with gzip.open(p, "rt", encoding="utf-8") as fh:
                df = pd.read_csv(fh, float_precision="round_trip")
        else:
            df = pd.read_csv(p, float_precision="round_trip")
        return _parse_dates(df, date_cols)
    if kind == "json":
        return json.loads(p.read_text(encoding="utf-8"))
    if kind == "yaml":
        import yaml
        return yaml.safe_load(p.read_text(encoding="utf-8"))
    raise ValueError(kind)


try:  # Streamlit caching when the module is used inside the app; plain functions elsewhere (tests, tools)
    import streamlit as st

    _read_file = st.cache_data(show_spinner=False)(_read_file)   # type: ignore[assignment]  # keyed by path + pinned sha + kind

    @st.cache_resource(show_spinner="Verifying the published artifacts…")
    def get_store() -> ArtifactStore:
        return ArtifactStore()
except Exception:  # pragma: no cover - streamlit absent
    def get_store() -> ArtifactStore:  # type: ignore[misc]
        return ArtifactStore()
