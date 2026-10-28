"""Export all records for the documented 100 m Amstel station selection."""

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data/internal"
OUT = ROOT / "amstel_subset"


def main():
    # shortcut: uses the verified station list, recompute it if the line or 100 m rule changes.
    selection = (ROOT / "docs/AMSTEL_STATION_SELECTION.md").read_text(encoding="utf-8")
    block = selection.split("The 76 locations, upstream → downstream:", 1)[1].split("```", 2)[1]
    ids = [code.strip() for code in block.replace("\n", "").split(",")]
    if len(ids) != 76 or len(set(ids)) != len(ids):
        raise ValueError("Expected 76 distinct stations in the documented Amstel selection")

    stations = {}
    OUT.mkdir(exist_ok=True)
    for source, filename in (
        ("chem", "FYCHEM_unique_locations_with_measurements.geojson"),
        ("bio", "HB_unique_locations_with_measurements.geojson"),
    ):
        data = json.loads((DATA / filename).read_text(encoding="utf-8"))
        data["features"] = [f for f in data["features"] if f["properties"]["locatiecode"] in ids]
        for feature in data["features"]:
            p = feature["properties"]
            code = p["locatiecode"]
            point = (p["rd_x_original"], p["rd_y_original"])
            station = stations.setdefault(code, {"point": point, "sources": set(), "chem_obs": 0, "bio_obs": 0})
            if station["point"] != point:
                raise ValueError(f"Conflicting coordinates for {code}")
            station["sources"].add(source)
            station[f"{source}_obs"] = p["total_observations"]
        (OUT / filename).write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    if set(stations) != set(ids):
        raise ValueError(f"Selected stations missing from inventories: {set(ids) - set(stations)}")
    with (OUT / "stations.csv").open("w", encoding="utf-8", newline="") as target:
        writer = csv.writer(target)
        writer.writerow(["station_id", "river_order", "is_chem", "is_bio", "rd_x", "rd_y", "n_chem_obs", "n_bio_obs", "beyond_river_end"])
        for order, code in enumerate(ids, 1):
            station = stations[code]
            writer.writerow([code, order, "chem" in station["sources"], "bio" in station["sources"],
                             *station["point"], station["chem_obs"], station["bio_obs"], code == "KMU103"])

    with (DATA / "HB_sampled50locations.csv").open(encoding="utf-8-sig", newline="") as source, \
            (OUT / "HB_sampled50locations.csv").open("w", encoding="utf-8", newline="") as target:
        reader = csv.DictReader(source, delimiter=";")
        writer = csv.DictWriter(target, fieldnames=reader.fieldnames, delimiter=";")
        writer.writeheader()
        rows = [row for row in reader if row["locatiecode"] in ids]
        writer.writerows(rows)

    if (sum("chem" in s["sources"] for s in stations.values()),
            sum("bio" in s["sources"] for s in stations.values()),
            {row["locatiecode"] for row in rows}) != (26, 61, {"VGD125"}):
        raise ValueError("Export does not match documented 100 m selection")
    print(f"Exported {len(ids)} stations and {len(rows)} raw biology rows to {OUT}")


if __name__ == "__main__":
    main()
