import plotly.graph_objects as go
import streamlit as st

from components import captions, data, theme
from components.provenance import about_view, empty_state
from hydronet.groups import group_label
from hydronet.views import gaps

ctx = st.session_state["ctx"]
b, grp = ctx.bundle, data.groups()

st.title("Data gaps")
st.markdown("What AGV's systems hold (observation counts in the location inventories) versus what the "
            "prototype can actually show (raw values). This is the quantified basis for the data request.")

cov = b.get("coverage.parquet")
if cov is None:
    empty_state(b.problems.get("coverage.parquet", "missing"), "`coverage.parquet`.")
    st.stop()

t = gaps.gaps_table(cov, b.get("bio_values.parquet"), ctx.corridor_all["station_id"], grp)
t["group"] = t["parameter_group"].map(lambda k: group_label(k, grp))

st.markdown("## Amstel corridor vs AGV-wide")
st.dataframe(
    t[["group", "observations_amstel", "locations_amstel", "values_in_prototype_amstel",
       "share_with_values_amstel", "observations_agv", "locations_agv", "values_in_prototype_agv", "status"]],
    hide_index=True, width="stretch",
    column_config={
        "group": st.column_config.TextColumn("parameter group", width="large"),
        "observations_amstel": st.column_config.NumberColumn("Amstel: observations", format="%d"),
        "locations_amstel": st.column_config.NumberColumn("Amstel: locations", format="%d"),
        "values_in_prototype_amstel": st.column_config.NumberColumn("Amstel: raw values", format="%d"),
        "share_with_values_amstel": st.column_config.ProgressColumn("Amstel: share with values", format="percent",
                                                                    min_value=0, max_value=1),
        "observations_agv": st.column_config.NumberColumn("AGV: observations", format="%d"),
        "locations_agv": st.column_config.NumberColumn("AGV: locations", format="%d"),
        "values_in_prototype_agv": st.column_config.NumberColumn("AGV: raw values", format="%d"),
        "status": st.column_config.TextColumn("status on the Amstel"),
    })
captions.figure_caption("Per parameter group: observation counts on the Amstel corridor and AGV-wide, and the "
                        "number of raw values available in the prototype (biology only). Sparse groups "
                        "(medicines, PFAS) are labelled 'too sparse to trace a source'.")
captions.n_line(int(t["observations_amstel"].sum()), len(ctx.corridor_all),
                extra=f"AGV-wide {int(t['observations_agv'].sum()):,} observations")
captions.settings_caption(["buffer", "data"])

st.markdown("## Where the values are missing")
d = t[t["observations_amstel"] > 0].sort_values("observations_amstel")
labels = [g.split(" · ")[-1] for g in d["group"]]
fig = go.Figure()
fig.add_trace(go.Scatter(x=d["observations_amstel"], y=labels, mode="markers", name="observations (counts)",
                         marker=dict(size=9, color=theme.INK)))
fig.add_trace(go.Scatter(x=d["values_in_prototype_amstel"].clip(lower=1), y=labels, mode="markers",
                         name="raw values in prototype", marker=dict(size=9, symbol="circle-open", color=theme.ACCENT,
                                                                     line=dict(width=1.6))))
for x0, x1, y in zip(d["values_in_prototype_amstel"].clip(lower=1), d["observations_amstel"], labels):
    fig.add_shape(type="line", x0=x0, x1=x1, y0=y, y1=y, line=dict(color=theme.HAIRLINE, width=1))
fig.add_annotation(x=1, y=1.02, xref="paper", yref="paper", xanchor="right", showarrow=False,
                   text="● observations in AGV systems   ○ raw values in the prototype (0 drawn at 1)",
                   font=dict(size=10, color=theme.MUTED))
fig.update_xaxes(type="log", title="count on the Amstel corridor (log scale)")
fig.update_layout(height=60 + 30 * len(d) + 40, margin=dict(l=10, r=16, t=30, b=40))
fig.update_yaxes(automargin=True, showgrid=False)
st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
captions.figure_caption("Dumbbell chart: for each group on the Amstel, filled dot = observations that exist, "
                        "open orange dot = raw values the prototype can show. The gap between them is the "
                        "data still to be requested.")

st.markdown("## Sparse tracers")
for key in [k for k, g in grp.items() if g.get("sparse")]:
    row = t[t["parameter_group"] == key]
    if row.empty:
        st.markdown(f"**{group_label(key, grp)}**: not measured in the inventories.")
        continue
    r = row.iloc[0]
    st.markdown(f"**{group_label(key, grp)}**: {int(r['observations_amstel']):,} observations at "
                f"{int(r['locations_amstel'])} Amstel locations ({int(r['observations_agv']):,} at "
                f"{int(r['locations_agv'])} AGV-wide). Too sparse to trace a source; measured at the "
                "upstream and downstream ends of the river only.")
captions.tagged("Counts from the inventories.", "observed")

request = ["# HydroNet data request (generated)", "", "| group | Amstel obs | Amstel locations | raw values | status |",
           "|---|---|---|---|---|"]
request += [f"| {r['group']} | {r['observations_amstel']} | {r['locations_amstel']} | "
            f"{r['values_in_prototype_amstel']} | {r['status']} |" for _, r in t.iterrows()]
st.download_button("Export as DATA_REQUEST.md", "\n".join(request).encode(), file_name="DATA_REQUEST.md",
                   mime="text/markdown", help="Same table in Markdown, for the request to AGV.")
about_view("data_gaps", b, sources=["coverage.parquet", "bio_values.parquet", "amstel_stations.parquet",
                                    "config/parameter_groups.yaml"],
           steps=["group parameters", "sum counts Amstel / AGV-wide", "count raw values", "label status"],
           outputs=["coverage.parquet", "bio_values.parquet"], table=t)
