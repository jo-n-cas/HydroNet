import pandas as pd

from hydronet.views import gaps, pressures, timeaxis


def test_spans_and_overlap():
    s = timeaxis.spans({
        "biology": pd.Series(["1998-06-24", "2024-09-30"]),
        "rwzi": pd.Series(["2021-01-01", "2025-12-31"]),
        "empty": pd.Series([], dtype="object"),
    })
    assert list(s.dataset) == ["biology", "rwzi"]
    assert timeaxis.overlap(s) == (pd.Timestamp("2021-01-01"), pd.Timestamp("2024-09-30"))


def test_overlap_none_cases():
    s = timeaxis.spans({"a": pd.Series(["2000-01-01", "2001-01-01"]),
                        "b": pd.Series(["2005-01-01", "2006-01-01"])})
    assert timeaxis.overlap(s) is None
    assert timeaxis.overlap(s, ["a"]) is None


METRICS = {
    "volume": {"match": {"quantity": "Volume", "parameter": "Niet van toepassing", "unit": "m3"},
               "yearly": "sum", "yearly_unit": "m3/year"},
    "phosphate": {"match": {"quantity": "(massa)Concentratie", "parameter": "fosfaat", "unit": "mg/l"},
                  "yearly": "median", "yearly_unit": "mg P/l"},
}


def _effluent():
    rows = []
    for d in ["2021-01-01", "2021-01-02", "2022-01-01"]:
        rows.append(("UI", "UI.vol", d, "Volume", "Niet van toepassing", "m3", 100.0))
        rows.append(("UI", "UI.puls", d, "Volume", "Pulsvolume", "m3/p", 70.0))     # pulse size, not flow
        rows.append(("WE", "WE.p1", d, "(massa)Concentratie", "fosfaat", "mg/l", 1.0))
        rows.append(("WE", "WE.p2", d, "(massa)Concentratie", "fosfaat", "mg/l", 3.0))
        rows.append(("AW", "AW.research", d, "(massa)Concentratie", "fosfaat", "mg/l", 9.0))
    return pd.DataFrame(rows, columns=["installation", "measurement_point", "date", "quantity",
                                       "parameter", "unit", "value"])


def test_classify_requires_full_match_and_excludes_points():
    c = pressures.classify_metrics(_effluent(), METRICS, exclude_points=["AW.research"])
    assert set(c.metric) == {"volume", "phosphate"}
    assert "UI.puls" not in set(c.measurement_point)
    assert "AW" not in set(c.installation)


def test_yearly_rules_and_gap_matrix():
    c = pressures.classify_metrics(_effluent(), METRICS, exclude_points=["AW.research"])
    y = pressures.yearly(c, METRICS).set_index(["installation", "metric", "year"])
    assert y.loc[("UI", "volume", 2021), "value"] == 200          # sum of 2 days
    assert y.loc[("UI", "volume", 2021), "n_days"] == 2
    assert y.loc[("WE", "phosphate", 2021), "value"] == 2          # 2 points averaged per day, then median
    g = pressures.gap_matrix(c, ["UI", "WE", "AW"], ["volume", "phosphate"])
    assert g.loc["UI", "phosphate"] == 0 and g.loc["WE", "volume"] == 0
    assert g.loc["AW"].sum() == 0 and g.loc["UI", "volume"] == 3


def test_gaps_table_status_labels():
    cov = pd.DataFrame({
        "station_id": ["A", "B", "A", "Z"],
        "parameter_group": ["tier1", "tier3", "meds", "tier1"],
        "n_observations": [100, 50, 4, 999],
    })
    bio = pd.DataFrame({"station_id": ["B"] * 5, "parameter_group": ["tier3"] * 5})
    groups = {"tier1": {"tier": 1}, "tier3": {"tier": 3}, "meds": {"tier": 2, "sparse": True}}
    t = gaps.gaps_table(cov, bio, ["A", "B"], groups).set_index("parameter_group")
    assert t.loc["tier1", "observations_agv"] == 1099 and t.loc["tier1", "observations_amstel"] == 100
    assert t.loc["tier1", "status"] == gaps.STATUS_COUNTS_ONLY
    assert t.loc["meds", "status"] == gaps.STATUS_SPARSE
    assert t.loc["tier3", "status"] == gaps.STATUS_PARTIAL
    assert t.loc["tier3", "share_with_values_amstel"] == 0.1
