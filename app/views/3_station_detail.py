import geopandas as gpd
import pandas as pd
import streamlit as st

from components import captions, charts, data
from components.provenance import about_view, empty_state
from hydronet.groups import group_label
from hydronet.views import corridor as corridor_views
from hydronet.views import coverage, timeaxis

ctx = st.session_state["ctx"]
b, grp, cfg = ctx.bundle, data.groups(), data.settings()
stations, cov = b.get("stations.parquet"), ctx.coverage()

st.title("Station detail")
if stations is None or cov is None:
    empty_state("station or coverage table missing.", "`stations.parquet` and `coverage.parquet`.")
    st.stop()

# station picker: corridor stations upstream -> downstream, then the rest
a = b.get("amstel_stations.parquet")
corridor_ids = list(ctx.corridor_all["station_id"])
others = sorted(set(stations["station_id"]) - set(corridor_ids))
options = corridor_ids + others
sel = st.session_state.get("selected_station")
idx = options.index(sel) if sel in options else 0
km = dict(zip(ctx.corridor_all["station_id"], ctx.corridor_all["chainage_m"] / 1000))
choice = st.selectbox("Location", options, index=idx,
                      format_func=lambda s: f"{s} · km {km[s]:.2f}" if s in km else f"{s} · outside corridor",
                      help="Corridor locations are listed upstream → downstream; context locations follow.")
if choice != sel:
    st.session_state["selected_station"] = choice
sel = choice

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

# coverage table with bar "sparklines"
st.markdown("## What is measured here")
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

# biology small multiples
st.markdown("## Raw biology values")
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

# nearby RWZIs
st.markdown("## Nearby wastewater treatment plants")
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

about_view("station_detail", b, sources=["stations.parquet", "coverage.parquet", "bio_values.parquet",
                                         "amstel_stations.parquet", "config/rwzi_locations.csv"],
           steps=["filter to location", "group parameters", "filter biology by dates and quality codes"],
           outputs=["coverage.parquet", "bio_values.parquet"],
           table=t if bio_s is None or bio_s.empty else bio_s)
