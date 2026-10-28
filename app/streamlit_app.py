"""HydroNet: Amstel monitoring explorer. Run: streamlit run app/streamlit_app.py"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for p in (ROOT / "src", ROOT / "app"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import streamlit as st  # noqa: E402

from components import data, sidebar, theme  # noqa: E402

st.set_page_config(page_title="HydroNet · Amstel", layout="wide", initial_sidebar_state="expanded")
theme.apply()

bundle = data.load_bundle(data.data_dir())
if bundle.synthetic:
    st.markdown('<div class="hn-banner" role="alert">Synthetic fixture data: for layout testing only, '
                'not AGV data. Switch <code>ui.data_dir</code> in <code>config/settings.yaml</code> to '
                '<code>data/processed</code> for real outputs.</div>', unsafe_allow_html=True)

st.session_state["ctx"] = sidebar.build(bundle)

PAGES = Path(__file__).parent / "views"   # not "pages/": that name triggers Streamlit's legacy MPA mode
nav = st.navigation([
    st.Page(PAGES / "1_overview.py", title="Overview", default=True),
    st.Page(PAGES / "2_coverage_map.py", title="Coverage map"),
    st.Page(PAGES / "3_station_detail.py", title="Station detail"),
    st.Page(PAGES / "4_amstel_corridor.py", title="Amstel corridor"),
])
nav.run()
