import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from components import captions, charts, data, theme
from components.provenance import about_view, empty_state
from hydronet.groups import group_label
from hydronet.views import corridor as corridor_views
from hydronet.views import timeaxis

ctx = st.session_state["ctx"]
b, grp, cfg = ctx.bundle, data.groups(), data.settings()

st.title("Amstel corridor")
st.markdown("The Amstel as an ordered, one-dimensional network: monitoring locations by position along the "
            "river, with the wastewater plants and hydrology sensors near it.")
captions.tagged("Position along the river (upstream → downstream, indicative). The Amstel is a managed "
                "system (sluices, pumping); ordering is not measured flow.", "assumed")

a, cov, stations = b.get("amstel_stations.parquet"), ctx.coverage(), b.get("stations.parquet")
if a is None or cov is None or b.line_rd is None:
    empty_state("; ".join(b.problems.values()) or "data missing",
                "`amstel_stations.parquet`, `coverage.parquet` and the Amstel centreline.")
    st.stop()

# nodes: RWZIs (projected onto the river) and sensors
nodes, links = [], []
buf_p = cfg["pressures"]["nearby_station_buffer_m"]
if b.rwzi is not None:
    linked = set(cfg["pressures"]["amstel_linked_rwzi"])
    r = b.rwzi[b.rwzi.geometry.notna()]
    loc = corridor_views.locate_on_line(b.line_rd, r.geometry)
    r = r.join(loc)
    for _, row in r[r["installation"].isin(linked) | (r["distance_to_river_m"] <= buf_p)].iterrows():
        label = row["name"].replace("rwzi ", "")
        nodes.append({"kind": "rwzi", "km": row["chainage_m"] / 1000, "label": label,
                      "hover": f"RWZI {label} · nearest river km {row['chainage_m'] / 1000:.1f} · "
                               f"{row['distance_to_river_m'] / 1000:.1f} km from the river (plant site; "
                               "discharge point not verified)"})
    st_corr = stations[stations["station_id"].isin(ctx.corridor_all["station_id"])]
    pl = corridor_views.proximity_links(r, st_corr, buf_p)
    for _, l in pl.iterrows():
        km = float(r.loc[r["installation"] == l["installation"], "chainage_m"].iloc[0]) / 1000
        links.append({"node_km": km, "station_id": l["station_id"]})
for name, s in cfg["amstel"]["sensors"].items():
    if s.get("chainage_km") is not None:
        nodes.append({"kind": "sensor", "km": s["chainage_km"], "label": name,
                      "hover": f"Hydrology sensor {name} · km {s['chainage_km']} (position assumed at structure)"})
nodes, links = pd.DataFrame(nodes), pd.DataFrame(links, columns=["node_km", "station_id"])

st.markdown("## Coverage along the river")
rows = [(k, group_label(k, grp)) for k in grp]
counts = cov[cov["station_id"].isin(ctx.corridor_all["station_id"])].groupby(
    ["station_id", "parameter_group"], as_index=False)["n_observations"].sum()
fig = charts.corridor_longitudinal(ctx.corridor_all, counts, rows, nodes, links, ctx.river_length_m / 1000,
                                   st.session_state.get("selected_station"),
                                   (ctx.stretch_m[0] / 1000, ctx.stretch_m[1] / 1000))
st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
captions.figure_caption(
    "Top track: wastewater plants (open triangles, at their nearest river position) and hydrology sensors "
    f"(bars); light lines link a plant to corridor locations within {buf_p / 1000:.0f} km of the plant site. "
    "Rows below: one per parameter group; each dot is a corridor location, sized by its number of "
    "observations (open grey = none). The selected location is orange; the selected stretch is shaded.")
captions.n_line(int(counts["n_observations"].sum()), len(ctx.corridor_all),
                extra=f"{len(nodes)} plants/sensors · {len(links)} proximity links")
