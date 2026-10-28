"""Cleaning of the raw biology sample (instructions 5.1). Nothing is deleted silently."""

from __future__ import annotations

import numpy as np
import pandas as pd

BIO_COLUMNS = ["station_id", "sample_id", "datetime", "parameter", "taxon", "taxon_group", "value", "unit",
               "limit_flag", "quality_code", "qa_flag"]


def dictionary_bounds(dictionary: pd.DataFrame) -> pd.DataFrame:
    """Widest available lower/upper bound per code from H_MIN/Z_MIN and H_MAX/Z_MAX.

    The H/Z distinction is undocumented, so bounds are used only to *flag* values, never to remove them.
    """
    d = dictionary.drop_duplicates("ID").set_index("ID")
    lo = d[["H_MIN", "Z_MIN"]].apply(pd.to_numeric, errors="coerce").min(axis=1)
    hi = d[["H_MAX", "Z_MAX"]].apply(pd.to_numeric, errors="coerce").max(axis=1)
    return pd.DataFrame({"lo": lo, "hi": hi})


def clean_bio(hb: pd.DataFrame, dictionary: pd.DataFrame,
              sentinels: list[float]) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Tidy biology values and rejected rows.

    - sentinel values (e.g. -999) and unparseable values/dates -> rejected with a reason
    - ``limietsymbool`` kept as ``limit_flag``; no value substitution for biology
    - ``kwaliteitsoordeelcode`` kept as ``quality_code`` (meanings unconfirmed; not filtered)
    - outside dictionary bounds -> ``qa_flag = out_of_range`` (kept)
    """
    df = pd.DataFrame({
        "station_id": hb["locatiecode"],
        "sample_id": hb["monsterident"],
        "datetime": pd.to_datetime(hb["datum"], format="%Y-%m-%d %H:%M", errors="coerce"),
        "parameter": hb["fewsparameter"],
        "taxon": hb["biotaxonnaam"],
        "taxon_group": hb["TWN taxontype"],
        "value": pd.to_numeric(hb["meetwaarde"].str.replace(",", ".", regex=False), errors="coerce"),
        "unit": hb["eenheid"],
        "limit_flag": hb["limietsymbool"],
        "quality_code": pd.to_numeric(hb["kwaliteitsoordeelcode"], errors="coerce").astype("Int64"),
    })
    reason = pd.Series(pd.NA, index=df.index, dtype="object")
    reason = reason.mask(df["datetime"].isna(), "unparseable_date")
    reason = reason.mask(reason.isna() & df["value"].isna(), "unparseable_value")
    for s in sentinels:
        reason = reason.mask(reason.isna() & np.isclose(df["value"], s), f"sentinel_{s:g}")

    b = dictionary_bounds(dictionary)
    lo, hi = df["parameter"].map(b["lo"]), df["parameter"].map(b["hi"])
    out = (lo.notna() & (df["value"] < lo)) | (hi.notna() & (df["value"] > hi))
    df["qa_flag"] = np.where(out, "out_of_range", None)

    rejected = pd.DataFrame({"source_file": "HB_sampled50locations.csv", "station_id": df["station_id"],
                             "parameter": df["parameter"], "value": df["value"], "reason": reason})[reason.notna()]
    return df[reason.isna()][BIO_COLUMNS].reset_index(drop=True), rejected.reset_index(drop=True)
