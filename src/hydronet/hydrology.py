"""Amstel water level and Q series (instructions 5.6). Outliers are flagged, never removed."""

from __future__ import annotations

import numpy as np
import pandas as pd

QUANTITY = {"WATHTE.mNAP.dag.gem": "level_mNAP", "Q.m3.dag": "Q_m3_per_day"}


def robust_outliers(values: pd.Series, k: float) -> pd.Series:
    """True where |x - median| > k * 1.4826 * MAD (robust SD)."""
    med = values.median()
    mad = (values - med).abs().median() * 1.4826
    if not np.isfinite(mad) or mad == 0:
        return pd.Series(False, index=values.index)
    return (values - med).abs() > k * mad


def tidy_sensor_file(raw: pd.DataFrame, site: str, k: float,
                     suspect: dict[str, dict[float, str]] | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Long table ``sensor_id, site, date, quantity, value, qa_flag`` and rejected rows.

    ``suspect`` maps quantity -> {exact value: flag name}; those flags take precedence over
    the robust-outlier flag. All values are kept.
    """
    time_col, *sensors = raw.columns
    dates = pd.to_datetime(raw[time_col], format="%d-%m-%Y %H:%M", errors="coerce").dt.normalize()
    out, rejected = [], []
    for sid in sensors:
        q = QUANTITY.get(raw.attrs["labels"].get(sid, ""), raw.attrs["labels"].get(sid, sid))
        v = pd.to_numeric(raw[sid].str.replace(",", ".", regex=False), errors="coerce")
        bad = dates.isna() | v.isna()
        for i in raw.index[bad]:
            rejected.append({"source_file": f"{site}_hydrology", "station_id": None, "parameter": q,
                             "value": v.loc[i], "reason": "unparseable_date" if pd.isna(dates.loc[i])
                             else "unparseable_value"})
        d = pd.DataFrame({"sensor_id": sid, "site": site, "date": dates[~bad], "quantity": q, "value": v[~bad]})
        codes = {float(v): f for v, f in (suspect or {}).get(q, {}).items()}
        is_code = d["value"].isin(list(codes))
        # robust statistics are computed without the code values, so they do not distort the scale
        out_ = pd.Series(False, index=d.index)
        out_[~is_code] = robust_outliers(d.loc[~is_code, "value"], k)
        d["qa_flag"] = np.where(is_code, d["value"].map(codes), np.where(out_, "outlier_robust", None))
        out.append(d)
    return pd.concat(out, ignore_index=True), pd.DataFrame(rejected)
