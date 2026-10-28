"""Rebuild all processed outputs from the raw inputs.

    python -m hydronet.pipeline            (from repo root, with src/ on PYTHONPATH)
    python -m hydronet.pipeline --skip-rwzi  (re-use the cached RWZI extract; skip the 3.4 GB scan)

Writes data/processed/*.parquet (contract: hydronet.schemas), rejected_values.parquet and
pipeline_manifest.json. Raw files are never modified.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import time
from datetime import datetime
from pathlib import Path

import pandas as pd

from . import amstel, cleaning, hydrology, io, pressures, stations
from .config import load_settings, repo_path
from .schemas import SCHEMAS, missing_columns

log = logging.getLogger("hydronet.pipeline")


def _sha256(path: Path, limit: int = 50_000_000) -> str:
    """Hash of the file (first 50 MB for very large files, noted in the manifest)."""
    h = hashlib.sha256()
    with path.open("rb") as fh:
        h.update(fh.read(limit))
    return h.hexdigest()


def _write(df: pd.DataFrame, name: str, out: Path, manifest: dict, rows_in: int | None = None,
           rejected: pd.DataFrame | None = None) -> None:
    miss = missing_columns(name, df)
    if miss:
        raise ValueError(f"{name} violates the contract, missing: {miss}")
    df.to_parquet(out / name, index=False)
    info = {"rows_out": int(len(df))}
    if rows_in is not None:
        info["rows_in"] = int(rows_in)
    if rejected is not None and len(rejected):
        info["rejected"] = {str(k): int(v) for k, v in rejected["reason"].value_counts().items()}
    manifest["outputs"][name] = info
    log.info("%-26s %8d rows", name, len(df))


def run(skip_rwzi_scan: bool = False) -> dict:
    t0 = time.time()
    s = load_settings()
    out = repo_path(s["paths"]["processed_dir"])
    out.mkdir(parents=True, exist_ok=True)
    manifest = {"synthetic": False, "run_at": datetime.now().isoformat(timespec="seconds"),
                "generator": "python -m hydronet.pipeline", "inputs": {}, "outputs": {}, "checks": {}}
    for key in s["paths"]["raw_files"]:
        p = io.raw_path(key)
        manifest["inputs"][key] = {"path": str(p.relative_to(repo_path("."))), "bytes": p.stat().st_size,
                                   "sha256_first_50MB" if p.stat().st_size > 50_000_000 else "sha256": _sha256(p)}
    rejected_all = []

    # dictionary, inventories, coverage, stations
    dictionary = io.read_dictionary()
    inv = {"chem": io.read_location_inventory("fychem_locations"), "bio": io.read_location_inventory("hb_locations")}
    cov, cov_issues = stations.build_coverage(inv, dictionary)
    _write(cov, "coverage.parquet", out, manifest)
    hb = io.read_hb_sample()
    st = stations.build_stations(inv, cov, hb)
    st.to_parquet(out / "stations.parquet")
    manifest["outputs"]["stations.parquet"] = {"rows_out": int(len(st))}
    manifest["checks"]["inventory_count_mismatches"] = len(cov_issues)
    manifest["checks"]["not_in_dictionary_codes"] = int(cov.loc[cov["NAME"] == "NOT FOUND", "parameter"].nunique())

    # Amstel corridor
    line = amstel.load_centreline()
    a = amstel.select_amstel_stations(st, line, s["amstel"]["max_distance_m"], s["amstel"]["end_tolerance_m"])
    _write(a, "amstel_stations.parquet", out, manifest)
    manifest["checks"]["amstel_locations"] = {"n": int(len(a)), "chem": int(a["is_chem"].sum()),
                                              "bio": int(a["is_bio"].sum()),
                                              "raw_bio": sorted(set(a["station_id"]) & set(st.loc[st["has_raw_bio"], "station_id"]))}

    # biology
    bio, bio_rej = cleaning.clean_bio(hb, dictionary, s["cleaning"]["sentinel_values"])
    _write(bio, "bio_values.parquet", out, manifest, rows_in=len(hb), rejected=bio_rej)
    rejected_all.append(bio_rej)

    # hydrology
    k = s["cleaning"]["hydrology_outlier_robust_sd"]
    parts, rej_h = [], []
    for key, site in [("hydrology_amstelsluizen", "Amstelsluizen"), ("hydrology_berlagebrug", "Berlagebrug")]:
        d, r = hydrology.tidy_sensor_file(io.read_hydrology(key), site, k,
                                          s["cleaning"].get("hydrology_suspect_values"))
        parts.append(d)
        rej_h.append(r)
    hyd = pd.concat(parts, ignore_index=True)
    rej_h = pd.concat([r for r in rej_h if len(r)], ignore_index=True) if any(len(r) for r in rej_h) else \
        pd.DataFrame(columns=SCHEMAS["rejected_values.parquet"])
    _write(hyd, "hydrology.parquet", out, manifest, rows_in=len(hyd) + len(rej_h), rejected=rej_h)
    manifest["checks"]["hydrology_flagged"] = {str(k_): int(v) for k_, v in hyd["qa_flag"].value_counts().items()}
    rejected_all.append(rej_h)

    # RWZI effluent
    interim = repo_path(s["paths"]["interim_dir"]) / "rwzi_values_nl11.parquet"
    if skip_rwzi_scan and not interim.exists():
        raise FileNotFoundError(f"--skip-rwzi needs {interim}; run once without it")
    vals = pressures.extract_agv_values(s["pressures"]["agv_installation_prefix"], interim, force=False)
    eff, rej_e = pressures.build_effluent(vals, io.read_rwzi_table("rwzi_measurement_points"),
                                          io.read_rwzi_table("rwzi_installations"))
    _write(eff, "rwzi_effluent.parquet", out, manifest, rows_in=len(eff) + len(rej_e), rejected=rej_e)
    manifest["checks"]["rwzi_agv_rows"] = int(len(vals))
    rejected_all.append(rej_e)

    rej = pd.concat([r for r in rejected_all + [pd.DataFrame(cov_issues)] if len(r)], ignore_index=True) \
        if any(len(r) for r in rejected_all + [pd.DataFrame(cov_issues)]) \
        else pd.DataFrame(columns=SCHEMAS["rejected_values.parquet"])
    rej = rej.astype({"value": "float64"}, errors="ignore")
    _write(rej[SCHEMAS["rejected_values.parquet"]], "rejected_values.parquet", out, manifest)

    manifest["duration_s"] = round(time.time() - t0, 1)
    (out / "pipeline_manifest.json").write_text(json.dumps(manifest, indent=2, default=str))
    log.info("done in %.0f s -> %s", manifest["duration_s"], out)
    return manifest


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--skip-rwzi", action="store_true", help="require and re-use the cached RWZI extract")
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s", datefmt="%H:%M:%S")
    run(skip_rwzi_scan=a.skip_rwzi)


if __name__ == "__main__":
    main()
