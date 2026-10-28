"""Build the Amstel centreline from OpenStreetMap exports.

Inputs:
- the `/relation/12882829/full` OSM XML of the Amstel (ways and nodes included);
- optionally an Overpass JSON export (`out geom`) holding extra ways to prepend,
  selected by way ID. Used for the Amstelhoek -> Nes aan de Amstel stretch, which
  OSM names "Amstel-Drechtkanaal" (way 96361977) and leaves out of the relation.

Steps: merge the ways into one line; where the river splits into parallel channels
(the lock complex at the Amstelsluizen), keep the shortest channel; orient the line
upstream (Amstelhoek) to downstream (Amsterdam centre); write GeoJSON in EPSG:4326
and EPSG:28992 (RD New), plus a per-segment file recording which way IDs were used.

Usage:
    python scripts/build_amstel_line.py RELATION_FULL.osm OUT.geojson \
        [--extra OVERPASS.json --extra-way 96361977]
"""

from __future__ import annotations

import argparse
import json
import xml.etree.ElementTree as ET
from pathlib import Path

import geopandas as gpd
from shapely.geometry import LineString, MultiLineString
from shapely.ops import linemerge


def read_relation(osm_path: Path) -> tuple[list[tuple[str, LineString]], dict]:
    """Return (way_id, line) for the relation's main_stream ways, and relation metadata."""
    root = ET.parse(osm_path).getroot()
    nodes = {n.get("id"): (float(n.get("lon")), float(n.get("lat"))) for n in root.iter("node")}
    ways = {w.get("id"): [nd.get("ref") for nd in w.iter("nd")] for w in root.iter("way")}
    rel = root.find("relation")
    tags = {t.get("k"): t.get("v") for t in rel.iter("tag")}
    lines = [
        (m.get("ref"), LineString([nodes[r] for r in ways[m.get("ref")]]))
        for m in rel.iter("member")
        if m.get("type") == "way" and m.get("role") in ("main_stream", "")
    ]
    meta = {"relation_id": rel.get("id"), "version": rel.get("version"),
            "timestamp": rel.get("timestamp"), **tags}
    return lines, meta


def read_overpass_ways(path: Path, way_ids: list[str]) -> list[tuple[str, LineString, str]]:
    """Return (way_id, line, name) for the requested ways in an Overpass `out geom` export."""
    elements = json.loads(path.read_text())["elements"]
    found = {
        str(e["id"]): (LineString([(p["lon"], p["lat"]) for p in e["geometry"]]),
                       e.get("tags", {}).get("name", ""))
        for e in elements if e["type"] == "way"
    }
    missing = [w for w in way_ids if w not in found]
    if missing:
        raise ValueError(f"Ways not in Overpass export: {missing}")
    return [(w, *found[w]) for w in way_ids]


def drop_parallel_channels(parts: list[LineString]) -> list[LineString]:
    """Where several parts connect the same two endpoints, keep only the shortest."""
    best: dict[frozenset, LineString] = {}
    for p in parts:
        key = frozenset({tuple(p.coords[0]), tuple(p.coords[-1])})
        if key not in best or p.length < best[key].length:
            best[key] = p
    return list(best.values())


def merge_to_single_line(lines: list[LineString]) -> LineString:
    """Merge to one line, resolving parallel channels; fail loudly on gaps or forks."""
    merged = linemerge(MultiLineString(lines))
    for _ in range(5):
        if merged.geom_type == "LineString":
            return merged
        merged = linemerge(MultiLineString(drop_parallel_channels(list(merged.geoms))))
    raise ValueError(f"River does not merge into one line: {len(merged.geoms)} parts remain")


def orient_downstream_north(line: LineString) -> LineString:
    """Amsterdam centre lies north of Amstelhoek: make the line run south -> north."""
    if line.coords[-1][1] < line.coords[0][1]:
        return LineString(list(line.coords)[::-1])
    return line


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("relation_osm")
    ap.add_argument("out_geojson")
    ap.add_argument("--extra", help="Overpass JSON export with extra ways")
    ap.add_argument("--extra-way", action="append", default=[], help="way ID to add from --extra")
    a = ap.parse_args()

    rel_lines, meta = read_relation(Path(a.relation_osm))
    segments = [{"way_id": w, "name": "Amstel", "in_osm_relation": True, "geometry": g}
                for w, g in rel_lines]
    if a.extra_way:
        for w, g, name in read_overpass_ways(Path(a.extra), a.extra_way):
            segments.append({"way_id": w, "name": name, "in_osm_relation": False, "geometry": g})

    line = orient_downstream_north(merge_to_single_line([s["geometry"] for s in segments]))
    source = "© OpenStreetMap contributors, ODbL 1.0"
    gdf = gpd.GeoDataFrame(
        [{"name": "Amstel", "osm_relation": meta["relation_id"], "osm_version": meta["version"],
          "osm_timestamp": meta["timestamp"], "extra_ways": ",".join(a.extra_way),
          "orientation": "upstream_to_downstream", "source": source}],
        geometry=[line], crs="EPSG:4326",
    )
    out = Path(a.out_geojson)
    gdf.to_file(out, driver="GeoJSON")
    gdf.to_crs("EPSG:28992").to_file(out.with_name(out.stem + "_rd.geojson"), driver="GeoJSON")
    gpd.GeoDataFrame(segments, crs="EPSG:4326").assign(source=source).to_file(
        out.with_name(out.stem + "_segments.geojson"), driver="GeoJSON")

    length = gdf.to_crs("EPSG:28992").length.iloc[0]
    print(f"ways={len(segments)} length_m={length:.0f} "
          f"start(lon,lat)={line.coords[0]} end(lon,lat)={line.coords[-1]} -> {out}")


if __name__ == "__main__":
    main()
