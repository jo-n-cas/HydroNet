"""Data-gaps table: observations in AGV's systems vs values available in the prototype."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

import pandas as pd

STATUS_SPARSE = "too sparse to trace a source"
STATUS_COUNTS_ONLY = "counts only: no values in prototype"
STATUS_PARTIAL = "partial: some raw values"
STATUS_ABSENT = "not measured here"


def gaps_table(coverage: pd.DataFrame, bio_values: pd.DataFrame | None,
               corridor_ids: Iterable[str], groups: Mapping[str, Mapping[str, Any]]) -> pd.DataFrame:
    """Per parameter group: AGV-wide and Amstel observation counts vs raw values in the prototype.

    ``coverage`` and ``bio_values`` must carry ``parameter_group``. Raw values exist
    only for biology (the 50 sampled locations), so chemistry groups have 0 values.
    """
    corridor = set(corridor_ids)
    cov_a = coverage[coverage["station_id"].isin(corridor)]

    def agg(cov: pd.DataFrame, suffix: str) -> pd.DataFrame:
        return cov.groupby("parameter_group").agg(
            **{f"observations_{suffix}": ("n_observations", "sum"),
               f"locations_{suffix}": ("station_id", "nunique")})

    out = agg(coverage, "agv").join(agg(cov_a, "amstel"), how="left")
    if bio_values is not None and not bio_values.empty:
        vals = bio_values.groupby("parameter_group").size().rename("values_in_prototype_agv")
        vals_a = (bio_values[bio_values["station_id"].isin(corridor)]
                  .groupby("parameter_group").size().rename("values_in_prototype_amstel"))
        out = out.join(vals, how="left").join(vals_a, how="left")
    for c in ["observations_amstel", "locations_amstel", "values_in_prototype_agv",
              "values_in_prototype_amstel"]:
        out[c] = out.get(c, pd.Series(dtype=float)).fillna(0).astype(int)
    out["share_with_values_amstel"] = (
        out["values_in_prototype_amstel"] / out["observations_amstel"].where(out["observations_amstel"] > 0)
    )
    out["status"] = [_status(k, r, groups) for k, r in out.iterrows()]
    out["tier"] = [groups.get(k, {}).get("tier") for k in out.index]
    out = out.reset_index()
    return out.sort_values(["tier", "observations_amstel"], ascending=[True, False],
                           na_position="last", ignore_index=True)


def _status(key: str, row: pd.Series, groups: Mapping[str, Mapping[str, Any]]) -> str:
    if row["observations_amstel"] == 0:
        return STATUS_ABSENT
    if groups.get(key, {}).get("sparse"):
        return STATUS_SPARSE
    if row["values_in_prototype_amstel"] > 0:
        return STATUS_PARTIAL
    return STATUS_COUNTS_ONLY
