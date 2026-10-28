"""RWZI (wastewater treatment plant) effluent summaries and data-availability gaps."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

import pandas as pd

MATCH_COLUMNS = {"quantity": "quantity", "parameter": "parameter", "unit": "unit"}


def classify_metrics(effluent: pd.DataFrame, metrics: Mapping[str, Mapping[str, Any]],
                     exclude_points: Iterable[str] = ()) -> pd.DataFrame:
    """Add a ``metric`` column; rows that match no metric, or excluded points, are dropped.

    A row matches a metric only if quantity, parameter and unit all match its rule.
    """
    df = effluent[~effluent["measurement_point"].isin(set(exclude_points))]
    metric = pd.Series(pd.NA, index=df.index, dtype="object")
    for key, spec in metrics.items():
        m = pd.Series(True, index=df.index)
        for field, col in MATCH_COLUMNS.items():
            if field in spec["match"]:
                m &= df[col] == spec["match"][field]
        metric = metric.mask(m & metric.isna(), key)
    out = df.assign(metric=metric)
    return out[out["metric"].notna()]


def daily(classified: pd.DataFrame) -> pd.DataFrame:
    """One value per plant, metric and day (several measurement points are averaged)."""
    d = classified.assign(date=pd.to_datetime(classified["date"]))
    return (d.groupby(["installation", "metric", "date"], as_index=False)["value"].mean()
            .sort_values(["installation", "metric", "date"], ignore_index=True))


def yearly(classified: pd.DataFrame, metrics: Mapping[str, Mapping[str, Any]]) -> pd.DataFrame:
    """Yearly value per plant and metric using each metric's ``yearly`` rule (sum / median / mean).

    Also returns ``n_days`` so the amount of data behind each value is visible.
    """
    d = daily(classified)
    if d.empty:
        return pd.DataFrame(columns=["installation", "metric", "year", "value", "n_days", "unit"])
    d["year"] = d["date"].dt.year
    parts = []
    for key, spec in metrics.items():
        part = d[d["metric"] == key]
        if part.empty:
            continue
        g = part.groupby(["installation", "year"])["value"]
        agg = g.agg(spec.get("yearly", "median")).rename("value").to_frame()
        agg["n_days"] = g.size()
        agg = agg.reset_index().assign(metric=key, unit=spec.get("yearly_unit", ""))
        parts.append(agg)
    out = pd.concat(parts, ignore_index=True)
    return out[["installation", "metric", "year", "value", "n_days", "unit"]]


def gap_matrix(classified: pd.DataFrame, installations: Iterable[str],
               metrics: Iterable[str]) -> pd.DataFrame:
    """Days with data per plant x metric (0 = not measured); every plant and metric appears."""
    counts = daily(classified).groupby(["installation", "metric"]).size()
    idx = pd.MultiIndex.from_product([list(installations), list(metrics)], names=["installation", "metric"])
    return counts.reindex(idx, fill_value=0).unstack("metric")
