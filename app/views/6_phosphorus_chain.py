import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from components import captions, charts, data, theme
from components.provenance import about_view, empty_state
from hydronet.views import corridor as corridor_views
from hydronet.views import pressures, timeaxis

ctx = st.session_state["ctx"]
b, grp, cfg = ctx.bundle, data.groups(), data.settings()
pcfg, ccfg = cfg["pressures"], cfg["ui"]["phosphorus_chain"]
metrics = pcfg["effluent_metrics"]

st.title("The phosphorus chain")
st.markdown("A guided walk along one possible pathway: **pressure** (a wastewater plant's effluent) → "
            "**water chemistry coverage** on the Amstel near that plant → **biological effect data** nearby. "
            "Each step shows only what the data contain.")
captions.causation_note()

eff, stations, cov = b.get("rwzi_effluent.parquet"), b.get("stations.parquet"), ctx.coverage()
if eff is None or stations is None or cov is None or b.rwzi is None or b.line_rd is None:
    empty_state("; ".join(b.problems.values()) or "data missing",
                "RWZI effluent, stations, coverage, RWZI locations and the Amstel centreline.")
    st.stop()

rw = b.rwzi[b.rwzi.geometry.notna()].copy()
rw = rw.join(corridor_views.locate_on_line(b.line_rd, rw.geometry))
linked = [p for p in pcfg["amstel_linked_rwzi"] if p in set(rw["installation"])]
names = dict(zip(b.rwzi["installation"], b.rwzi["name"].str.replace("rwzi ", "", regex=False)))
default = ccfg["default_plant"] if ccfg["default_plant"] in linked else linked[0]
plant = st.radio("Plant", linked, index=linked.index(default), horizontal=True, format_func=names.get,
                 help="Amstel-linked plants. Uithoorn is the default: upstream and nearest to the river.")
prow = rw.set_index("installation").loc[plant]
plant_km = prow["chainage_m"] / 1000
window_km = st.slider("Stretch around the plant (± km along the river)", 1, 6, int(ccfg["window_km"]),
                      help="Corridor locations within this distance (along the river) of the plant's nearest "
                           "river position. An analysis choice.")

# shared time axis: overlap of effluent and raw biology
bio = ctx.bio_values()
sp = timeaxis.spans({"RWZI effluent": eff["date"], "biology": None if bio is None else bio["datetime"]})
ov = timeaxis.overlap(sp)
# axis = span of the two datasets in this chain (effluent, raw biology), within the sidebar date range
x_range = (max(pd.Timestamp(ctx.date_range[0]), sp["start"].min()), min(pd.Timestamp(ctx.date_range[1]), sp["end"].max()))
ov_txt = f"{ov[0]:%Y}–{ov[1]:%Y}" if ov else "none"
st.markdown(f'<div class="hn-nline">Shared time axis {x_range[0]:%Y}–{x_range[1]:%Y} · '
            f'effluent and raw biology overlap: <b>{ov_txt}</b></div>', unsafe_allow_html=True)

# ---- step 1: pressure
st.markdown(f"## 1 · Pressure: effluent of RWZI {names[plant]}")
captions.tagged(f"Plant site {prow['distance_to_river_m'] / 1000:.1f} km from the Amstel, nearest river km "
                f"{plant_km:.1f}; {prow['location_basis']}; discharge point not verified.", "assumed")
cl = pressures.classify_metrics(eff, metrics, pcfg.get("exclude_measurement_points", []))
dly = pressures.daily(cl[cl["installation"] == plant])
show = ["volume", "phosphate"]
fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.1,
                    subplot_titles=[f"{metrics[k]['label']} (daily, {cl.loc[cl.metric == k, 'unit'].iloc[0] if (cl.metric == k).any() else ''})"
                                    for k in show])
