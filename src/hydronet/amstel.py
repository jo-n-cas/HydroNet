"""Amstel corridor selection (docs/AMSTEL_STATION_SELECTION.md): every location within 100 m."""

from __future__ import annotations

import geopandas as gpd
import pandas as pd

from .config import load_settings, repo_path
from .views.corridor import locate_on_line, order_by_chainage


def load_centreline():
    """Amstel centreline (EPSG:28992), built by scripts/build_amstel_line.py."""
    path = repo_path(load_settings()["amstel"]["centreline_rd"])
    if not path.exists():
        raise FileNotFoundError(f"{path} missing: run scripts/build_amstel_line.py (see README)")
    return gpd.read_file(path).geometry.iloc[0]


def select_amstel_stations(stations: gpd.GeoDataFrame, line, max_distance_m: float,
                           end_tolerance_m: float) -> pd.DataFrame:
    """``station_id, is_chem, is_bio, distance_to_river_m, chainage_m, beyond_river_end``, upstream first.

    Not pre-filtered below ``max_distance_m``; overrides are applied by the UI and documented separately.
    """
    loc = locate_on_line(line, stations.geometry)
    df = pd.concat([stations[["station_id", "is_chem", "is_bio"]], loc], axis=1)
    df = df[df["distance_to_river_m"] <= max_distance_m].copy()
    df["beyond_river_end"] = (df["chainage_m"] <= end_tolerance_m) | (df["chainage_m"] >= line.length - end_tolerance_m)
    return order_by_chainage(df)
