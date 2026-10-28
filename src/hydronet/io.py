"""Locate and load the raw AGV files (never modified). Encodings and formats per docs/DATA_PROFILE notes."""

from __future__ import annotations

import ast
import json
import re
from pathlib import Path

import pandas as pd

from .config import load_settings, repo_path


def raw_path(key: str) -> Path:
    """Path of a raw file: first folder in ``paths.raw_dirs`` that contains it."""
    paths = load_settings()["paths"]
    name = paths["raw_files"][key]
    for d in paths["raw_dirs"]:
        p = repo_path(d) / name
        if p.exists():
            return p
    raise FileNotFoundError(f"{name} not found in any of {paths['raw_dirs']}")


_NP_INT = re.compile(r"np\.int64\((\d+)\)")


def parse_parameter_counts(text: str) -> dict[str, int]:
    """Parse the serialized ``{'code': np.int64(n), ...}`` string safely (no eval)."""
    return {str(k): int(v) for k, v in ast.literal_eval(_NP_INT.sub(r"\1", text)).items()}


def read_location_inventory(key: str) -> pd.DataFrame:
    """One row per location: code, RD coordinates, total and parsed parameter counts."""
    gj = json.loads(raw_path(key).read_text(encoding="utf-8"))
    rows = []
    for f in gj["features"]:
        p = f["properties"]
        rows.append({"station_id": p["locatiecode"], "x_rd": float(p["rd_x_original"]),
                     "y_rd": float(p["rd_y_original"]), "total_observations": int(p["total_observations"]),
                     "parameter_counts": parse_parameter_counts(p["parameter_counts"])})
    return pd.DataFrame(rows)


def read_dictionary() -> pd.DataFrame:
    """Parameter dictionary (Parameter_uitleg.xlsx)."""
    return pd.read_excel(raw_path("parameter_dictionary"))


def read_hb_sample() -> pd.DataFrame:
    """Raw biology export: ';' separated, UTF-8, '.' decimals; all columns read as text."""
    return pd.read_csv(raw_path("hb_sample"), sep=";", dtype=str, encoding="utf-8-sig")


def read_hydrology(key: str) -> pd.DataFrame:
    """Sensor CSV with two header rows (sensor IDs, then labels); dates d-m-yyyy HH:MM (GMT+1)."""
    path = raw_path(key)
    with path.open(encoding="utf-8") as fh:
        ids = fh.readline().strip().split(";")
        labels = fh.readline().strip().split(";")
    df = pd.read_csv(path, sep=";", skiprows=2, header=None, names=ids, dtype=str)
    df.attrs["labels"] = dict(zip(ids, labels))
    return df


def read_rwzi_table(key: str) -> pd.DataFrame:
    """Installations / MeasurementPoints: ',' separated, quoted, latin-1."""
    return pd.read_csv(raw_path(key), encoding="latin-1", dtype=str)


def iter_rwzi_values(chunksize: int = 2_000_000):
    """Stream the 3.4 GB MeasurementValues.csv in chunks (never loaded whole)."""
    cols = ["InstallationCodeOrigin", "MeasurementPointID", "Date", "Value", "Unit"]
    yield from pd.read_csv(raw_path("rwzi_measurement_values"), encoding="latin-1", usecols=cols, dtype=str,
                           chunksize=chunksize)