fig.update_annotations(font=dict(size=11, color=theme.MUTED))          # subplot titles
for i, k in enumerate(show, start=1):
    d = dly[dly["metric"] == k]
    if d.empty:
        ax = "" if i == 1 else str(i)
        fig.add_trace(go.Scatter(x=list(x_range), y=[0, 0], mode="lines", line=dict(width=0), hoverinfo="skip"),
                      row=i, col=1)
        fig.add_annotation(x=0.5, y=0.5, xref=f"x{ax} domain", yref=f"y{ax} domain", showarrow=False,
                           text=f"not measured at RWZI {names[plant]}", font=dict(color=theme.MUTED, size=12))
    else:
        fig.add_trace(go.Scattergl(x=d["date"], y=d["value"], mode="lines", line=dict(color=theme.INK, width=0.7),
                                   hovertemplate="%{x|%Y-%m-%d} · %{y:,.3g}<extra></extra>"), row=i, col=1)
    if ov:
        charts.overlap_band(fig, *ov, row=i, col=1, annotate=(i == 1), label="overlap with biology")
fig.update_xaxes(range=list(x_range))
fig.update_layout(height=330, margin=dict(l=60, r=16, t=40, b=30))
st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
with_p = sorted(set(cl.loc[cl["metric"] == "phosphate", "installation"]))
if (dly["metric"] == "phosphate").sum() == 0:
    captions.note(f"RWZI {names[plant]} has no effluent phosphate in the data. Plants that do: "
                  + ", ".join(names.get(p, p) for p in with_p) + " (none of them Amstel-linked). "
                  "Effluent phosphate for the Amstel plants is part of the data request.")
captions.figure_caption("Daily effluent volume and phosphate of the selected plant on the shared time axis; "
                        "the grey band marks the period with both effluent and raw biology data.")
captions.n_line(len(dly), 1, None if dly.empty else dly["date"].min(), None if dly.empty else dly["date"].max())
captions.tagged("Effluent series as delivered.", "observed")

# ---- step 2: chemistry coverage near the plant
st.markdown("## 2 · Water chemistry on the Amstel near the plant")
near = corridor_views.near_chainage(ctx.corridor_all, plant_km * 1000, window_km * 1000)
t1 = [c for c in grp["tier1_nutrients_core"]["codes"]]
c2 = cov[cov["station_id"].isin(near["station_id"]) & cov["parameter"].isin(t1)]
if near.empty:
    empty_state(f"no corridor locations within ±{window_km} km of river km {plant_km:.1f} at a "
                f"{ctx.buffer_m} m buffer.", "widening the stretch or the buffer.")
else:
    order = list(near["station_id"])
    grid = c2.pivot_table(index="parameter", columns="station_id", values="n_observations", aggfunc="sum")
    grid = grid.reindex(index=t1, columns=order).fillna(0)
    xs, ys, sz, tx = [], [], [], []
    vmax = float(grid.values.max() or 1)
    for p in grid.index:
        for s in grid.columns:
            v = grid.loc[p, s]
            xs.append(s); ys.append(p); sz.append(3 if v == 0 else 5 + 15 * np.sqrt(v / vmax)); tx.append(int(v))
    f2 = go.Figure(go.Scatter(x=xs, y=ys, mode="markers", text=tx,
                              marker=dict(size=sz, color=[theme.PAPER if v == 0 else theme.INK for v in tx],
                                          line=dict(width=0.8, color=[theme.ZERO_GREY if v == 0 else theme.INK
                                                                      for v in tx])),
                              hovertemplate="%{y} at %{x}: %{text} observations<extra></extra>"))
    off = dict(zip(near["station_id"], near["offset_m"] / 1000))
    f2.update_xaxes(tickvals=order, ticktext=[f"{s}<br>{off[s] + 0.0:+.1f} km".replace("-0.0", "±0.0").replace("+0.0", "±0.0") for s in order], tickangle=0,
                    title="corridor locations, ordered upstream → downstream (offset from the plant's river km)")
    f2.update_yaxes(autorange="reversed", showgrid=False)
    f2.update_layout(height=60 + 26 * len(t1) + 50, margin=dict(l=140, r=16, t=16, b=70))
    st.plotly_chart(f2, width="stretch", config={"displayModeBar": False})
    captions.note("Counts only: the prototype has no raw chemistry values, so concentrations along this "
                  "stretch cannot be shown. Raw FYCHEM values for these locations are the first data request.")
    captions.figure_caption("Grid of Tier 1 parameters (rows) by corridor locations near the plant (columns). "
                            "Dot size = number of observations; open grey = not measured.")
    captions.n_line(int(c2["n_observations"].sum()), len(near), extra=f"±{window_km} km around river km {plant_km:.1f}")
    captions.tagged("Counts per location.", "observed")
    captions.tagged("Offsets along the river (upstream → downstream) are indicative.", "assumed")

