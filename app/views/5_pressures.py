import pandas as pd
import streamlit as st

from components import captions, charts, data
from components.provenance import about_view, empty_state
from hydronet.views import corridor as corridor_views
from hydronet.views import pressures, timeaxis

ctx = st.session_state["ctx"]
b, cfg = ctx.bundle, data.settings()
pcfg = cfg["pressures"]
metrics = pcfg["effluent_metrics"]

st.title("Pressures · wastewater treatment plants")
st.markdown("Effluent of AGV's wastewater treatment plants (RWZIs), per year. The Amstel-linked plants come "
            "first; the rest of AGV is shown as context below.")
captions.causation_note()

eff = b.get("rwzi_effluent.parquet")
if eff is None or b.rwzi is None:
    empty_state(b.problems.get("rwzi_effluent.parquet", "RWZI locations missing"),
                "`rwzi_effluent.parquet` (instructions 5.1) and `config/rwzi_locations.csv`.")
    st.stop()

eff_f = timeaxis.clip(eff, "date", ctx.date_range[0], ctx.date_range[1])
classified = pressures.classify_metrics(eff_f, metrics, pcfg.get("exclude_measurement_points", []))
yearly = pressures.yearly(classified, metrics)
rw = b.rwzi.copy()
has_geom = rw.geometry.notna()
if b.line_rd is not None:
    rw = rw.join(corridor_views.locate_on_line(b.line_rd, rw.geometry[has_geom]))   # NaN where no location
else:
    rw["distance_to_river_m"] = rw["chainage_m"] = None
linked = pcfg["amstel_linked_rwzi"]
gaps = pressures.gap_matrix(classified, rw["installation"], list(metrics))
years = (int(pd.Timestamp(ctx.date_range[0]).year), int(pd.Timestamp(ctx.date_range[1]).year))
if not yearly.empty:
    years = (max(years[0], int(yearly["year"].min())), min(years[1], int(yearly["year"].max())))


def plant_label(row) -> str:
    name = row["name"].replace("rwzi ", "")
    if pd.isna(row.get("distance_to_river_m")):
        return f"{name} (no location)"
    return f"{name} · {row['distance_to_river_m'] / 1000:.1f} km · km {row['chainage_m'] / 1000:.1f}"


st.markdown("## Amstel-linked plants")
captions.tagged("Linked to the Amstel in public sources; plant sites, discharge points not verified.", "assumed")
sub = rw[rw["installation"].isin(linked)].set_index("installation").loc[linked].reset_index()
plants = [(r["installation"], plant_label(r)) for _, r in sub.iterrows()]
st.plotly_chart(charts.rwzi_grid(yearly, gaps, plants, metrics, years), width="stretch",
                config={"displayModeBar": False})
captions.figure_caption("Small multiples: one row per plant (distance of the plant site to the river and "
                        "nearest river km in the label), one column per effluent metric, shared y-axis per "
                        "column. 'not measured' marks plant–metric combinations without data.")
missing = [f"{r['name'].replace('rwzi ', '')}: {', '.join(metrics[m]['label'].lower() for m in metrics if gaps.loc[r['installation'], m] == 0)}"
           for _, r in sub.iterrows() if (gaps.loc[r["installation"]] == 0).any()]
if missing:
    captions.note("Not measured in the effluent data: " + "; ".join(missing) + ". No Amstel-linked plant has "
                  "effluent phosphate in the current files.")
n_days = int(classified[classified["installation"].isin(linked)]["date"].nunique())
captions.n_line(int(classified["installation"].isin(linked).sum()), len(linked),
                extra=f"{n_days:,} distinct days · {years[0]}–{years[1]}")
captions.tagged("Effluent series as delivered; yearly summaries as stated in the column titles.", "observed")
captions.settings_caption(["dates", "data"])

st.markdown("## Monitoring locations near each plant")
stations = b.get("stations.parquet")
buf = pcfg["nearby_station_buffer_m"]
if stations is not None:
    links = corridor_views.proximity_links(rw[rw["installation"].isin(linked)], stations, buf)
    links["on_amstel_corridor"] = links["station_id"].isin(ctx.corridor_all["station_id"])
    links["distance_km"] = links["distance_m"] / 1000
    st.dataframe(links.merge(rw[["installation", "name"]], on="installation")[
        ["name", "station_id", "distance_km", "on_amstel_corridor"]], hide_index=True, width="stretch",
        column_config={"distance_km": st.column_config.NumberColumn("distance (km)", format="%.2f")})
    captions.n_line(n_loc=int(links["station_id"].nunique()),
                    extra=f"within {buf / 1000:.0f} km of a plant site ({int(links['on_amstel_corridor'].sum())} "
                          "on the corridor)")
    captions.tagged(f"'Near' = within {buf:,} m of the plant site: an analysis choice, not a norm.", "assumed")

with st.expander("Rest of AGV (context)"):
    rest = rw[~rw["installation"].isin(linked)].sort_values("distance_to_river_m", na_position="last")
    plants_r = [(r["installation"], plant_label(r)) for _, r in rest.iterrows()]
    st.plotly_chart(charts.rwzi_grid(yearly, gaps, plants_r, metrics, years), width="stretch",
                    config={"displayModeBar": False})
    no_loc = rest[rest.geometry.isna()]["name"].tolist()
    if no_loc:
        st.caption("Without a verified location (tables only, not on maps): " + ", ".join(no_loc) + ".")

st.markdown("## Data availability per plant")
gtab = gaps.rename(columns={k: metrics[k]["label"] for k in metrics}).reset_index()
gtab = gtab.merge(rw[["installation", "name"]], on="installation")
st.dataframe(gtab.set_index("name").drop(columns="installation"), width="stretch",
             column_config={c: st.column_config.ProgressColumn(c, format="%d days", min_value=0,
                                                               max_value=int(gaps.values.max() or 1))
                            for c in [metrics[k]["label"] for k in metrics]})
captions.figure_caption("Days with data per plant and metric in the selected date range; 0 = not measured.")
captions.settings_caption(["dates", "data"])

about_view("pressures", b, sources=["rwzi_effluent.parquet", "config/rwzi_locations.csv (OSM)",
                                    "config/settings.yaml (effluent_metrics)"],
           steps=["keep Effluent rows", "match quantity + parameter + unit to a metric",
                  "exclude non-effluent points", "average points per day", "yearly sum / median"],
           outputs=["rwzi_effluent.parquet"], table=yearly)
