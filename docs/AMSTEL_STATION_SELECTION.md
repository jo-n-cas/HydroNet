# How to select the Amstel measurement locations (for the data-cleaning pipeline)

**Rule (team decision, 2026-10-28):** a measurement location belongs to the Amstel dataset if it lies **within 100 m of the Amstel centreline**. Keep every data point from those locations.

This document says exactly how to apply that rule, so that the pipeline and the UI select the same locations. Expected results are at the bottom: check your output against them.

---

## 1. Inputs

| What | File | Notes |
|---|---|---|
| Amstel centreline (RD New, metres) | `data/external/amstel_rd.geojson` | Built by `scripts/build_amstel_line.py` (command below). One LineString, 22.0 km, running **upstream → downstream** (Amstelhoek → Binnen-Amstel, Amsterdam). Do not edit by hand. |
| Chemistry locations | `FYCHEM_unique_locations_with_measurements.geojson` | 1,321 locations |
| Biology locations | `HB_unique_locations_with_measurements.geojson` | 4,093 locations |
| Raw biology rows | `HB_sampled50locations.csv` | 50 locations; `;` separated |

Build the line once (the `*.geojson` output is git-ignored, so everyone builds it locally):

```bash
python scripts/build_amstel_line.py data/external/amstel_relation_12882829_full.osm \
    data/external/amstel.geojson \
    --extra data/external/uithoorn_waterways_overpass.json --extra-way 96361977
# expected: ways=40 length_m=22021 ...
```

## 2. Rules

1. **Measure in metres, in RD New (EPSG:28992).** Never compute distances in longitude/latitude (degrees).
   - GeoJSON inventories: build the points from `rd_x_original`, `rd_y_original`. Do not use the WGS84 geometry.
   - `HB_sampled50locations.csv`: use the **location** coordinates `locatie x`, `locatie y`, not the sample coordinates `xcoormonster`, `ycoormonster`. The station is the unit of selection.
2. **Distance = shortest distance from the point to the centreline** (`point.distance(line)` in shapely / geopandas). Keep locations with `distance_to_river_m <= 100`. Use `<=`, so a location at exactly 100 m is included.
3. **Select locations, then keep all their data.** The decision is made per `locatiecode`. All measurements, samples and parameters of a selected location are kept, for any date. Do not filter individual rows by their own sample coordinates.
4. **Same code in both inventories = same location.** The 443 codes present in both FYCHEM and HB have identical coordinates (checked: difference 0 m), so a code is selected or not selected in both. Mark it `is_chem` and `is_bio`.
5. **Do not select by code prefix.** Most Amstel locations are `AMS…`, but `AMS186` lies on the Ringvaart, about 10 km away. The corridor also contains KMU, UHP, PEB, GWV, NLP, PRH, VGD, MPA and ADM codes.
6. **Chainage (position along the river):** `chainage_m = line.project(point)`, in metres from the upstream start. It is used for upstream → downstream ordering, which is indicative only.
7. **Flag, do not drop, the edge cases** (see Section 4). The team decides on them through `config/amstel_overrides.csv`, not in code.

## 3. Reference implementation

This was checked against the real files on 2026-10-28. Paths and the 100 m value should come from `config/settings.yaml` in the pipeline.

```python
import geopandas as gpd
import pandas as pd

MAX_DISTANCE_M = 100          # settings.yaml: amstel.max_distance_m
END_TOLERANCE_M = 1.0         # projection this close to a line end = beyond the river end

line = gpd.read_file("data/external/amstel_rd.geojson").geometry.iloc[0]

frames = []
for path, source in [("FYCHEM_unique_locations_with_measurements.geojson", "chem"),
                     ("HB_unique_locations_with_measurements.geojson", "bio")]:
    g = gpd.read_file(path)
    g = gpd.GeoDataFrame(
        g.drop(columns="geometry"),
        geometry=gpd.points_from_xy(g["rd_x_original"], g["rd_y_original"]),
        crs="EPSG:28992",
    )
    g["source"] = source
    frames.append(g[["locatiecode", "source", "total_observations", "geometry"]])
locs = pd.concat(frames, ignore_index=True)

locs["distance_to_river_m"] = locs.distance(line)
locs["chainage_m"] = locs.geometry.apply(line.project)

sel = locs[locs["distance_to_river_m"] <= MAX_DISTANCE_M]
amstel = (
    sel.groupby("locatiecode")
    .agg(is_chem=("source", lambda s: "chem" in set(s)),
         is_bio=("source", lambda s: "bio" in set(s)),
         distance_to_river_m=("distance_to_river_m", "min"),
         chainage_m=("chainage_m", "first"))
    .reset_index()
    .rename(columns={"locatiecode": "station_id"})
)
amstel["beyond_river_end"] = (amstel["chainage_m"] <= END_TOLERANCE_M) | (
    amstel["chainage_m"] >= line.length - END_TOLERANCE_M)
amstel = amstel.sort_values(["chainage_m", "station_id"])     # upstream -> downstream
amstel.to_parquet("data/processed/amstel_stations.parquet", index=False)

# Filtering the raw data afterwards: keep all rows of the selected stations
ids = set(amstel["station_id"])
# bio = bio[bio["station_id"].isin(ids)]   # same for any future FYCHEM value export
```

