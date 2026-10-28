import pandas as pd
import streamlit as st

from components import captions, charts
from components.provenance import about_view, empty_state
from hydronet.views import coverage, timeaxis

ctx = st.session_state["ctx"]
b = ctx.bundle

st.title("HydroNet · the Amstel")
st.markdown(
    "HydroNet shows **what is measured along the Amstel, where, and how often**, next to the "
    "wastewater treatment plants (RWZIs) near the river and the river's water level. It is an exploratory "
    "instrument, not a status dashboard.\n\n"
    "**It can say:** which locations measure which parameters (counts), how coverage changes along the "
    "river, which plants lie near which stretch, and which data are missing.  \n"
    "**It cannot say:** concentrations or KRW status of the river (raw chemistry values are not in the "
    "prototype), or whether a plant affects a station (observational data, no causal claims)."
)

cov = b.get("coverage.parquet")
stations = b.get("stations.parquet")
if cov is None or stations is None:
    empty_state(b.problems.get("coverage.parquet") or b.problems.get("stations.parquet", "data missing"),
                "the pipeline outputs `coverage.parquet` and `stations.parquet` (instructions 5.1–5.3).")
    st.stop()

amstel = coverage.totals(cov, ctx.corridor_all["station_id"])
agv = coverage.totals(cov)
bio = b.get("bio_values.parquet")
raw_ids = set(stations.loc[stations["has_raw_bio"], "station_id"])
raw_amstel = raw_ids & set(ctx.corridor_all["station_id"])


def cell(k, v, s):
    return f'<div><div class="k">{k}</div><div class="v">{v}</div><div class="s">{s}</div></div>'


st.markdown("## Data card")
st.markdown(
    '<div class="hn-card">'
    + cell("Amstel locations", f"{amstel['n_locations']:,}",
           f"within {ctx.buffer_m} m · AGV-wide {agv['n_locations']:,}")
    + cell("Chemistry / biology", f"{amstel['n_locations_chem']:,} / {amstel['n_locations_bio']:,}",
           f"AGV-wide {agv['n_locations_chem']:,} / {agv['n_locations_bio']:,}")
    + cell("Observations (counts)", f"{amstel['n_observations']:,}",
           f"AGV-wide {agv['n_observations']:,} · {amstel['n_observations'] / max(agv['n_observations'], 1):.1%}"
           " on the Amstel")
    + cell("Locations with raw values", f"{len(raw_amstel)} of {len(raw_ids)}",
           "raw biology only · no raw chemistry")
    + cell("Raw biology rows", f"{0 if bio is None else len(bio):,}",
           f"{0 if bio is None else int(bio['station_id'].isin(raw_amstel).sum()):,} on the Amstel")
    + "</div>", unsafe_allow_html=True)
captions.tagged("Counts come from the AGV location inventories (aggregate observation counts per "
                "parameter); they say what was measured, not what was found.", "observed")
captions.settings_caption(["buffer", "source", "data"])

st.markdown("## Observed vs assumed")
st.markdown(
    f"{captions.tag('observed')} directly from the data: counts, dates, raw biology values, effluent series, "
    "water level and Q.  \n"
    f"{captions.tag('assumed')} assumptions and indicative orderings: upstream → downstream position along "
    "the river, plant location used as discharge point, sensor positions at their structures, and treating "
    "overlapping periods as comparable.", unsafe_allow_html=True)

st.markdown("## Time spans of the datasets")
dates = {"Biology (raw values)": None if bio is None else bio["datetime"]}
hyd = b.get("hydrology.parquet")
if hyd is not None:
    for site in ["Amstelsluizen", "Berlagebrug"]:
        dates[f"Hydrology · {site}"] = hyd.loc[hyd["site"] == site, "date"]
eff = b.get("rwzi_effluent.parquet")
dates["RWZI effluent"] = None if eff is None else eff["date"]
spans = timeaxis.spans({k: v for k, v in dates.items() if v is not None})
ov = timeaxis.overlap(spans, ["Biology (raw values)", "RWZI effluent"])
st.plotly_chart(charts.spans_chart(spans, ov, "biology ∩ RWZI"), width="stretch",
                config={"displayModeBar": False})
captions.figure_caption("Horizontal lines show the first and last date of each dataset. The grey band "
                        "marks the period in which raw biology and RWZI effluent data both exist.")
captions.tagged("Comparisons across datasets are limited to the shaded overlap.", "assumed")
captions.settings_caption(["data"])
about_view("overview", b, sources=["coverage.parquet", "stations.parquet", "bio_values.parquet",
                                   "hydrology.parquet", "rwzi_effluent.parquet", "amstel_stations.parquet"],
           steps=["count per location (inventories)", "select Amstel locations by buffer", "date spans"],
           outputs=["coverage.parquet", "bio_values.parquet", "hydrology.parquet", "rwzi_effluent.parquet"],
           table=pd.concat([pd.DataFrame([{"scope": "Amstel", **amstel}, {"scope": "AGV-wide", **agv}]),
                            spans.assign(scope="time span")], ignore_index=True))