# ---- step 3: biological effect data nearby
st.markdown("## 3 · Biological effect data nearby")
raw_ids = set(stations.loc[stations["has_raw_bio"], "station_id"])
raw_corr = ctx.corridor_all[ctx.corridor_all["station_id"].isin(raw_ids)].copy()
if raw_corr.empty:
    empty_state(f"none of the raw-biology locations lies within {ctx.buffer_m} m of the Amstel.",
                "the full HB export for corridor locations, or a 100 m buffer.")
else:
    raw_corr["river_distance_km"] = (raw_corr["chainage_m"] / 1000 - plant_km).abs()
    pick = raw_corr.sort_values("river_distance_km").iloc[0]
    sid = pick["station_id"]
    captions.tagged(f"Nearest raw-biology location on the corridor: {sid}, "
                    f"{pick['river_distance_km']:.1f} km along the river from the plant's river km "
                    f"({pick['distance_to_river_m']:.0f} m from the centreline).", "assumed")
    bs = bio[bio["station_id"] == sid] if bio is not None else None
    if bs is None or bs.empty:
        empty_state("no raw biology rows match the date range and quality-code filter.", "widening the filters.")
    else:
        st.plotly_chart(charts.bio_small_multiples(bs, x_range=x_range, overlap=ov), width="stretch",
                        config={"displayModeBar": False})
        in_ov = bs if not ov else bs[(pd.to_datetime(bs["datetime"]) >= ov[0]) & (pd.to_datetime(bs["datetime"]) <= ov[1])]
        captions.figure_caption("Raw biology values at the nearest corridor location on the same time axis as "
                                "step 1; flags styled as on Station detail.")
        captions.n_line(len(bs), 1, bs["datetime"].min(), bs["datetime"].max(),
                        extra=f"{len(in_ov)} values inside the overlap period")
        captions.tagged("Raw values as delivered.", "observed")

st.markdown("## What this chain can and cannot say")
st.markdown("- It shows **where** effluent enters near the river, **what** is monitored nearby and **when** "
            "the datasets overlap.\n- It cannot show whether effluent changes phosphorus in the river (no raw "
            "chemistry values, no verified discharge point, no flow routing), nor whether biology responds.\n"
            "- Next step: raw FYCHEM values (Tier 1) for the locations in step 2 and effluent phosphate for "
            "the Amstel plants (see Data gaps).")
captions.settings_caption(["buffer", "dates", "quality codes", "data"],
                          extra=f"plant={names[plant]} · window=±{window_km} km")
about_view("phosphorus_chain", b, sources=["rwzi_effluent.parquet", "config/rwzi_locations.csv", "coverage.parquet",
                                           "amstel_stations.parquet", "bio_values.parquet"],
           steps=["classify effluent metrics", "project plant on river", f"corridor ±{window_km} km",
                  "Tier 1 counts", "nearest raw-biology location"],
           outputs=["rwzi_effluent.parquet", "coverage.parquet", "bio_values.parquet"],
           table=c2 if not near.empty else None)
