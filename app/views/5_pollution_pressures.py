"""Pollution pressures in the AGV area: embeds the standalone OSM map (app/assets/agv-pressures-map-osm.html)."""

from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

ASSET = Path(__file__).resolve().parents[1] / "assets" / "agv-pressures-map-osm.html"

st.title("Pollution pressures")
st.markdown("Industrial sites, wastewater plants, waste and energy sites, and marinas in the AGV area "
            "(OpenStreetMap), linked to the KRW substances each sector typically releases. These links are "
            "based on typical sector emissions: leads to check, not measurements or permit data.")

if not ASSET.exists():
    st.warning(f"Map file not found. Copy `agv-pressures-map-osm.html` to `{ASSET.parent.name}/` "
               f"(expected at `app/assets/agv-pressures-map-osm.html`).")
    st.stop()

# The map loads Leaflet and the OSM tiles from the web, so it needs an internet connection.
components.html(ASSET.read_text(encoding="utf-8"), height=1900, scrolling=True)
st.caption("Map data © OpenStreetMap contributors (ODbL). Sector-to-substance links are indicative.")
