"""Cached loading of processed outputs and reference files. The app never runs the pipeline.

Where data comes from is set by one line in config/settings.yaml: ``ui.data_dir``.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import geopandas as gpd
import pandas as pd
import streamlit as st

from hydronet.config import load_parameter_groups, load_settings, repo_path
from hydronet.groups import add_group_column
from hydronet.schemas import SCHEMAS, missing_columns

FILES = list(SCHEMAS)


@dataclass
class Bundle:
    """Everything the views need, loaded once per data directory."""

    data_dir: Path
    synthetic: bool
    tables: dict[str, pd.DataFrame | None]
    problems: dict[str, str] = field(default_factory=dict)      # file -> why it is unavailable
    manifest: dict[str, Any] | None = None
    line_rd: Any = None                                           # shapely LineString, EPSG:28992
    line_wgs84: Any = None
    rwzi: gpd.GeoDataFrame | None = None                          # EPSG:28992, rows without coords kept
    overrides: pd.DataFrame | None = None

    def get(self, name: str) -> pd.DataFrame | None:
        return self.tables.get(name)


@st.cache_data(show_spinner="Loading processed data …")
def load_bundle(data_dir: str) -> Bundle:
    """Load all processed files from ``data_dir`` (repo-relative) plus reference geometry."""
    settings, groups = load_settings(), load_parameter_groups()
    root = repo_path(data_dir)
    tables: dict[str, pd.DataFrame | None] = {}
    problems: dict[str, str] = {}
    for name in FILES:
        path = root / name
        if not path.exists():
            tables[name], problems[name] = None, f"`{name}` not found in `{data_dir}`"
            continue
        df = gpd.read_parquet(path) if name == "stations.parquet" else pd.read_parquet(path)
        miss = missing_columns(name, df)
        if miss:
            tables[name], problems[name] = None, f"`{name}` lacks contract columns: {', '.join(miss)}"
            continue
        tables[name] = df

    if tables.get("coverage.parquet") is not None:
        tables["coverage.parquet"] = add_group_column(tables["coverage.parquet"], groups)
    if tables.get("bio_values.parquet") is not None:
        bio = tables["bio_values.parquet"].assign(category=None)
        tables["bio_values.parquet"] = add_group_column(bio, groups).drop(columns="category")
    st_ = tables.get("stations.parquet")
    if st_ is not None and st_.crs is not None and st_.crs.to_epsg() != 28992:
        tables["stations.parquet"] = st_.to_crs(28992)

    manifest_path = root / "pipeline_manifest.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else None
    synthetic = bool(manifest and manifest.get("synthetic")) or "fixtures" in str(data_dir)

    line_rd = line_wgs84 = None
    line_path = repo_path(settings["amstel"]["centreline_rd"])
    if line_path.exists():
        g = gpd.read_file(line_path)
        line_rd = g.geometry.iloc[0]
        line_wgs84 = g.to_crs(4326).geometry.iloc[0]
    else:
        problems["amstel_centreline"] = (f"`{settings['amstel']['centreline_rd']}` not found: build it with "
                                         "`scripts/build_amstel_line.py` (see docs/AMSTEL_STATION_SELECTION.md)")

    rwzi = None
    rwzi_path = repo_path(settings["pressures"]["rwzi_locations"])
    if rwzi_path.exists():
        r = pd.read_csv(rwzi_path)
        geom = gpd.points_from_xy(r["x_rd"], r["y_rd"])
        rwzi = gpd.GeoDataFrame(r, geometry=geom, crs="EPSG:28992")
        rwzi.loc[r["x_rd"].isna(), "geometry"] = None
    ov_path = repo_path(settings["amstel"]["overrides"])
    overrides = pd.read_csv(ov_path) if ov_path.exists() else None

    return Bundle(root, synthetic, tables, problems, manifest, line_rd, line_wgs84, rwzi, overrides)


def data_dir() -> str:
    """Data folder for the UI: env ``HYDRONET_DATA_DIR`` (used by tests) overrides ``ui.data_dir``."""
    return os.environ.get("HYDRONET_DATA_DIR") or load_settings()["ui"]["data_dir"]


def settings() -> dict[str, Any]:
    return load_settings()


def groups() -> dict[str, dict[str, Any]]:
    return load_parameter_groups()