**Output schema** `data/processed/amstel_stations.parquet`: `station_id, is_chem, is_bio, distance_to_river_m, chainage_m, beyond_river_end`. This extends the instructions Section 5.4 schema with `is_chem`, `is_bio` and `beyond_river_end`. The UI filters this table further at 25 / 50 m, so do **not** pre-filter it below 100 m.

## 4. Edge cases to flag (not drop)

| Case | Locations (100 m) | What to do |
|---|---|---|
| Beyond the upstream end: the point projects onto the start of the line, so it is near the river's start point but not on the Amstel | `KMU103` (Kromme Mijdrecht, 72 m from the start point) | `beyond_river_end = True`. Proposed: exclude through `amstel_overrides.csv` with reason "on Kromme Mijdrecht, upstream of the Amstel". |
| Probably in adjacent polder waters, not in the river (70–100 m, non-AMS prefix) | `UHP001` (95 m), `PEB001` (92 m), `MPA130` (93 m), `PRH145` (70 m), `PRH146` (76 m), `PRH151` (80 m), `NLP150` (78 m) | Keep, and list them in the overrides file for review (`action: include`, `reason: "70–100 m, check whether in river or polder"`). Check on a map before excluding. |

Overrides file format: `config/amstel_overrides.csv` with columns `station_id, action (include|exclude), reason`. Apply it after the distance rule and log every override in `docs/DECISIONS.md`.

## 5. Expected results (check your output)

With the line built as above and `MAX_DISTANCE_M = 100`:

- 87 inventory records → **76 unique locations**: 26 chemistry, 61 biology, 11 in both.
- For comparison, the UI's sensitivity panel shows 30 locations at 25 m and 58 at 50 m.
- Raw biology (`HB_sampled50locations.csv`): **1 of 50 locations** is selected: `VGD125` (63 m, chainage ≈ 12.3 km). So the raw-biology subset for the Amstel is the `VGD125` rows only.
- First and last by chainage: `KMU103` (0 m, beyond the upstream end), `AMS148`, `UHP001` … `ADM142`, `ADM077`, `ADM023` (≈ 21.9 km).

The 76 locations, upstream → downstream:

```
KMU103, AMS148, UHP001, AMS112, AMS159, AMS030, AMS003, AMS115, AMS145, GWV507,
AMS105, NLP150, PEB001, AMS125, AMS102, AMS124, AMS149, AMS111, AMS021, AMS123,
AMS016, PRH145, AMS127, PRH146, AMS152, AMS151, AMS005, AMS031, AMS110, AMS126,
AMS106, AMS101, PRH151, AMS006, AMS128, AMS129, AMS109, AMS150, AMS130, AMS007,
AMS015, AMS008, VGD125, AMS131, MPA130, AMS107, VGD158, AMS132, VGD121, VGD037,
AMS009, AMS032, AMS153, VGD108, AMS108, AMS160, AMS103, AMS014, VGD028, VGD103,
AMS133, AMS033, AMS010, AMS012, ADM101, AMS022, AMS134, AMS011, AMS024, ADM138,
ADM133, ADM112, ADM016, ADM142, ADM077, ADM023
```

## 6. Not selected by distance

- **RWZIs (wastewater plants):** the RWZI files have no coordinates. Their link to the Amstel is handled in `pressures.py` (instructions Section 5.5), not by this rule.
- **Hydrology sensors (Amstelsluizen, Berlagebrug):** these are Amstel sensors by definition. Keep both series entirely.

## 7. Suggested tests

- A point 99.9 m from a synthetic line is selected, and one at 100.1 m is not.
- A code present in both inventories gives one row with `is_chem` and `is_bio` both true.
- A point beyond a line end gets `beyond_river_end = True`.
- Chainage is monotone for points placed along a synthetic line.
- The real-data smoke test returns 76 locations, including `VGD125`.
