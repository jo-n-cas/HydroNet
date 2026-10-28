import json

import numpy as np
import pandas as pd
import pytest

from hydronet import cleaning, hydrology, io, pipeline, pressures
from hydronet.config import repo_path


def test_parse_parameter_counts_strips_numpy_wrappers():
    assert io.parse_parameter_counts("{'MEA_n': np.int64(426), 'X': np.int64(2)}") == {"MEA_n": 426, "X": 2}
    with pytest.raises((ValueError, SyntaxError)):
        io.parse_parameter_counts("{'a': __import__('os')}")          # no eval of arbitrary code


def _hb(**over):
    base = {"locatiecode": ["A", "A", "A", "A"], "monsterident": ["1", "1", "2", "2"],
            "datum": ["2020-06-01 00:00", "2020-06-01 00:00", "2021-06-01 00:00", "bad"],
            "fewsparameter": ["PTN_BEDKG_%", "PTN_BEDKG_%", "MEA_n", "MEA_n"],
            "biotaxonnaam": ["t1", "t2", "t3", "t4"], "TWN taxontype": ["Macrophytes"] * 4,
            "meetwaarde": ["120", "-999", "5,5", "3"], "eenheid": ["%", "%", "n", "n"],
            "limietsymbool": [None, None, ">", None], "kwaliteitsoordeelcode": ["0", "0", "3", "0"]}
    base.update(over)
    return pd.DataFrame(base)


def test_clean_bio_rejects_sentinels_and_bad_dates_flags_bounds_keeps_limits():
    dictionary = pd.DataFrame({"ID": ["PTN_BEDKG_%"], "H_MIN": [0.0], "H_MAX": [None], "Z_MIN": [None],
                               "Z_MAX": [100.0]})
    bio, rej = cleaning.clean_bio(_hb(), dictionary, [-999])
    assert sorted(rej["reason"]) == ["sentinel_-999", "unparseable_date"]
    assert len(bio) == 2
    assert bio.loc[bio.value == 120, "qa_flag"].iloc[0] == "out_of_range"      # flagged, not removed
    assert bio.loc[bio.value == 5.5, "limit_flag"].iloc[0] == ">"             # decimal comma parsed, limit kept
    assert bio.loc[bio.value == 5.5, "quality_code"].iloc[0] == 3


def test_hydrology_two_header_rows_and_robust_flag(tmp_path):
    rows = ["GMT+1;S1", ";WATHTE.mNAP.dag.gem"] + [f"{d}-1-2020 01:00;-0.4{d % 3}" for d in range(1, 29)]
    rows.append("29-1-2020 01:00;-9.0")
    rows.append("xx;-0.41")
    p = tmp_path / "h.csv"
    p.write_text("\n".join(rows))
    with p.open() as fh:
        ids, labels = fh.readline().strip().split(";"), fh.readline().strip().split(";")
    raw = pd.read_csv(p, sep=";", skiprows=2, header=None, names=ids, dtype=str)
    raw.attrs["labels"] = dict(zip(ids, labels))
    d, r = hydrology.tidy_sensor_file(raw, "Test", k=6)
    assert set(d["quantity"]) == {"level_mNAP"}
    assert d.loc[d.value == -9.0, "qa_flag"].iloc[0] == "outlier_robust"
    assert d["qa_flag"].notna().sum() == 1
    assert list(r["reason"]) == ["unparseable_date"]
    assert d["date"].min() == pd.Timestamp("2020-01-01")                       # day-first parsing


def test_build_effluent_keeps_effluent_only_and_rejects_bad_values():
    vals = pd.DataFrame({"InstallationCodeOrigin": ["NL.11.UI"] * 3, "MeasurementPointID": ["e", "e", "i"],
                         "Date": ["2021-01-01", "2021-01-02", "2021-01-01"], "Value": ["10", "x", "5"],
                         "Unit": ["m3", "m3", "m3"]})
    pts = pd.DataFrame({"MeasurementPointID": ["e", "i"], "ProductDescription": ["Effluent", "Influent"],
                        "QuantityDescription": ["Volume", "Volume"],
                        "ParameterDescription": ["Niet van toepassing", "Niet van toepassing"]})
    inst = pd.DataFrame({"Installation": ["NL.11.UI"], "Installation Description": ["rwzi Uithoorn "]})
    eff, rej = pressures.build_effluent(vals, pts, inst)
    assert len(eff) == 1 and eff["installation_name"].iloc[0] == "rwzi Uithoorn"
    assert len(rej) == 1


PROCESSED = repo_path("data/processed")


def test_partial_run_rejects_stale_rwzi_output(tmp_path, monkeypatch):
    (tmp_path / "rwzi_effluent.parquet").touch()
    monkeypatch.setattr(pipeline, "load_settings", lambda: {"paths": {"processed_dir": "data/processed"}})
    monkeypatch.setattr(pipeline, "repo_path", lambda _: tmp_path)
    with pytest.raises(FileExistsError, match="older rwzi_effluent"):
        pipeline.run(without_rwzi=True)


@pytest.mark.skipif(not (PROCESSED / "pipeline_manifest.json").exists(), reason="pipeline not run on real data")
def test_real_outputs_match_documented_amstel_selection():
    m = json.loads((PROCESSED / "pipeline_manifest.json").read_text())
    a = m["checks"]["amstel_locations"]
    assert (a["n"], a["chem"], a["bio"], a["raw_bio"]) == (76, 26, 61, ["VGD125"])
    assert m["outputs"]["bio_values.parquet"]["rejected"].get("sentinel_-999") == 6
    st = pd.read_parquet(PROCESSED / "coverage.parquet")
    assert st["station_id"].nunique() == 4093 + 1321 - 443


def test_hydrology_suspect_codes_take_precedence_and_are_kept():
    vals = [f"{d}-1-2020 01:00;-0.4{d % 3}" for d in range(1, 29)] + ["29-1-2020 01:00;-32.768"]
    raw = pd.DataFrame([r.split(";") for r in vals], columns=["GMT+1", "S1"])
    raw.attrs["labels"] = {"GMT+1": "", "S1": "WATHTE.mNAP.dag.gem"}
    d, _ = hydrology.tidy_sensor_file(raw, "T", 6, {"level_mNAP": {-32.768: "sentinel_-32.768"}})
    assert len(d) == 29
    assert d.loc[d.value == -32.768, "qa_flag"].iloc[0] == "sentinel_-32.768"
    assert d["qa_flag"].notna().sum() == 1