captions.tagged("Counts per location.", "observed")
captions.tagged(f"Plant positions projected onto the river; links within {buf_p:,} m are an analysis "
                "choice, not hydraulic connections.", "assumed")
captions.causation_note()
captions.settings_caption(["buffer", "stretch", "source", "data"], extra=f"plant link distance={buf_p} m")

st.markdown("## Water level and flow")
hyd = b.get("hydrology.parquet")
if hyd is None:
    empty_state(b.problems.get("hydrology.parquet", "missing"), "`hydrology.parquet` (instructions 5.6).")
else:
    hyd_f = timeaxis.clip(hyd, "date", ctx.date_range[0], ctx.date_range[1])
    sp = timeaxis.spans({s: hyd.loc[hyd["site"] == s, "date"] for s in ["Amstelsluizen", "Berlagebrug"]})
    ov = timeaxis.overlap(sp)
    st.plotly_chart(charts.hydrology_chart(hyd_f, ov, ctx.date_range), width="stretch",
                    config={"displayModeBar": False})
    captions.figure_caption("Daily water level at the two Amstel sensors and daily Q at Berlagebrug, on a "
                            "shared time axis. Orange crosses mark flagged values (kept, not removed). The grey "
                            "band is the period both sensors cover.")
    captions.n_line(len(hyd_f), 2, hyd_f["date"].min(), hyd_f["date"].max(),
                    extra=f"{int(hyd_f['qa_flag'].notna().sum())} flagged")
    captions.tagged("Values as delivered; Q sign convention unknown (mostly negative).", "observed")
    captions.settings_caption(["dates", "data"])

st.markdown("## Buffer sensitivity")
sens = corridor_views.buffer_sensitivity(a, cfg["amstel"]["ui_buffer_options_m"])
c1, c2 = st.columns([3, 2])
with c1:
    show = sens.assign(entering=sens["entering"].map(lambda l: ", ".join(l[:12]) + (" …" if len(l) > 12 else "")))
    st.dataframe(show.rename(columns={"buffer_m": "buffer (m)", "n_stations": "locations", "n_chem": "chemistry",
                                      "n_bio": "biology", "entering": "added vs smaller buffer"}),
                 hide_index=True, width="stretch")
with c2:
    f2 = go.Figure(go.Scatter(x=sens["buffer_m"], y=sens["n_stations"], mode="lines+markers+text",
                              text=sens["n_stations"], textposition="top center",
                              line=dict(color=theme.INK, width=1), marker=dict(size=8, color=theme.INK)))
    f2.add_vline(x=ctx.buffer_m, line=dict(color=theme.ACCENT, width=1, dash="dot"))
    f2.update_layout(height=220, margin=dict(l=50, r=10, t=20, b=40))
    f2.update_xaxes(title="buffer (m)", tickvals=sens["buffer_m"])
    f2.update_yaxes(title="corridor locations", range=[0, float(sens["n_stations"].max()) * 1.25 + 1])
    st.plotly_chart(f2, width="stretch", config={"displayModeBar": False})
captions.figure_caption("How many locations count as 'on the Amstel' at each buffer; the dotted line marks the "
                        "current choice. The pipeline keeps everything within 100 m.")
captions.settings_caption(["buffer", "data"])

about_view("amstel_corridor", b, sources=["amstel_stations.parquet", "coverage.parquet", "hydrology.parquet",
                                          "config/rwzi_locations.csv", "config/settings.yaml (sensors)",
                                          "data/external/amstel_rd.geojson (OSM)"],
           steps=["project locations on the centreline (chainage)", f"select ≤ {ctx.buffer_m} m",
                  "aggregate per group", "project plants and sensors on the river"],
           outputs=["amstel_stations.parquet", "coverage.parquet", "hydrology.parquet"],
           table=ctx.corridor_all.merge(counts.pivot(index="station_id", columns="parameter_group",
                                                     values="n_observations").reset_index(),
                                        on="station_id", how="left"))
