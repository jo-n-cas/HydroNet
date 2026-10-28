import pandas as pd
import streamlit as st
from streamlit_folium import st_folium

from components import captions, charts, data, map_view
from components.provenance import about_view, empty_state
from hydronet.groups import group_label
from hydronet.views import corridor as corridor_views
from hydronet.views import coverage, timeaxis

ctx = st.session_state["ctx"]
b, grp, cfg = ctx.bundle, data.groups(), data.settings()

st.title("Coverage map & station detail")
st.markdown("Monitoring locations within the Amstel corridor, sized and coloured by the number of observations "
            "that exist for the selected parameter group or parameter. The main goal is to use this map to identify "
            "where it makes sense to make regular measurements and what kind of measurements are needed. "
            "Click a location to see its details below the map.")

cov = ctx.coverage()
if cov is None or b.get("stations.parquet") is None or b.get("amstel_stations.parquet") is None:
    empty_state("; ".join(v for k, v in b.problems.items() if k.endswith(".parquet")) or "data missing",
                "`stations.parquet`, `coverage.parquet` and `amstel_stations.parquet` from the pipeline.")
    st.stop()
if b.line_rd is None:
    empty_state(b.problems["amstel_centreline"], "the OSM Amstel centreline (data/external).")

counts = coverage.per_station(cov, group=None if ctx.parameter else ctx.group, parameter=ctx.parameter)
what = ctx.parameter or group_label(ctx.group, grp)

