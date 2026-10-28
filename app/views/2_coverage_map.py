import pandas as pd
import streamlit as st
from streamlit_folium import st_folium

from components import captions, charts, data, map_view
from components.provenance import about_view, empty_state
from hydronet.groups import group_label
from hydronet.views import coverage

ctx = st.session_state["ctx"]
b, grp, cfg = ctx.bundle, data.groups(), data.settings()

st.title("Coverage map")
st.markdown("Monitoring locations within the Amstel corridor, sized and coloured by concentration of observation "
            "exist for the selected parameter group or parameter. The main goal is to use this map to identify where does it makes sense to make regular measurements and what kind of measurements are needed." \
            "Click a location to inspect it.")

cov = ctx.coverage()
if cov is None or b.get("stations.parquet") is None or b.get("amstel_stations.parquet") is None:
    empty_state("; ".join(v for k, v in b.problems.items() if k.endswith(".parquet")) or "data missing",
                "`stations.parquet`, `coverage.parquet` and `amstel_stations.parquet` from the pipeline.")
    st.stop()
if b.line_rd is None:
    empty_state(b.problems["amstel_centreline"], "the OSM Amstel centreline (data/external).")

counts = coverage.per_station(cov, group=None if ctx.parameter else ctx.group, parameter=ctx.parameter)
what = ctx.parameter or group_label(ctx.group, grp)

left, right = st.columns([3, 2], gap="large")
with left:
    fmap = map_view.build_map(ctx, counts, st.session_state.get("selected_station"), cfg)
    out = st_folium(fmap, height=560, use_container_width=True, key="coverage_map",
                    returned_objects=["last_object_clicked_tooltip"])
    clicked = map_view.station_id_from_tooltip((out or {}).get("last_object_clicked_tooltip"))
    if clicked and clicked != st.session_state.get("_last_map_click"):
        st.session_state["_last_map_click"] = clicked
        st.session_state["selected_station"] = clicked
        st.rerun()
    st.markdown(map_view.legend_html(), unsafe_allow_html=True)
    sel_counts = counts.reindex(ctx.corridor["station_id"]).fillna(0)
    captions.n_line(int(sel_counts.sum()), int((sel_counts > 0).sum()),
                    extra=f"of {len(ctx.corridor)} corridor locations in the stretch measure: {what}")
    captions.figure_caption(
        f"Map of the Amstel from Amstelhoek (south) to Amsterdam (north). Each corridor location is a marker; "
        f"size and colour show the number of observations of {what}. Grey = none. Locations outside the "
        "selected stretch are faded.")
    captions.tagged("Counts per location from the inventories.", "observed")
    captions.tagged("RWZI markers show plant locations, not verified discharge points; "
                    "sensor positions are assumed at their structures.", "assumed")
    captions.settings_caption(["group", "parameter", "buffer", "stretch", "source", "data"])

with right:
    st.markdown("### Coverage per parameter group in the selected stretch")
    strip = coverage.by_group(cov, ctx.corridor["station_id"])
    if strip.empty:
        empty_state("no corridor locations in the selected stretch at this buffer.",
                    "widening the stretch or the buffer in the sidebar.")
    else:
        labels = {k: group_label(k, grp).split(" · ")[-1] for k in strip["parameter_group"]}
        st.plotly_chart(charts.dot_strip(strip, labels, highlight=ctx.group), width="stretch",
                        config={"displayModeBar": False})
        captions.figure_caption("Rank-ordered dots: observations per parameter group (log scale) at corridor "
                                "locations in the selected stretch; labels give the number of locations. "
                                "The selected group is highlighted.")
        captions.n_line(int(strip["n_observations"].sum()), len(ctx.corridor),
                        extra="km {:.1f}–{:.1f}".format(*[x / 1000 for x in ctx.stretch_m]))
        captions.settings_caption(["buffer", "stretch", "source"])

    sel = st.session_state.get("selected_station")
    st.markdown("### Selected location")
    if not sel:
        st.markdown('<div class="hn-caption">Click a marker on the map to select a location. The selection '
                    'is shared with Station detail and Amstel corridor.</div>', unsafe_allow_html=True)
    else:
        a = b.get("amstel_stations.parquet").set_index("station_id")
        s_info = b.get("stations.parquet").set_index("station_id")
        row = s_info.loc[sel] if sel in s_info.index else None
        st.markdown(f"**{sel}**")
        if row is not None:
            kinds = [k for k, f in [("chemistry", row["is_chem"]), ("biology", row["is_bio"])] if f]
            st.markdown(f"{' + '.join(kinds)} · {int(row['n_chem_obs']):,} chemistry / "
                        f"{int(row['n_bio_obs']):,} biology observations · {int(row['n_parameters'])} parameters"
                        + (" · **raw biology values available**" if row["has_raw_bio"] else ""))
        if sel in a.index:
            captions.tagged(f"km {a.loc[sel, 'chainage_m'] / 1000:.2f} along the river · "
                            f"{a.loc[sel, 'distance_to_river_m']:.0f} m from the centreline", "assumed")
        else:
            st.caption("Outside the 100 m Amstel corridor (context station).")
        st.page_link("views/3_station_detail.py", label="Open station detail →")

table = (ctx.corridor[["station_id", "chainage_m", "distance_to_river_m", "is_chem", "is_bio"]]
         .assign(n_observations_selection=lambda d: d["station_id"].map(counts).fillna(0).astype(int)))
about_view("coverage_map", b,
           sources=["stations.parquet", "coverage.parquet", "amstel_stations.parquet",
                    "data/external/amstel.geojson (OSM)", "config/rwzi_locations.csv (OSM)"],
           steps=["group parameter codes (config/parameter_groups.yaml)", f"select corridor ≤ {ctx.buffer_m} m",
                  "restrict to stretch", "sum observations per location"],
           outputs=["coverage.parquet", "amstel_stations.parquet"], table=table)
