"""RWZI effluent extraction (instructions 5.1 / 5.5): stream, filter to AGV, keep Effluent."""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from . import io

log = logging.getLogger(__name__)


def extract_agv_values(prefix: str, interim: Path, force: bool = False) -> pd.DataFrame:
    """All values of installations starting with ``prefix``; cached in interim (re-used if newer than source)."""
    src = io.raw_path("rwzi_measurement_values")
    if interim.exists() and not force and interim.stat().st_mtime > src.stat().st_mtime:
        log.info("re-using %s", interim)
        return pd.read_parquet(interim)
    parts, n = [], 0
    for chunk in io.iter_rwzi_values():
        n += len(chunk)
        parts.append(chunk[chunk["InstallationCodeOrigin"].str.startswith(prefix, na=False)])
    df = pd.concat(parts, ignore_index=True)
    df.attrs["rows_scanned"] = n
    interim.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(interim, index=False)
    log.info("scanned %d rows, kept %d %s rows", n, len(df), prefix)
    return df


def build_effluent(values: pd.DataFrame, points: pd.DataFrame,
                   installations: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Effluent rows in the contract schema; rows with unparseable date/value go to rejected."""
    mp = points.rename(columns={"MeasurementPointID": "measurement_point"})
    df = values.rename(columns={"InstallationCodeOrigin": "installation", "MeasurementPointID": "measurement_point",
                                "Date": "date", "Value": "value", "Unit": "unit"})
    df = df.merge(mp[["measurement_point", "ProductDescription", "QuantityDescription", "ParameterDescription"]],
                  on="measurement_point", how="left")
    df = df[df["ProductDescription"] == "Effluent"]
    names = dict(zip(installations["Installation"], installations["Installation Description"].str.strip()))
    out = pd.DataFrame({
        "installation": df["installation"], "installation_name": df["installation"].map(names),
        "measurement_point": df["measurement_point"],
        "date": pd.to_datetime(df["date"], format="%Y-%m-%d", errors="coerce"),
        "product": df["ProductDescription"], "quantity": df["QuantityDescription"],
        "parameter": df["ParameterDescription"].str.strip(), "unit": df["unit"],
        "value": pd.to_numeric(df["value"], errors="coerce"),
    })
    bad = out["date"].isna() | out["value"].isna()
    rejected = pd.DataFrame({"source_file": "MeasurementValues.csv", "station_id": out.loc[bad, "installation"],
                             "parameter": out.loc[bad, "measurement_point"], "value": out.loc[bad, "value"],
                             "reason": "unparseable_date_or_value"})
    return out[~bad].reset_index(drop=True), rejected
