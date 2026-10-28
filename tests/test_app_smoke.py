"""Headless smoke test: every page renders on the fixtures, also under changed settings."""

import os
from pathlib import Path
from unittest.mock import patch

import pytest
from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parents[1] / "app" / "streamlit_app.py")
PAGES = ["views/1_overview.py", "views/2_coverage_map.py", "views/3_station_detail.py",
         "views/4_amstel_corridor.py", "views/5_pressures.py", "views/6_phosphorus_chain.py",
         "views/7_data_gaps.py", "views/8_methods.py", "views/9_detection.py"]


def _run(page, **state):
    os.environ["HYDRONET_DATA_DIR"] = "tests/fixtures/processed"     # always test on fixtures
    at = AppTest.from_file(APP, default_timeout=180)
    for k, v in state.items():
        at.session_state[k] = v
    at.run()
    at.switch_page(page)
    at.run()
    return at


@pytest.mark.parametrize("page", PAGES)
def test_page_renders_with_defaults(page):
    at = _run(page)
    assert not at.exception, [e.message for e in at.exception]
    assert at.session_state["ctx"].bundle.synthetic          # fixtures are flagged (banner shown in browser)


@pytest.mark.parametrize("page", ["views/2_coverage_map.py", "views/4_amstel_corridor.py",
                                  "views/6_phosphorus_chain.py", "views/7_data_gaps.py"])
def test_pages_render_with_narrow_settings(page):
    at = _run(page, buffer_m=25, stretch_km=(2.0, 6.0), group="tier2_medicines", source="chem")
    assert not at.exception, [e.message for e in at.exception]


def test_detection_page_switches_between_three_chemicals():
    at = _run("views/9_detection.py")
    chemical = next(s for s in at.selectbox if s.label == "Chemical")
    overview = next(r for r in at.radio if r.label == "Overview")
    assert len(overview.options) == 2
    assert not any(s.label == "Entry hypothesis" for s in at.selectbox)
    assert not at.button
    overview.set_value("Map 2 · Possible entry and downstream route")
    with patch("streamlit_folium.st_folium") as render_map:
        at.run()
    assert 'aria-label="Map 2 legend"' in render_map.call_args.args[0].get_root().render()
    assert not at.exception, [e.message for e in at.exception]
    assert not any(s.label == "Entry hypothesis" for s in at.selectbox)
    reaches = at.dataframe[0].value
    assert ((reaches["previous_station"] == "AMS030") &
            (reaches["station_id"] == "AMS003") &
            (reaches["count_rise"] == 636)).any()
    assert len(chemical.options) == 3
    for parameter in ["NH4_mgN/l_nf", "Ptot_mgP/l"]:
        chemical.set_value(parameter)
        at.run()
        assert not at.exception, [e.message for e in at.exception]
