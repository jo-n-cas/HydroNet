"""Generate SYNTHETIC processed outputs for building and testing the UI.

All values are random (seeded). Station IDs start with "SYN" so a fixture value can
never be mistaken for AGV data. Only public reference geometry is real: the Amstel
centreline (OSM, if built) and the RWZI locations in config/rwzi_locations.csv.
Data *availability* per RWZI and metric mirrors the real files (e.g. no effluent
phosphate at Uithoorn), because the UI must show those gaps; the numbers do not.

Usage:  python scripts/make_ui_fixtures.py [OUT_DIR]   (default tests/fixtures/processed)
"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.geometry import LineString, Point

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from hydronet.config import load_settings, repo_path  # noqa: E402

RNG = np.random.default_rng(20261028)

# (code, NAME, UNIT, dictionary GROUP, P_categorie, source)
PARAMS = [
    ("Ptot_mgP/l", "Fosfor (synthetic fixture)", "mg/l", "Concentratie mg/l", "NUTRI", "chem"),
    ("PO4_mgP/l_nf", "Ortho-fosfaat na filtratie", "mg/l", "Concentratie mg/l", "NUTRI", "chem"),
    ("Ntot_mgN/l", "Stikstof", "mg/l", "Concentratie mg/l", "NUTRI", "chem"),
    ("NH4_mgN/l_nf", "Ammonium na filtratie", "mg/l", "Concentratie mg/l", "NUTRI", "chem"),
    ("NO3_mgN/l_nf", "Nitraat na filtratie", "mg/l", "Concentratie mg/l", "NUTRI", "chem"),
    ("O2_%", "Zuurstofverzadigingspercentage", "%", "Percentage", "VELD", "chem"),
    ("O2_mg/l", "Zuurstof (mg/l)", "mg/l", "Concentratie mg/l", "VELD", "chem"),
    ("CHLFa_ug/l_spectro", "Chlorofyl-a", "ug/l", "Concentratie ug/l", "ALG", "chem"),
    ("ZICHT_m", "Doorzicht (m)", "m", "Lengte", "VELD", "chem"),
    ("T_oC", "Temperatuur (oC)", "oC", "Temperatuur", "VELD", "chem"),
    ("pH", "Zuurgraad", "DIMSLS", "Typering", "VELD", "chem"),
    ("Cl_mg/l", "Chloride (mg/l)", "mg/l", "Concentratie mg/l", "IONEN", "chem"),
    ("Cu_ug/l", "Koper (ug/l)", "ug/l", "Concentratie ug/l", "METAL", "chem"),
    ("Zn_ug/l", "Zink (ug/l)", "ug/l", "Concentratie ug/l", "METAL", "chem"),
    ("Ni_ug/l", "Nikkel (ug/l)", "ug/l", "Concentratie ug/l", "METAL", "chem"),
    ("E_COLI_nKVE/dl", "Escherichia coli", "n/dl", "Aantal", "BACT", "chem"),
    ("BZV5a_mgO2/l", "Biochemisch zuurstofverbruik met ATU", "mg/l", "Concentratie mg/l", "REST", "chem"),
    ("atzne_ug/l", "Atrazine (ug/l)", "ug/l", "Concentratie ug/l", "BEST", "chem"),
    ("carbmzpne_ug/l", "carbamazepine (ug/l)", "ug/l", "Concentratie ug/l", "MEDICIJN", "chem"),
    ("metpll_ug/l", "metoprolol (ug/l)", "ug/l", "Concentratie ug/l", "MEDICIJN", "chem"),
    ("PFOS_ug/l", "Perfluoroctaansulfonaat", "ug/l", "Concentratie ug/l", "REST", "chem"),
    ("FRD-903_ng/l", None, None, None, None, "chem"),            # PFAS code without dictionary entry
    ("PTN_BEDKG_%", "Plantenbedekking (%)", "%", "Percentage", "HYBIO", "bio"),
    ("MEA_n", "Macro-evertebraten (n)", "n", "Aantal", "HYBIO", "bio"),
    ("VSLC_n", "Vissen per lengteklasse in cm (n)", "n", "Aantal", "HYBIO", "bio"),
    ("FPA_ncel/ml", "Fytoplankton (cellen/ml)", "n/ml", "Aantal n/ml", "HYBIO", "bio"),
    ("ZICHT_m", "Doorzicht (m)", "m", "Lengte", "VELD", "bio"),
    ("WATDTE_m", "Waterdiepte (m)", "m", "Lengte", "MONSVAR", "bio"),
]
TIER1 = [p for p in PARAMS if p[4] in ("NUTRI", "VELD", "ALG", "IONEN") and p[5] == "chem"]


def amstel_line() -> LineString:
    path = repo_path(load_settings()["amstel"]["centreline_rd"])
    if path.exists():
        return gpd.read_file(path).geometry.iloc[0]
    # fallback: straight synthetic river roughly from Amstelhoek to Amsterdam (RD metres)
    return LineString([(116900, 472600), (121400, 486700)])


def offset_point(line: LineString, chainage: float, offset: float) -> Point:
    """Point at ``chainage`` along the line, shifted ``offset`` metres perpendicular to it."""
    a, b = line.interpolate(max(chainage - 5, 0)), line.interpolate(min(chainage + 5, line.length))
    dx, dy = b.x - a.x, b.y - a.y
    n = np.hypot(dx, dy) or 1.0
    p = line.interpolate(chainage)
    return Point(p.x - dy / n * offset, p.y + dx / n * offset)


def make_stations(line: LineString) -> gpd.GeoDataFrame:
    rows = []
    for i, ch in enumerate(np.sort(RNG.uniform(0, line.length, 44))):
        off = RNG.choice([-1, 1]) * RNG.uniform(0, 110)
        kind = RNG.choice(["chem", "bio", "both"], p=[0.25, 0.55, 0.2])
        rows.append((f"SYN{i + 1:03d}", kind, offset_point(line, ch, off)))
    for j in range(36):                                   # context stations outside the corridor
        ch, off = RNG.uniform(0, line.length), RNG.choice([-1, 1]) * RNG.uniform(300, 6000)
        kind = RNG.choice(["chem", "bio", "both"], p=[0.3, 0.5, 0.2])
        rows.append((f"SYN{100 + j:03d}", kind, offset_point(line, ch, off)))
    g = gpd.GeoDataFrame({"station_id": [r[0] for r in rows], "kind": [r[1] for r in rows]},
                         geometry=[r[2] for r in rows], crs="EPSG:28992")
    g["is_chem"] = g.kind.isin(["chem", "both"])
    g["is_bio"] = g.kind.isin(["bio", "both"])
    # raw biology: one corridor station at ~63 m (mirrors reality: VGD125) and three context stations
    corridor_bio = g[g.is_bio & (g.station_id < "SYN100")].index
    pick = corridor_bio[len(corridor_bio) // 2]
    g.loc[pick, "geometry"] = offset_point(line, line.project(g.loc[pick, "geometry"]), 63)
    raw = [pick] + list(g[g.is_bio & (g.station_id >= "SYN100")].index[:3])
    g["has_raw_bio"] = g.index.isin(raw)
    g["krw_watertype"] = np.where(g.has_raw_bio, "M7b", None)
    g["eag"] = np.where(g.has_raw_bio, "SYN-EAG-1", None)
    g["krw_waterbody"] = np.where(g.has_raw_bio, "SYN_WB_1", None)
    return g.drop(columns="kind")


def make_coverage(st: gpd.GeoDataFrame, line: LineString) -> pd.DataFrame:
    rows = []
    for sid, is_chem, is_bio, geom in zip(st.station_id, st.is_chem, st.is_bio, st.geometry):
        ch = line.project(geom)
        for code, name, unit, grp, cat, src in PARAMS:
            if (src == "chem" and not is_chem) or (src == "bio" and not is_bio):
                continue
            if cat == "MEDICIJN" or code in ("PFOS_ug/l", "FRD-903_ng/l"):
                # sparse tracers only at the two river ends (mirrors reality: km 0.75 and km 21.2)
                if not (geom.distance(line) <= 100 and (ch < 1500 or ch > line.length - 1500)):
                    continue
                n = int(RNG.integers(4, 40))
            elif (code, name, unit, grp, cat, src) in TIER1:
                n = int(RNG.integers(5, 400)) if RNG.random() > 0.08 else 0
            else:
                n = int(RNG.integers(1, 200)) if RNG.random() > 0.45 else 0
            if n:
                rows.append((sid, src, code, n, name, unit, grp, cat))
    return pd.DataFrame(rows, columns=["station_id", "source", "parameter", "n_observations", "NAME", "UNIT",
                                       "GROUP", "category"])


def make_bio_values(st: gpd.GeoDataFrame) -> tuple[pd.DataFrame, list[dict]]:
    rows, rejected = [], []
    taxa = {"PTN_BEDKG_%": [("SYN plant A", "Macrophytes"), ("SYN plant B", "Macrophytes")],
            "MEA_n": [("SYN invertebrate A", "Macroinvertebrates")],
            "VSLC_n": [("SYN fish A", "Fish")]}
    units = {"PTN_BEDKG_%": "%", "MEA_n": "n", "VSLC_n": "n"}
    k = 0
    for sid in st.loc[st.has_raw_bio, "station_id"]:
        years = sorted(RNG.choice(np.arange(2006, 2025), size=6, replace=False))
        for y in years:
            date = pd.Timestamp(f"{y}-{int(RNG.integers(6, 9)):02d}-{int(RNG.integers(1, 28)):02d}")
            k += 1
            for par, tl in taxa.items():
                for taxon, tgroup in tl:
                    v = float(RNG.gamma(2, 8 if par == "PTN_BEDKG_%" else 15))
                    limit = ">" if RNG.random() < 0.04 else None
                    q = int(RNG.choice([0, 0, 0, 0, 3, 9]))
                    qa = "out_of_range" if (par == "PTN_BEDKG_%" and v > 100) else None
                    if RNG.random() < 0.02:
                        rejected.append({"source_file": "HB_sampled50locations.csv", "station_id": sid,
                                         "parameter": par, "value": -999.0, "reason": "sentinel_-999"})
                        continue
                    rows.append((sid, f"SYNS{k:04d}", date, par, taxon, tgroup, round(v, 1), units[par],
                                 limit, q, qa))
    cols = ["station_id", "sample_id", "datetime", "parameter", "taxon", "taxon_group", "value", "unit",
            "limit_flag", "quality_code", "qa_flag"]
    return pd.DataFrame(rows, columns=cols), rejected


def make_hydrology() -> pd.DataFrame:
    parts = []
    for site, sensor, start, quants in [
        ("Amstelsluizen", "MPP00013_LIT054_1", "1993-07-01", ["level_mNAP"]),
        ("Berlagebrug", "MPP00976_LIT054_1", "2012-07-27", ["level_mNAP", "Q_m3_per_day"]),
    ]:
        dates = pd.date_range(start, "2025-05-07", freq="D")
        doy = dates.day_of_year.to_numpy()
        for q in quants:
            if q == "level_mNAP":
                v = -0.40 + 0.03 * np.sin(2 * np.pi * doy / 365) + RNG.normal(0, 0.02, len(dates))
            else:
                v = -300000 + 150000 * np.sin(2 * np.pi * doy / 365) + RNG.normal(0, 60000, len(dates))
            flag = np.array([None] * len(dates), dtype=object)
            idx = RNG.choice(len(dates), 4, replace=False)
            v[idx] = v[idx] * (8 if q == "Q_m3_per_day" else 3)
            flag[idx] = "outlier"
            parts.append(pd.DataFrame({"sensor_id": sensor if q == "level_mNAP" else "MPP00976_FIT001_Q",
                                       "site": site, "date": dates, "quantity": q, "value": v, "qa_flag": flag}))
    return pd.concat(parts, ignore_index=True)


# availability per plant mirrors the real NL.11 effluent files (2021-01-01 .. 2026-01-01)
AVAILABILITY = {
    "volume": ["NL.11.AM", "NL.11.HI", "NL.11.HO", "NL.11.HU", "NL.11.LO", "NL.11.RV", "NL.11.UI", "NL.11.WP"],
    "phosphate": ["NL.11.AW", "NL.11.BL", "NL.11.HU", "NL.11.WE"],
    "suspended_solids": ["NL.11.AM", "NL.11.BL", "NL.11.HI", "NL.11.HO", "NL.11.HU", "NL.11.LO", "NL.11.RV",
                         "NL.11.WE", "NL.11.WP"],
}
SPEC = {"volume": ("Volume", "Niet van toepassing", "m3", lambda n: RNG.gamma(9, 1500, n)),
        "phosphate": ("(massa)Concentratie", "fosfaat", "mg/l", lambda n: RNG.gamma(2, 0.25, n)),
        "suspended_solids": ("(massa)Concentratie", "Onopgeloste bestandsdelen", "mg/l",
                             lambda n: RNG.gamma(2, 1.3, n))}


def make_effluent(names: dict[str, str]) -> pd.DataFrame:
    dates = pd.date_range("2021-01-01", "2025-12-31", freq="D")
    parts = []
    for metric, plants in AVAILABILITY.items():
        q, p, u, gen = SPEC[metric]
        for inst in plants:
            d = dates[RNG.random(len(dates)) > 0.03]              # a few missing days
            parts.append(pd.DataFrame({"installation": inst, "installation_name": names.get(inst, inst),
                                       "measurement_point": f"SYN.{inst}.{metric}", "date": d,
                                       "product": "Effluent", "quantity": q, "parameter": p, "unit": u,
                                       "value": gen(len(d))}))
    # a pulse-volume series that must NOT be read as flow
    d = dates
    parts.append(pd.DataFrame({"installation": "NL.11.UI", "installation_name": names["NL.11.UI"],
                               "measurement_point": "SYN.NL.11.UI.puls", "date": d, "product": "Effluent",
                               "quantity": "Volume", "parameter": "Pulsvolume", "unit": "m3/p", "value": 70.0}))
    return pd.concat(parts, ignore_index=True)


def main(out_dir: str = "tests/fixtures/processed") -> None:
    out = repo_path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    s = load_settings()
    line = amstel_line()

    st = make_stations(line)
    cov = make_coverage(st, line)
    n = cov.groupby(["station_id", "source"])["n_observations"].sum().unstack(fill_value=0)
    st["n_chem_obs"] = st.station_id.map(n.get("chem", pd.Series(dtype=int))).fillna(0).astype(int)
    st["n_bio_obs"] = st.station_id.map(n.get("bio", pd.Series(dtype=int))).fillna(0).astype(int)
    st["n_parameters"] = st.station_id.map(cov.groupby("station_id").parameter.nunique()).fillna(0).astype(int)
    st.to_parquet(out / "stations.parquet")
    cov.to_parquet(out / "coverage.parquet", index=False)

    loc = pd.DataFrame({"station_id": st.station_id, "is_chem": st.is_chem, "is_bio": st.is_bio,
                        "distance_to_river_m": st.distance(line), "chainage_m": st.geometry.apply(line.project)})
    tol = s["amstel"]["end_tolerance_m"]
    loc["beyond_river_end"] = (loc.chainage_m <= tol) | (loc.chainage_m >= line.length - tol)
    loc = loc[loc.distance_to_river_m <= s["amstel"]["max_distance_m"]]
    loc.sort_values(["chainage_m", "station_id"]).to_parquet(out / "amstel_stations.parquet", index=False)

    bio, rejected = make_bio_values(st)
    bio.to_parquet(out / "bio_values.parquet", index=False)
    hyd = make_hydrology()
    hyd.to_parquet(out / "hydrology.parquet", index=False)
    names = dict(pd.read_csv(repo_path(s["pressures"]["rwzi_locations"]))[["installation", "name"]].values)
    eff = make_effluent(names)
    eff.to_parquet(out / "rwzi_effluent.parquet", index=False)
    rej = pd.DataFrame(rejected + [{"source_file": "Berlagebrug_debiet_waterhoogte.csv", "station_id": None,
                                    "parameter": "Q_m3_per_day", "value": None, "reason": "unparseable_date"}])
    rej.to_parquet(out / "rejected_values.parquet", index=False)

    manifest = {
        "synthetic": True,
        "run_at": datetime.now().isoformat(timespec="seconds"),
        "generator": "scripts/make_ui_fixtures.py (seed 20261028)",
        "inputs": {"amstel_centreline": str(s["amstel"]["centreline_rd"]),
                   "rwzi_locations": str(s["pressures"]["rwzi_locations"])},
        "outputs": {
            "stations.parquet": {"rows_out": len(st)},
            "coverage.parquet": {"rows_out": len(cov)},
            "amstel_stations.parquet": {"rows_out": len(loc)},
            "bio_values.parquet": {"rows_in": len(bio) + len(rejected), "rows_out": len(bio),
                                   "rejected": {"sentinel_-999": len(rejected)}},
            "hydrology.parquet": {"rows_in": len(hyd) + 1, "rows_out": len(hyd),
                                  "rejected": {"unparseable_date": 1}},
            "rwzi_effluent.parquet": {"rows_out": len(eff)},
        },
    }
    (out / "pipeline_manifest.json").write_text(json.dumps(manifest, indent=2))
    print(f"fixtures -> {out}: stations={len(st)} corridor={len(loc)} coverage={len(cov)} bio={len(bio)} "
          f"hydrology={len(hyd)} effluent={len(eff)}")


if __name__ == "__main__":
    main(*sys.argv[1:2])
