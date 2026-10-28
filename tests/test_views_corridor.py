import geopandas as gpd
import pandas as pd
from shapely.geometry import LineString, Point

from hydronet.views import corridor

LINE = LineString([(0, 0), (1000, 0)])   # synthetic straight river, metres


def _stations():
    # station_id, x, y  -> distance |y|, chainage x
    pts = [("S1", 100, 10), ("S2", 300, -40), ("S3", 300, 60), ("S4", 700, 99.9), ("S5", 900, 100.1),
           ("S0", -50, 0)]
    g = gpd.GeoDataFrame({"station_id": [p[0] for p in pts]},
                         geometry=[Point(p[1], p[2]) for p in pts], crs="EPSG:28992")
    loc = corridor.locate_on_line(LINE, g.geometry)
    return pd.concat([g[["station_id"]], loc], axis=1).assign(is_chem=True, is_bio=False)


def test_locate_on_line_distance_and_chainage():
    df = _stations().set_index("station_id")
    assert round(df.loc["S2", "distance_to_river_m"], 6) == 40
    assert df.loc["S2", "chainage_m"] == 300
    assert df.loc["S0", "chainage_m"] == 0          # beyond the upstream end projects to 0
    assert df.loc["S0", "distance_to_river_m"] == 50


def test_corridor_selection_boundary_and_ordering():
    sel = corridor.corridor_stations(_stations(), 100)
    assert "S4" in set(sel.station_id) and "S5" not in set(sel.station_id)
    assert list(sel.chainage_m) == sorted(sel.chainage_m)
    # tie at chainage 300 is broken by station_id
    ties = sel[sel.chainage_m == 300].station_id.tolist()
    assert ties == sorted(ties)


def test_corridor_overrides_and_chainage_range():
    ov = pd.DataFrame({"station_id": ["S5", "S1"], "action": ["include", "exclude"], "reason": ["", ""]})
    sel = corridor.corridor_stations(_stations(), 100, overrides=ov)
    assert "S5" in set(sel.station_id) and "S1" not in set(sel.station_id)
    stretch = corridor.corridor_stations(_stations(), 100, chainage_range_m=(200, 800))
    assert set(stretch.station_id) == {"S2", "S3", "S4"}


def test_buffer_sensitivity_monotone_with_entering():
    s = corridor.buffer_sensitivity(_stations(), [100, 25, 50])
    assert list(s.buffer_m) == [25, 50, 100]
    assert list(s.n_stations) == sorted(s.n_stations)
    assert s.loc[0, "entering"] == ["S1"]
    assert s.loc[1, "entering"] == ["S0", "S2"]
    assert s.loc[2, "entering"] == ["S3", "S4"]


def test_proximity_links_within_buffer_only():
    st = gpd.GeoDataFrame(_stations()[["station_id"]],
                          geometry=[Point(100, 10), Point(300, -40), Point(300, 60), Point(700, 99.9),
                                    Point(900, 100.1), Point(-50, 0)], crs="EPSG:28992")
    plants = gpd.GeoDataFrame({"installation": ["P1", "P2"]}, geometry=[Point(100, 0), None], crs="EPSG:28992")
    links = corridor.proximity_links(plants, st, 60)
    assert links.station_id.tolist() == ["S1"]
    assert links.distance_m.iloc[0] == 10


def test_near_chainage_window_and_signed_offset():
    sel = corridor.corridor_stations(_stations(), 100)
    near = corridor.near_chainage(sel, 300, 250)
    assert set(near.station_id) == {"S1", "S2", "S3"}           # S0 (offset -300) and S4 (+400) fall outside
    assert near.set_index("station_id").loc["S1", "offset_m"] == -200    # upstream of reference
