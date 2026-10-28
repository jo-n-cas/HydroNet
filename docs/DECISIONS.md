# Decisions log

Assumptions and deviations, newest first. Format: date, decision, reason.

## 2026-10-28: Amstel selection rule is 100 m

- **Decision:** the pipeline keeps all data from every location within 100 m of the Amstel centreline: 76 locations (26 chemistry, 61 biology, 11 in both). The procedure is in `docs/AMSTEL_STATION_SELECTION.md`. The UI default buffer is also 100 m, with 25 / 50 m as sensitivity views. This supersedes the earlier 50 m default below.
- **Reason:** team decision (user, 2026-10-28).
- **Flagged for review, not dropped:**
  - `KMU103` lies beyond the upstream end, on the Kromme Mijdrecht.
  - The 70–100 m non-AMS locations `UHP001, PEB001, MPA130, PRH145, PRH146, PRH151, NLP150` may be in adjacent polder waters.
  - Decisions on these go in `config/amstel_overrides.csv`.

## 2026-10-28: Spatial focus on the Amstel river only

- **Decision:** the UI is scoped to the Amstel corridor. AGV-wide numbers are context only. A chainage (km) range slider replaces free-form map area selection.
- **Reason:** team decision (user, 2026-10-28). It narrows instructions Sections 1 and 6, which were updated accordingly.

## 2026-10-28: Amstel centreline from OpenStreetMap

- **Source:** OpenStreetMap, © OpenStreetMap contributors, licensed under ODbL 1.0. Downloaded 2026-10-28, with user approval.
  - Relation `12882829` (`waterway=river`, `name=Amstel`, version 12, last edited 2024-11-17), fetched from `https://www.openstreetmap.org/api/0.6/relation/12882829/full` and saved as `data/external/amstel_relation_12882829_full.osm`. The team's `amstel_river_loc.xml` holds the same relation but without the way and node geometry, so it cannot be used on its own.
  - Way `96361977` (Amstelhoek → Nes aan de Amstel), fetched with an Overpass query over bbox 52.225–52.256 N, 4.81–4.875 E (`overpass-api.de`) and saved as `data/external/uithoorn_waterways_overpass.json`.
- **Build:** `scripts/build_amstel_line.py data/external/amstel_relation_12882829_full.osm data/external/amstel.geojson --extra data/external/uithoorn_waterways_overpass.json --extra-way 96361977`.
- **Decision 1, include way 96361977:** the instructions define the Amstel as starting at the Drecht / Kromme Mijdrecht confluence (Amstelhoek). OSM names this 4.5 km stretch "Amstel-Drechtkanaal" and starts the Amstel relation at the Oude Waver junction near Nes aan de Amstel. Without this stretch, the Uithoorn reach, where the RWZI Uithoorn is located, would be missing.
- **Decision 2, parallel channels:** at the Amstelsluizen (around 52.362 N, 4.903 E) the OSM river splits into 4 parallel lock and canal channels of 137–149 m. The shortest is kept, so the centreline is a single line. The effect on chainage is under 15 m.
- **Result:** one line of 22.0 km, from 52.2288 N, 4.8207 E (Amstelhoek) to 52.3674 N, 4.8940 E (Binnen-Amstel, Amsterdam centre). It is oriented upstream → downstream (south → north).
- **Buffer sensitivity** (real FYCHEM and HB inventories, RD coordinates): 30 locations at 25 m (12 chemistry, 24 biology), 58 at 50 m (21 / 47), and 76 at 100 m (26 / 61). Some locations appear in both inventories. The default stays at 50 m because many river stations lie 20–45 m from the centreline (the river is wide, and samples are taken near the banks).
- **Code prefix not used:** most corridor stations are `AMS…`, but AMS186 lies on the Ringvaart, and the corridor also contains KMU, UHP, PEB, GWV, NLP, PRH, VGD, MPA and ADM codes.
- **Raw biology on the Amstel:** only 1 of the 50 raw-biology locations is within 100 m (VGD125, 63 m from the centreline, km 12.3). None are within 50 m. The UI states this explicitly rather than borrowing biology from further away.

## 2026-10-28: UI dependencies

- **Decision:** the UI dependencies are installed in a project virtualenv `.venv` (Python 3.13.5): streamlit 1.66.1, folium 0.20.0, streamlit-folium, plotly, geopandas 1.2.0, shapely, pyproj, pyarrow, pyyaml, pytest. `.venv/` is git-ignored.
- **Reason:** approved by the user. The system Python did not have them.
