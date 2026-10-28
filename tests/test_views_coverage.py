import pandas as pd

from hydronet.config import load_parameter_groups
from hydronet.groups import OTHER, add_group_column, assign_group
from hydronet.views import coverage

GROUPS = {
    "tier1": {"codes": ["Ptot_mgP/l", "CHLFa_ug/l_spectro"]},
    "metals": {"category": "METAL"},
    "phyto": {"prefixes": ["FPA_"], "codes": ["CHLFa_ug/l_spectro"]},
}


def _cov():
    return pd.DataFrame({
        "station_id": ["A", "A", "B", "B", "C"],
        "source": ["chem", "chem", "chem", "bio", "bio"],
        "parameter": ["Ptot_mgP/l", "Cu_ug/l", "Ptot_mgP/l", "FPA_n", "XYZ"],
        "category": [None, "METAL", None, None, None],
        "n_observations": [10, 5, 3, 7, 1],
    })


def test_assign_group_first_match_wins_and_other():
    assert assign_group("CHLFa_ug/l_spectro", None, GROUPS) == "tier1"
    assert assign_group("Cu_ug/l", "METAL", GROUPS) == "metals"
    assert assign_group("FPA_mm3/l", None, GROUPS) == "phyto"
    assert assign_group("XYZ", None, GROUPS) == OTHER


def test_by_group_and_area_filter():
    cov = add_group_column(_cov(), GROUPS)
    allg = coverage.by_group(cov).set_index("parameter_group")
    assert allg.loc["tier1", "n_observations"] == 13
    assert allg.loc["tier1", "n_locations"] == 2
    area = coverage.by_group(cov, ["A"]).set_index("parameter_group")
    assert set(area.index) == {"tier1", "metals"}
    assert coverage.by_group(cov, ["nope"]).empty


def test_per_station_and_totals():
    cov = add_group_column(_cov(), GROUPS)
    s = coverage.per_station(cov, parameter="Ptot_mgP/l")
    assert s.to_dict() == {"A": 10, "B": 3}
    t = coverage.totals(cov)
    assert t["n_observations"] == 26 and t["n_locations_bio"] == 2 and t["n_observations_chem"] == 18


def test_real_group_config_orders_tier1_before_phytoplankton():
    groups = load_parameter_groups()
    assert assign_group("CHLFa_ug/l_spectro", None, groups) == "tier1_nutrients_core"
    assert assign_group("CHLFa_ug/l_blauwalg", "ALG", groups) == "tier3_phytoplankton"
    assert assign_group("carbmzpne_ug/l", "MEDICIJN", groups) == "tier2_medicines"
    assert assign_group("FRD-903_ng/l", None, groups) == "tier2_pfas"
    assert assign_group("PTN_BEDKG_%", "HYBIO", groups) == "tier3_macrophytes"
