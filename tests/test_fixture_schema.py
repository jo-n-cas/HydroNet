import geopandas as gpd
import pandas as pd
import pytest

from hydronet.config import repo_path
from hydronet.schemas import SCHEMAS, missing_columns

FIXTURES = repo_path("tests/fixtures/processed")


@pytest.mark.parametrize("name", sorted(SCHEMAS))
def test_fixture_matches_contract(name):
    path = FIXTURES / name
    assert path.exists(), f"run scripts/make_ui_fixtures.py ({name} missing)"
    df = gpd.read_parquet(path) if name == "stations.parquet" else pd.read_parquet(path)
    assert missing_columns(name, df) == []
    assert len(df) > 0


def test_fixture_ids_are_marked_synthetic():
    st = gpd.read_parquet(FIXTURES / "stations.parquet")
    assert st.station_id.str.startswith("SYN").all()
