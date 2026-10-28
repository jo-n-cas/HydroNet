"""Coverage table and merged station table (instructions 5.1-5.3)."""

from __future__ import annotations

import logging

import geopandas as gpd
import pandas as pd

log = logging.getLogger(__name__)


def build_coverage(inventories: dict[str, pd.DataFrame], dictionary: pd.DataFrame) -> tuple[pd.DataFrame, list[dict]]:
    """Long table ``station_id, source, parameter, n_observations`` joined to the dictionary.

    Unknown codes are kept with NAME = "NOT FOUND". Returns the table and a list of
    issues (locations whose counts do not sum to ``total_observations``).
    """
    rows, issues = [], []
    for source, inv in inventories.items():
        for sid, total, counts in zip(inv["station_id"], inv["total_observations"], inv["parameter_counts"]):
            if sum(counts.values()) != total:
                issues.append({"source_file": source, "station_id": sid, "parameter": None,
                               "value": float(total), "reason": "counts_do_not_sum_to_total"})
            rows += [(sid, source, code, n) for code, n in counts.items()]
    cov = pd.DataFrame(rows, columns=["station_id", "source", "parameter", "n_observations"])
    d = dictionary.drop_duplicates("ID").set_index("ID")
    cov["NAME"] = cov["parameter"].map(d["NAME"]).fillna("NOT FOUND")
    cov["UNIT"] = cov["parameter"].map(d["UNIT"])
    cov["GROUP"] = cov["parameter"].map(d["GROUP"])
    cov["category"] = cov["parameter"].map(d["P_categorie"])
    return cov, issues


def build_stations(inventories: dict[str, pd.DataFrame], coverage: pd.DataFrame,
                   hb_sample: pd.DataFrame) -> gpd.GeoDataFrame:
    """One row per station_id, geometry in EPSG:28992.

    The same code in both inventories is the same station (coordinates must agree).
    Water body attributes come from the raw biology sample and exist only for its locations.
    """
    parts = []
    for source, inv in inventories.items():
        parts.append(inv[["station_id", "x_rd", "y_rd"]].assign(source=source))
    allp = pd.concat(parts, ignore_index=True)
    coords = allp.groupby("station_id")[["x_rd", "y_rd"]].nunique()
    conflicting = coords[(coords > 1).any(axis=1)].index.tolist()
    if conflicting:
        raise ValueError(f"Codes with different coordinates in FYCHEM and HB: {conflicting[:10]}")
    st = allp.groupby("station_id").agg(x_rd=("x_rd", "first"), y_rd=("y_rd", "first"),
                                        is_chem=("source", lambda s: "chem" in set(s)),
                                        is_bio=("source", lambda s: "bio" in set(s))).reset_index()
    n = coverage.groupby(["station_id", "source"])["n_observations"].sum().unstack(fill_value=0)
    st["n_chem_obs"] = st["station_id"].map(n.get("chem", pd.Series(dtype=int))).fillna(0).astype(int)
    st["n_bio_obs"] = st["station_id"].map(n.get("bio", pd.Series(dtype=int))).fillna(0).astype(int)
    st["n_parameters"] = st["station_id"].map(coverage.groupby("station_id")["parameter"].nunique()).fillna(0).astype(int)

    attrs = (hb_sample.groupby("locatiecode")
             .agg(krw_watertype=("locatie KRW watertype", "first"), eag=("locatie EAG", "first"),
                  krw_waterbody=("locatie KRWmeetpuntlocatie", "first")))
    st["has_raw_bio"] = st["station_id"].isin(attrs.index)
    for c in ["krw_watertype", "eag", "krw_waterbody"]:
        st[c] = st["station_id"].map(attrs[c])

    dup = st[st.duplicated(["x_rd", "y_rd"], keep=False)]
    if len(dup):
        log.info("%d distinct codes share coordinates with another code (kept separate)", len(dup))
    geom = gpd.points_from_xy(st["x_rd"], st["y_rd"])
    return gpd.GeoDataFrame(st.drop(columns=["x_rd", "y_rd"]), geometry=geom, crs="EPSG:28992")
