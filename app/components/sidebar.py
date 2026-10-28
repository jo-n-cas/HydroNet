"""Global controls (sidebar) and the per-run context shared by all pages."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import pandas as pd
import streamlit as st

from hydronet.groups import OTHER, group_label
from hydronet.views import corridor as corridor_views

from .data import Bundle, groups, settings


@dataclass
class Context:
    """Data plus the user's current analysis choices, after applying them."""

    bundle: Bundle
    group: str
    parameter: str | None
    buffer_m: int
    stretch_m: tuple[float, float]
    source: str
    date_range: tuple[date, date]
    quality_codes: list[int]
    show_context: bool
    corridor_all: pd.DataFrame        # corridor stations at the chosen buffer (whole river)
    corridor: pd.DataFrame            # ... and within the chosen stretch
    river_length_m: float

    @property
    def corridor_ids(self) -> set[str]:
        return set(self.corridor["station_id"])

    @property
    def amstel_ids_all_buffers(self) -> set[str]:
        a = self.bundle.get("amstel_stations.parquet")
        return set() if a is None else set(a["station_id"])

    def coverage(self) -> pd.DataFrame | None:
        """Coverage filtered by the station-source control."""
        cov = self.bundle.get("coverage.parquet")
        if cov is None or self.source == "both":
            return cov
        return cov[cov["source"] == self.source]

    def bio_values(self) -> pd.DataFrame | None:
        """Raw biology filtered by date range and quality codes."""
        bio = self.bundle.get("bio_values.parquet")
        if bio is None:
            return None
        d = pd.to_datetime(bio["datetime"]).dt.date
        m = (d >= self.date_range[0]) & (d <= self.date_range[1])
        m &= bio["quality_code"].isin(self.quality_codes) | bio["quality_code"].isna()
        return bio[m]


GROUP_HELP = "Groups from instructions §1.1. Tier 1 (nutrients, led by phosphorus) is the approved focus."


def build(bundle: Bundle) -> Context:
    """Render the sidebar and return the context. Every control has a one-line help text."""
    cfg, grp = settings(), groups()
    ss = st.session_state
    sb = st.sidebar
    sb.markdown("### Analysis settings")

    source = sb.radio("Station source", ["both", "chem", "bio"], horizontal=True, key="source",
                      format_func={"both": "both", "chem": "chemistry", "bio": "biology"}.get,
                      help="Which location inventory to show: chemistry (FYCHEM), biology (HB) or both.")

    group_keys = list(grp) + [OTHER]
    default_group = cfg["ui"]["default_parameter_group"]
    if "group" not in ss:
        ss.group = default_group
    group = sb.selectbox("Parameter group", group_keys, key="group", format_func=lambda k: group_label(k, grp),
                         help=GROUP_HELP)
    ss.group_label = group_label(group, grp)

    cov = bundle.get("coverage.parquet")
    params = [] if cov is None else sorted(cov.loc[cov["parameter_group"] == group, "parameter"].unique())
    options = ["(all in group)"] + params
    if ss.get("_param_group") != group:          # reset the parameter when the group changes
        default_p = cfg["ui"]["default_parameter"]
        ss.parameter_choice = default_p if default_p in params else options[0]
        ss._param_group = group
    choice = sb.selectbox("Parameter", options, key="parameter_choice",
                          help="A single parameter within the group, or all of them together.")
    parameter = None if choice == options[0] else choice
    ss.parameter = parameter

    buffers = cfg["amstel"]["ui_buffer_options_m"]
    if "buffer_m" not in ss:
        ss.buffer_m = cfg["amstel"]["ui_default_buffer_m"]
    buffer_m = sb.select_slider("Amstel buffer (m)", buffers, key="buffer_m",
                                help="Distance from the river centreline. 100 m is the pipeline rule; "
                                     "25 / 50 m show how sensitive results are to that choice.")

    length = bundle.line_rd.length if bundle.line_rd is not None else 22000.0
    km_max = round(length / 1000, 1)
    if "stretch_km" not in ss:
        ss.stretch_km = (0.0, km_max)
    stretch = sb.slider("River stretch (km from Amstelhoek)", 0.0, km_max, key="stretch_km", step=0.1,
                        help="Select a stretch of the Amstel; km 0 = Amstelhoek (upstream), "
                             f"km {km_max} = Binnen-Amstel (downstream). Drives map, strip and corridor views.")

    lo, hi = _date_bounds(bundle)
    if "date_range" not in ss:
        ss.date_range = (lo, hi)
    date_range = sb.slider("Date range", lo, hi, key="date_range", format="YYYY",
                           help="Filters biology, hydrology and RWZI series. Coverage counts have no dates.")

    bio = bundle.get("bio_values.parquet")
    codes = [] if bio is None else sorted(int(c) for c in bio["quality_code"].dropna().unique())
    if "quality_codes" not in ss:
        ss.quality_codes = codes
    quality = sb.multiselect("Biology quality codes", codes, key="quality_codes",
                             help="kwaliteitsoordeelcode 0 / 3 / 9. Code meanings are not confirmed, "
                                  "so nothing is hidden by default; deselect to filter.")

    show_context = sb.toggle("Show stations outside the corridor", value=False, key="show_context",
                             help="Context only: tiny grey dots, no counts.")

    a = bundle.get("amstel_stations.parquet")
    if a is None:
        corridor_all = corridor = pd.DataFrame(columns=["station_id", "is_chem", "is_bio",
                                                         "distance_to_river_m", "chainage_m", "beyond_river_end"])
    else:
        corridor_all = corridor_views.corridor_stations(a, buffer_m, overrides=bundle.overrides)
        corridor = corridor_views.corridor_stations(a, buffer_m, (stretch[0] * 1000, stretch[1] * 1000),
                                                    overrides=bundle.overrides)
        if source != "both":
            flag = "is_chem" if source == "chem" else "is_bio"
            corridor_all, corridor = corridor_all[corridor_all[flag]], corridor[corridor[flag]]

    ss.data_label = ("SYNTHETIC fixtures" if bundle.synthetic else "processed") + (
        f" (run {bundle.manifest['run_at'][:10]})" if bundle.manifest and bundle.manifest.get("run_at") else "")
    sb.markdown("---")
    sb.caption(f"Data: `{settings()['ui']['data_dir']}` · {ss.data_label}")
    if ss.get("selected_station"):
        sb.caption(f"Selected station: **{ss.selected_station}**")
        if sb.button("Clear selection", help="Deselect the station highlighted across views."):
            ss.selected_station = None
            st.rerun()

    return Context(bundle, group, parameter, buffer_m, (stretch[0] * 1000, stretch[1] * 1000), source,
                   date_range, quality, show_context, corridor_all, corridor, length)


def _date_bounds(bundle: Bundle) -> tuple[date, date]:
    dates = []
    for name, col in [("bio_values.parquet", "datetime"), ("hydrology.parquet", "date"),
                      ("rwzi_effluent.parquet", "date")]:
        df = bundle.get(name)
        if df is not None and not df.empty:
            d = pd.to_datetime(df[col])
            dates += [d.min(), d.max()]
    if not dates:
        return date(1990, 1, 1), date.today()
    return min(dates).date(), max(dates).date()
