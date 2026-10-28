"""Explore assumed chemical presence and possible routes along the Amstel."""

from html import escape

import folium
import geopandas as gpd
import pandas as pd
import streamlit as st
from shapely.geometry import Point
from shapely.ops import substring
from streamlit_folium import st_folium

from hydronet.config import repo_path


CHEMICALS = {
    "Cl_mg/l": ("Chloride", "mg/l", 3696, "#2563eb"),
    "NH4_mgN/l_nf": ("Ammonium after filtration", "mg N/l", 3550, "#d97706"),
    "Ptot_mgP/l": ("Total phosphorus", "mg P/l", 3525, "#7c3aed"),
}

st.title("Chemical detection reach")
st.write("Explore selected Amstel chemistry stations and possible downstream routes.")

b = st.session_state["ctx"].bundle
station_path = repo_path("amstel_subset/stations.csv")
coverage_path = repo_path("amstel_subset/coverage.csv")
if b.line_rd is None or not station_path.exists() or not coverage_path.exists():
    st.error("Amstel station subset or centreline is missing. Build the river line and run "
             "`python scripts/amstel_subset.py` (see README).")
    st.stop()

parameter = st.selectbox("Chemical", list(CHEMICALS),
                         format_func=lambda p: f"{CHEMICALS[p][0]} ({p})")
name, _, n_inventory, color = CHEMICALS[parameter]
coverage = pd.read_csv(coverage_path)
all_counts = (coverage.loc[(coverage["source"] == "chem") &
                           coverage["parameter"].isin(CHEMICALS)]
              .pivot_table(index="station_id", columns="parameter", values="n_observations",
                           aggfunc="sum", fill_value=0))
selected = coverage.loc[(coverage["source"] == "chem") &
                        (coverage["parameter"] == parameter) &
                        (coverage["n_observations"] > 0), ["station_id", "n_observations"]]
covered = set(selected["station_id"])
all_stations = pd.read_csv(station_path)
all_stations["chainage_m"] = [b.line_rd.project(Point(x, y)) for x, y in
                             zip(all_stations["rd_x"], all_stations["rd_y"])]
stations = all_stations[all_stations["station_id"].isin(covered) & ~all_stations["beyond_river_end"]].copy()
stations = stations.merge(selected, on="station_id").sort_values(["chainage_m", "station_id"])
st.caption(f"{name}: {len(stations)} of {len(all_stations)} selected locations highlighted; "
           f"{n_inventory:,} inventory observations. "
           "Inventory counts are not concentrations. Station order is positional, not measured flow.")

overview = st.radio("Overview", ["Map 1 · Chemical locations", "Map 2 · Possible entry and downstream route"],
                    horizontal=True)
st.warning("Assumption: a positive observation count means this chemical was found. "
           "The source file does not verify that assumption. No station is known to be negative, "
           "so an entry reach, source, or transport path cannot be identified from these counts.")
all_points = gpd.GeoSeries(gpd.points_from_xy(all_stations["rd_x"], all_stations["rd_y"]),
                           crs=28992).to_crs(4326)
point_by_id = dict(zip(all_stations["station_id"], all_points))
tooltips = {}
for row in all_stations.itertuples():
    found = row.station_id in covered
    counts = all_counts.loc[row.station_id] if row.station_id in all_counts.index else pd.Series(dtype=int)
    tooltip = f"<b>{escape(row.station_id)}</b> · {'assumed detected' if found else 'status unknown'}<br>"
    tooltip += "<br>".join(f"{label}: {int(counts.get(code, 0))} observations"
                             for code, (label, _, _, _) in CHEMICALS.items())
    tooltips[row.station_id] = tooltip
bounds = b.line_wgs84.bounds

if overview.startswith("Map 1"):
    m = folium.Map(tiles="OpenStreetMap", control_scale=True)
    folium.PolyLine([(y, x) for x, y in b.line_wgs84.coords], color="#555", weight=3,
                    tooltip="Amstel centreline; order toward Amsterdam is indicative").add_to(m)
    for row, point in zip(all_stations.itertuples(), all_points):
        found = row.station_id in covered
        folium.CircleMarker((point.y, point.x), radius=6 if found else 3,
                            color=color if found else "#999", fill=True,
                            fill_opacity=0.9 if found else 0.65,
                            tooltip=folium.Tooltip(tooltips[row.station_id])).add_to(m)
    m.fit_bounds([[bounds[1], bounds[0]], [bounds[3], bounds[2]]])
    st_folium(m, height=520, use_container_width=True, returned_objects=[])
    st.caption("Selected chemical: chloride blue, ammonium orange, total phosphorus purple. "
               "A colored marker = assumed detected. Grey = no record for the selected "
               "chemical (unknown, not absent). Hover for all three observation counts. "
               "Later stations along the line are "
               "not evidence that the same pollution event travelled between them. "
               "© OpenStreetMap contributors.")
    st.dataframe(stations.assign(river_km=(stations["chainage_m"] / 1000).round(3))[
        ["station_id", "river_km", "n_observations"]], hide_index=True, width="stretch")
    st.stop()

