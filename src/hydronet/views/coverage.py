"""Coverage aggregations: how many observations exist, where, per parameter group.

Input is ``coverage.parquet`` with a ``parameter_group`` column added by
:func:`hydronet.groups.add_group_column`.
"""

from __future__ import annotations

from collections.abc import Iterable

import pandas as pd


def by_group(coverage: pd.DataFrame, station_ids: Iterable[str] | None = None) -> pd.DataFrame:
    """Observations, locations and distinct parameters per group, for the given stations.

    Returns columns ``parameter_group, n_observations, n_locations, n_parameters``,
    sorted by observations (descending).
    """
    cov = coverage if station_ids is None else coverage[coverage["station_id"].isin(set(station_ids))]
    if cov.empty:
        return pd.DataFrame(columns=["parameter_group", "n_observations", "n_locations", "n_parameters"])
    out = (
        cov.groupby("parameter_group")
        .agg(n_observations=("n_observations", "sum"),
             n_locations=("station_id", "nunique"),
             n_parameters=("parameter", "nunique"))
        .reset_index()
        .sort_values(["n_observations", "parameter_group"], ascending=[False, True], ignore_index=True)
    )
    return out


def per_station(coverage: pd.DataFrame, group: str | None = None,
                parameter: str | None = None) -> pd.Series:
    """Observation count per station for a group and/or a single parameter (0 if absent)."""
    cov = coverage
    if group is not None:
        cov = cov[cov["parameter_group"] == group]
    if parameter is not None:
        cov = cov[cov["parameter"] == parameter]
    return cov.groupby("station_id")["n_observations"].sum()


def station_table(coverage: pd.DataFrame, station_id: str) -> pd.DataFrame:
    """Coverage rows of one station, grouped and sorted for the station detail table."""
    cov = coverage[coverage["station_id"] == station_id]
    cols = ["parameter_group", "parameter", "NAME", "UNIT", "source", "n_observations"]
    cols = [c for c in cols if c in cov.columns]
    return cov[cols].sort_values(["parameter_group", "n_observations"], ascending=[True, False],
                                 ignore_index=True)


def totals(coverage: pd.DataFrame, station_ids: Iterable[str] | None = None) -> dict[str, int]:
    """Headline counts: observations, locations, parameters (overall and per source)."""
    cov = coverage if station_ids is None else coverage[coverage["station_id"].isin(set(station_ids))]
    out = {
        "n_observations": int(cov["n_observations"].sum()),
        "n_locations": int(cov["station_id"].nunique()),
        "n_parameters": int(cov["parameter"].nunique()),
    }
    for src in ("chem", "bio"):
        part = cov[cov["source"] == src]
        out[f"n_observations_{src}"] = int(part["n_observations"].sum())
        out[f"n_locations_{src}"] = int(part["station_id"].nunique())
    return out