with st.container():
    fmap = map_view.build_map(ctx, counts, st.session_state.get("selected_station"), cfg)
    out = st_folium(fmap, height=750, use_container_width=True, key="coverage_map",
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


table = (ctx.corridor[["station_id", "chainage_m", "distance_to_river_m", "is_chem", "is_bio"]]
         .assign(n_observations_selection=lambda d: d["station_id"].map(counts).fillna(0).astype(int)))

# ---------------------------------------------------------------- station detail (follows the map click)
stations = b.get("stations.parquet")
a = b.get("amstel_stations.parquet")
st.divider()
st.header("Station detail")

corridor_ids = list(ctx.corridor_all["station_id"])
others = sorted(set(stations["station_id"]) - set(corridor_ids))
options = corridor_ids + others
sel = st.session_state.get("selected_station")
idx = options.index(sel) if sel in options else None
km = dict(zip(ctx.corridor_all["station_id"], ctx.corridor_all["chainage_m"] / 1000))
choice = st.selectbox("Location", options, index=idx, placeholder="Click a marker on the map or pick a location",
                      format_func=lambda s: f"{s} · km {km[s]:.2f}" if s in km else f"{s} · outside corridor",
                      help="Selecting on the map and here are the same selection. Corridor locations are listed "
                           "upstream → downstream; context locations follow.")
if choice is not None and choice != sel:
    st.session_state["selected_station"] = choice
    st.session_state["_last_map_click"] = choice
sel = choice

detail_table = None
if sel is None:
    st.markdown('<div class="hn-caption">No location selected yet. Click a marker on the map to see what is '
                'measured there.</div>', unsafe_allow_html=True)
else:
    info = stations.set_index("station_id").loc[sel]
    loc = a.set_index("station_id").loc[sel] if a is not None and sel in set(a["station_id"]) else None
    kinds = " + ".join(k for k, f in [("chemistry", info["is_chem"]), ("biology", info["is_bio"])] if f)

    st.markdown(f"## {sel}")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Inventories", kinds)
    c2.metric("Observations", f"{int(info['n_chem_obs'] + info['n_bio_obs']):,}",
              help="Aggregate counts from the location inventories (chemistry + biology).")
    c3.metric("Parameters", int(info["n_parameters"]))
    c4.metric("Raw values in prototype", "yes (biology)" if info["has_raw_bio"] else "no")
    wb = [f"{label} {info[col]}" for label, col in [("KRW water type", "krw_watertype"), ("EAG", "eag"),
                                                    ("waterbody", "krw_waterbody")]
          if pd.notna(info[col]) and str(info[col]) not in ("", "None", "nan")]
    captions.tagged(" · ".join(wb) if wb else "Water body attributes not available for this location "
                    "(they exist only for the raw-biology locations).", "observed")
    if loc is not None:
        captions.tagged(f"km {loc['chainage_m'] / 1000:.2f} along the Amstel (upstream → downstream, indicative) · "
                        f"{loc['distance_to_river_m']:.0f} m from the centreline"
                        + (" · beyond the river end" if loc["beyond_river_end"] else ""), "assumed")
    else:
        captions.tagged("Not within 100 m of the Amstel centreline: context location.", "observed")

    st.markdown("### What is measured here")
    t = coverage.station_table(cov, sel)
    if t.empty:
        empty_state("no coverage rows for this location with the current source filter.",
                    "switching the station source to 'both' in the sidebar.")
    else:
        t = t.assign(group=t["parameter_group"].map(lambda k: group_label(k, grp).split(" · ")[-1]))
        st.dataframe(
            t[["group", "parameter", "NAME", "UNIT", "source", "n_observations"]], hide_index=True, width="stretch",
            height=min(38 * len(t) + 40, 420),
            column_config={
                "NAME": st.column_config.TextColumn("name (dictionary)"),
                "n_observations": st.column_config.ProgressColumn(
                    "observations", format="%d", min_value=0, max_value=int(t["n_observations"].max())),
            })
        captions.n_line(int(t["n_observations"].sum()), 1, extra=f"{t['parameter'].nunique()} parameters")
        captions.figure_caption("Table of parameters measured at this location with the number of observations "
                                "as a bar. Codes without a dictionary entry show an empty name.")
        captions.settings_caption(["source", "data"])
    detail_table = t

    st.markdown("### Raw biology values")
    bio = ctx.bio_values()
    bio_s = None if bio is None else bio[bio["station_id"] == sel]
    if bio_s is None or bio_s.empty:
        n_raw = int(stations["has_raw_bio"].sum())
        reason = (f"this location is not one of the {n_raw} locations with raw biology values in the prototype."
                  if not info["has_raw_bio"] else "no rows match the date range and quality-code filter.")
        empty_state(reason, "the full HB export for this location (or widening the filters).")
        if not info["has_raw_bio"] and a is not None:
            raw = stations[stations["has_raw_bio"]]
            near = corridor_views.nearest(raw, stations.set_index("station_id").geometry.loc[sel], "station_id", k=1)
            if not near.empty and near["station_id"].iloc[0] != sel:
                st.caption(f"Nearest location with raw biology values: **{near['station_id'].iloc[0]}** "
                           f"({near['distance_m'].iloc[0]:,.0f} m away).")
    else:
        eff = b.get("rwzi_effluent.parquet")
        sp = timeaxis.spans({"bio": bio_s["datetime"], "rwzi": None if eff is None else eff["date"]})
        ov = timeaxis.overlap(sp)
        st.plotly_chart(charts.bio_small_multiples(bio_s, x_range=ctx.date_range, overlap=ov), width="stretch",
                        config={"displayModeBar": False})
        captions.figure_caption("One panel per parameter on a shared time axis. Filled dots: quality code 0; faded: "
                                "codes 3/9 (meaning unconfirmed); triangles: reported relative to a limit (> or <); "
                                "orange crosses: QA-flagged values, kept and shown. Grey band: overlap with RWZI data.")
        captions.n_line(len(bio_s), 1, bio_s["datetime"].min(), bio_s["datetime"].max(),
                        extra=f"{bio_s['sample_id'].nunique()} samples · {bio_s['taxon'].nunique()} taxa")
        captions.tagged("Raw values as delivered; no unit conversion or quality filtering beyond your selection.",
                        "observed")
        captions.settings_caption(["dates", "quality codes", "data"])
        detail_table = bio_s

    st.markdown("### Nearby wastewater treatment plants")
    if b.rwzi is None:
        empty_state("no RWZI locations configured.", "`config/rwzi_locations.csv`.")
    else:
        pt = stations.set_index("station_id").geometry.loc[sel]
        r = b.rwzi.copy()
        r["distance_km"] = (r.geometry.distance(pt) / 1000).where(r.geometry.notna())
        r = r.sort_values("distance_km", na_position="last")
        st.dataframe(r[["name", "installation", "distance_km", "location_basis"]].head(6), hide_index=True,
                     width="stretch", column_config={"distance_km": st.column_config.NumberColumn("distance (km)",
                                                                                                  format="%.1f")})
        captions.tagged("Distance from the plant site, not its discharge point (not verified).", "assumed")
        captions.causation_note()

if detail_table is not None:
    about_view("station_detail", b, sources=["stations.parquet", "coverage.parquet", "bio_values.parquet",
                                             "amstel_stations.parquet", "config/rwzi_locations.csv"],
               steps=["filter to location", "group parameters", "filter biology by dates and quality codes"],
               outputs=["coverage.parquet", "bio_values.parquet"], table=detail_table)

about_view("coverage_map", b,
           sources=["stations.parquet", "coverage.parquet", "amstel_stations.parquet",
                    "data/external/amstel.geojson (OSM)", "config/rwzi_locations.csv (OSM)"],
           steps=["group parameter codes (config/parameter_groups.yaml)", f"select corridor ≤ {ctx.buffer_m} m",
                  "restrict to stretch", "sum observations per location"],
           outputs=["coverage.parquet", "amstel_stations.parquet"], table=table)
