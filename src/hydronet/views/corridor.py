"""Amstel corridor logic: selection by buffer, chainage ordering, sensitivity, proximity links.

Distances are in metres in EPSG:28992 (RD New). Chainage is measured from the
upstream start of the centreline (Amstelhoek). Ordering is indicative only.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence

import geopandas as gpd
import pandas as pd
from shapely.geometry import LineString, Point


def corridor_stations(amstel_stations: pd.DataFrame, buffer_m: float,
                      chainage_range_m: tuple[float, float] | None = None,
                      overrides: pd.DataFrame | None = None) -> pd.DataFrame:
    """Stations within ``buffer_m`` of the centreline, ordered upstream -> downstream.

    ``overrides`` (columns ``station_id, action, reason``) is applied after the
    distance rule: ``exclude`` removes a station, ``include`` keeps it regardless
    of distance (only stations present in ``amstel_stations`` can be included).
    """
    df = amstel_stations
    keep = df["distance_to_river_m"] <= buffer_m
    if overrides is not None and not overrides.empty:
        inc = set(overrides.loc[overrides["action"] == "include", "station_id"])
        exc = set(overrides.loc[overrides["action"] == "exclude", "station_id"])
        keep = (keep | df["station_id"].isin(inc)) & ~df["station_id"].isin(exc)
    out = df[keep]
    if chainage_range_m is not None:
        lo, hi = chainage_range_m
        out = out[(out["chainage_m"] >= lo) & (out["chainage_m"] <= hi)]
    return order_by_chainage(out)


def order_by_chainage(df: pd.DataFrame) -> pd.DataFrame:
    """Stable upstream -> downstream ordering; ties broken by station_id."""
    return df.sort_values(["chainage_m", "station_id"], kind="mergesort", ignore_index=True)


def buffer_sensitivity(amstel_stations: pd.DataFrame, buffers_m: Sequence[float]) -> pd.DataFrame:
    """Station counts per buffer, and which stations enter relative to the next-smaller buffer.

    Returns columns ``buffer_m, n_stations, n_chem, n_bio, entering`` (list of IDs).
    Counts are monotone non-decreasing in the buffer.
    """
    rows, previous = [], set()
    for b in sorted(buffers_m):
        sel = amstel_stations[amstel_stations["distance_to_river_m"] <= b]
        ids = set(sel["station_id"])
        rows.append({
            "buffer_m": b,
            "n_stations": len(ids),
            "n_chem": int(sel["is_chem"].sum()) if "is_chem" in sel else None,
            "n_bio": int(sel["is_bio"].sum()) if "is_bio" in sel else None,
            "entering": sorted(ids - previous),
        })
        previous = ids
    return pd.DataFrame(rows)


def locate_on_line(line: LineString, points: gpd.GeoSeries) -> pd.DataFrame:
    """Distance to the line and chainage (projection) for each point, in the line's CRS units."""
    return pd.DataFrame({
        "distance_to_river_m": points.distance(line).to_numpy(),
        "chainage_m": [line.project(p) for p in points],
    }, index=points.index)


def proximity_links(sources: gpd.GeoDataFrame, targets: gpd.GeoDataFrame, buffer_m: float,
                    source_id: str = "installation", target_id: str = "station_id") -> pd.DataFrame:
    """All (source, target) pairs closer than ``buffer_m``, with distance, nearest first.

    Sources without geometry are skipped. Both frames must share a metric CRS.
    """
    src = sources[sources.geometry.notna() & ~sources.geometry.is_empty]
    rows = []
    for sid, sgeom in zip(src[source_id], src.geometry):
        d = targets.distance(sgeom)
        near = targets.loc[d <= buffer_m, target_id]
        rows += [{source_id: sid, target_id: tid, "distance_m": float(d.loc[i])}
                 for i, tid in near.items()]
    out = pd.DataFrame(rows, columns=[source_id, target_id, "distance_m"])
    return out.sort_values([source_id, "distance_m"], ignore_index=True)


def nearest(points: gpd.GeoDataFrame, target: Point, id_col: str, k: int = 1) -> pd.DataFrame:
    """The ``k`` points nearest to ``target``, with distance."""
    d = points.distance(target)
    idx = d.nsmallest(k).index
    return pd.DataFrame({id_col: points.loc[idx, id_col].to_numpy(), "distance_m": d.loc[idx].to_numpy()})


def near_chainage(corridor_df: pd.DataFrame, chainage_m: float, window_m: float) -> pd.DataFrame:
    """Corridor stations within ``window_m`` along the river of ``chainage_m``, with signed offset.

    ``offset_m`` > 0 means downstream of the reference point (indicative).
    """
    d = corridor_df.assign(offset_m=corridor_df["chainage_m"] - chainage_m)
    return order_by_chainage(d[d["offset_m"].abs() <= window_m])


def chainage_extent(df: pd.DataFrame, ids: Iterable[str]) -> tuple[float, float] | None:
    """Min/max chainage of the given stations (None if none)."""
    sel = df[df["station_id"].isin(set(ids))]["chainage_m"]
    return None if sel.empty else (float(sel.min()), float(sel.max()))
