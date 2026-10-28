"""Dataset time spans and their overlap, for shading shared time axes."""

from __future__ import annotations

from collections.abc import Mapping

import pandas as pd


def spans(dates_by_dataset: Mapping[str, pd.Series]) -> pd.DataFrame:
    """First/last date and number of distinct dates per dataset (empty or all-NaT datasets skipped)."""
    rows = []
    for name, dates in dates_by_dataset.items():
        d = pd.to_datetime(pd.Series(dates), errors="coerce").dropna()
        if d.empty:
            continue
        rows.append({"dataset": name, "start": d.min(), "end": d.max(), "n_dates": d.nunique()})
    return pd.DataFrame(rows, columns=["dataset", "start", "end", "n_dates"])


def overlap(span_table: pd.DataFrame,
            datasets: list[str] | None = None) -> tuple[pd.Timestamp, pd.Timestamp] | None:
    """Common period of the selected datasets: (latest start, earliest end), or None if disjoint.

    Fewer than two datasets is not an overlap, so it also returns None.
    """
    t = span_table if datasets is None else span_table[span_table["dataset"].isin(datasets)]
    if len(t) < 2:
        return None
    start, end = t["start"].max(), t["end"].min()
    return (start, end) if start <= end else None


def clip(df: pd.DataFrame, date_col: str, start, end) -> pd.DataFrame:
    """Rows with ``start <= date <= end`` (either bound may be None)."""
    d = pd.to_datetime(df[date_col])
    m = pd.Series(True, index=df.index)
    if start is not None:
        m &= d >= pd.Timestamp(start)
    if end is not None:
        m &= d <= pd.Timestamp(end)
    return df[m]
