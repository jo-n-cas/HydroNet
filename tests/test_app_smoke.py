"""Headless smoke test: every page renders on the fixtures, also under changed settings."""

import os
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parents[1] / "app" / "streamlit_app.py")
PAGES = ["views/1_overview.py", "views/2_coverage_map.py", "views/3_station_detail.py",
         "views/4_amstel_corridor.py"]


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


@pytest.mark.parametrize("page", ["views/2_coverage_map.py", "views/4_amstel_corridor.py"])
def test_pages_render_with_narrow_settings(page):
    at = _run(page, buffer_m=25, stretch_km=(2.0, 6.0), group="tier2_medicines", source="chem")
    assert not at.exception, [e.message for e in at.exception]