if overview.startswith("Map 2"):
    st.subheader("Assumed south-to-north flow and possible entries")
    ordered = stations.reset_index(drop=True)
    ordered["previous_station"] = ordered["station_id"].shift()
    ordered["previous_count"] = ordered["n_observations"].shift()
    ordered["previous_m"] = ordered["chainage_m"].shift()
    entries = ordered[ordered["previous_count"].notna() &
                      (ordered["n_observations"] > ordered["previous_count"])].copy()
    entries["count_rise"] = entries["n_observations"] - entries["previous_count"]
    max_count = int(ordered["n_observations"].max())
    tooltip_style = "max-width:220px;white-space:normal;line-height:1.4;font-size:13px"
    route = folium.Map(tiles="OpenStreetMap", control_scale=True)
    route.get_root().header.add_child(folium.Element(
        "<style>.leaflet-tile-pane{filter:grayscale(1) contrast(.8) brightness(1.1);opacity:.6}</style>"))
    route.get_root().html.add_child(folium.Element(
        '<div role="group" aria-label="Map 2 legend" style="position:fixed;top:12px;right:12px;'
        'z-index:1000;width:225px;max-width:50vw;padding:10px 12px;background:rgba(255,255,255,.96);'
        'border:1px solid #777;border-radius:4px;font:12px/1.35 Arial,sans-serif;'
        'color:#222;pointer-events:none">'
        f'<strong style="display:block;margin-bottom:5px">Map legend · {escape(name)}</strong>'
        f'<div><b style="color:{color}">━</b> Route; thicker = more observations</div>'
        f'<div><b style="color:{color}">●</b> Station; larger = more observations</div>'
        '<div>◯ First recorded station</div>'
        '<div>◇ Possible entry reach (count rises)</div>'
        f'<div><b style="color:{color}">┄</b> Possible continuation</div>'
        '<div><b style="color:#777">━</b> River centreline</div>'
        '<div>↑ Assumed flow toward the north</div>'
        '</div>'))
    folium.PolyLine([(y, x) for x, y in b.line_wgs84.coords], color="#777", weight=2,
                    tooltip=folium.Tooltip("<b>Amstel centreline</b><br>Assumed flow: south → north",
                                           style=tooltip_style)).add_to(route)
    for previous, current in zip(ordered.iloc[:-1].itertuples(), ordered.iloc[1:].itertuples()):
        if current.chainage_m <= previous.chainage_m:
            continue
        segment = gpd.GeoSeries([substring(b.line_rd, previous.chainage_m, current.chainage_m)],
                                crs=28992).to_crs(4326).iloc[0]
        strength = (current.n_observations / max_count) ** 0.5
        folium.PolyLine([(y, x) for x, y in segment.coords], color=color,
                        weight=2 + 6 * strength, opacity=0.9,
                        tooltip=folium.Tooltip(
                            f"<b>Assumed route</b><br>{escape(previous.station_id)} → "
                            f"{escape(current.station_id)}<br>Next station: "
                            f"{current.n_observations:,} observations",
                            style=tooltip_style)).add_to(route)
    last_m = float(ordered["chainage_m"].max())
    if last_m < b.line_rd.length:
        segment = gpd.GeoSeries([substring(b.line_rd, last_m, b.line_rd.length)],
                                crs=28992).to_crs(4326).iloc[0]
        folium.PolyLine([(y, x) for x, y in segment.coords], color=color, weight=3,
                        opacity=0.45, dash_array="8, 7",
                        tooltip=folium.Tooltip("<b>Possible continuation north</b><br>"
                                               "No later selected measurement",
                                               style=tooltip_style)).add_to(route)
    for row in ordered.itertuples():
        point = point_by_id[row.station_id]
        strength = (row.n_observations / max_count) ** 0.5
        folium.CircleMarker((point.y, point.x), radius=4 + 5 * strength,
                            color="white", weight=2, fill=True, fill_color=color,
                            fill_opacity=0.95,
                            tooltip=folium.Tooltip(tooltips[row.station_id],
                                                   style=tooltip_style)).add_to(route)
    first = ordered.iloc[0]
    first_point = gpd.GeoSeries([b.line_rd.interpolate(first.chainage_m)], crs=28992).to_crs(4326).iloc[0]
    folium.CircleMarker((first_point.y, first_point.x), radius=11, color="#111", fill=False,
                        tooltip=folium.Tooltip(
                            f"<b>First recorded station</b><br>{escape(first.station_id)}<br>"
                            "Entry may be farther south", style=tooltip_style)).add_to(route)
    for row in entries.itertuples():
        midpoint = gpd.GeoSeries([b.line_rd.interpolate((row.previous_m + row.chainage_m) / 2)],
                                 crs=28992).to_crs(4326).iloc[0]
        folium.RegularPolygonMarker((midpoint.y, midpoint.x), number_of_sides=4,
                                    rotation=45, radius=8, color="#111", fill=True,
                                    fill_color="white", fill_opacity=1,
                                    tooltip=folium.Tooltip(
                                        f"<b>Possible entry reach</b><br>"
                                        f"{escape(row.previous_station)} → {escape(row.station_id)}<br>"
                                        f"Observations: {int(row.previous_count):,} → "
                                        f"{row.n_observations:,}<br>"
                                        "May reflect sampling frequency",
                                        style=tooltip_style)).add_to(route)
    route.fit_bounds([[bounds[1], bounds[0]], [bounds[3], bounds[2]]])
    st_folium(route, height=520, use_container_width=True, returned_objects=[], key="route_scenario")
    st.caption("Observation counts are not concentrations; more sampling may explain a count rise. "
               "Entries and flow are hypotheses: flow can reverse and the 100 m selection may "
               "include adjacent waters. © OpenStreetMap contributors.")
    st.subheader("Candidate entry reaches")
    st.caption(f"First assumed presence: {first.station_id}; entry may be farther south. "
               f"{len(entries)} additional count rises shown between recorded stations.")
    st.dataframe(entries.assign(from_km=(entries["previous_m"] / 1000).round(2),
                                to_km=(entries["chainage_m"] / 1000).round(2))[
        ["previous_station", "station_id", "from_km", "to_km", "previous_count",
         "n_observations", "count_rise"]], hide_index=True, width="stretch")
    st.stop()
