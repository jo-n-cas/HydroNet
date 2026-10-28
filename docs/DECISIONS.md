# Decisions log

Assumptions and deviations, newest first. Format: date, decision, reason.

<<<<<<< Updated upstream
## 2026-10-28: Cleaning pipeline and switch of the UI to real data

- **Pipeline:** `python -m hydronet.pipeline` (with `src` on `PYTHONPATH`) rebuilds `data/processed/` in about 12 s, including a streamed scan of the 28.7 M-row `MeasurementValues.csv`. `--skip-rwzi` re-uses the cached extract `data/interim/rwzi_values_nl11.parquet`.
- **UI data source:** `ui.data_dir` is now `data/processed` (real). Tests force the fixtures with `HYDRONET_DATA_DIR=tests/fixtures/processed`.
- **Raw file lookup:** `paths.raw_dirs: [data/raw, data/internal, .]`, first match per file. The colleagues' scripts use `data/internal/`; locally the files sit in the repo root. Raw files are never modified.
- **Checks recorded in the manifest** (all as documented):
  - 4,971 stations (4,093 + 1,321 − 443 shared codes); 0 inventory count mismatches; 35 codes not in the dictionary.
  - 76 Amstel locations (26 chemistry, 61 biology); raw biology only at VGD125.
  - 6 sentinels (−999) rejected from 13,340 biology rows.
  - 1,333,435 AGV RWZI rows, of which 72,698 are effluent.
  - 123 distinct codes share coordinates with another code; they are kept separate and logged.
- **Biology flags:**
  - Dictionary bounds (`H_MIN`/`Z_MIN`, `H_MAX`/`Z_MAX`, widest available) only *flag* values (`out_of_range`).
  - Limit symbols and quality codes are kept unchanged; values are not substituted.
  - `taxon_group` = `TWN taxontype`; `krw_waterbody` = `locatie KRWmeetpuntlocatie`.
- **Hydrology codes found in the real files** (flagged, never removed; `config/settings.yaml` → `hydrology_suspect_values`):
  - Berlagebrug water level **−32.768 m** on 15 days. This is an int16 "no data" code, flagged `sentinel_-32.768`.
  - Berlagebrug Q **−28,300,000 m³/day** on exactly 185 days (2013–2019), with more days just below it. This is probably a sensor ceiling, flagged `repeated_extreme_value`.
  - The remaining extremes are flagged `outlier_robust` (median ± 6 robust SD, computed without the code values): 13 at Amstelsluizen, 125 for the Berlagebrug level and 112 for Berlagebrug Q.
  - Plots scale to the unflagged values; flagged values beyond that range are drawn at the panel edge (▲▼), and the hover shows the true value.
- **Observation, not interpreted:** Berlagebrug Q is almost flat near 0 from about late 2022 onward, which looks like a sensor or method change. To be checked with AGV.
- **RWZI partial years:** the effluent files end on 2026-01-01, so "2026" is one day. Years with fewer than 300 days are drawn hollow and not connected.
- **Biology on the Amstel:** VGD125 was sampled once, on 2005-08-09 (44 rows). It has no values in the 2021–2024 overlap with the RWZI data; the phosphorus chain states this.
=======
## 2026-10-28: First chemical detection reach model

- **User scenario:** treat each positive inventory count as assumed chemical presence. This is displayed explicitly on the detection page; unmeasured stations are not treated as negative. Because there is no confirmed low station, this mode cannot locate an entry reach or learn transport.
- **Second map:** selecting the same chemical shows a hypothetical south-to-north route between recorded stations. Line width and station size represent observation counts, not concentration. A hollow circle marks the first assumed presence; diamonds mark reaches between successive recorded stations where counts rise. A dashed segment continues beyond the last record. Count rises can reflect sampling effort, so these are candidate entry reaches, not inferred discharges or sources. The map does not establish a shared event or travel time.
- **Scope:** chloride (`Cl_mg/l`), ammonium (`NH4_mgN/l_nf`) and total phosphorus (`Ptot_mgP/l`), the three most frequent pollutant-related concentration parameters by aggregate observation count at the selected Amstel chemistry stations (3,696 / 3,550 / 3,525). Temperature, oxygen and conductivity are excluded because they are context measurements rather than pollutants.
- **Map selection:** the overview control switches between assumed chemical locations and a hypothetical downstream route. Inventory counts never stand in for concentrations.
- **Limit:** changing flow direction, side channels and mixed water bodies can invalidate the route. Raw chemistry values, confirmed negative stations and verified local flow are unavailable in the current files.
>>>>>>> Stashed changes

## 2026-10-28: UI build decisions (branch `ui`)

- **Map library:** folium with streamlit-folium.
  - It gives point markers with distinct shapes, clean click-to-select via tooltips, and needs no arrows or animation (flow arrows are out of scope).
  - **Base map:** OpenStreetMap tiles, shown in greyscale and faded with CSS so the data carry the colour. CARTO tiles now need an API key, so they are not used.
- **Pages folder renamed `app/views/`:** a folder named `pages/` next to the entry script switches Streamlit to its legacy multipage mode, which skips the entry script (sidebar and shared context) when a page URL is opened directly.
- **Contract extension:** `coverage.parquet` gets a `category` column (dictionary `P_categorie`), which the parameter-group rules need.
  - The full contract is in `src/hydronet/schemas.py`.
  - `amstel_stations.parquet` adds `is_chem`, `is_bio` and `beyond_river_end`.
  - `rejected_values.parquet` uses `source_file, station_id, parameter, value, reason`.
- **Shared logic:** `hydronet.groups.assign_group` is shared code, so the pipeline and the UI group parameters identically.
- **Effluent metrics:** matched on quantity + parameter + unit (`config/settings.yaml`). The real files show three things:
  - "Pulsvolume" (m³/p) is a pulse size, not a flow, so it is not used as volume.
  - `11.AWwlBI.mi-001.PO4` is a research line and is excluded.
  - Effluent `fosfaat` is "uitgedrukt in fosfor / opgeloste fractie" (dissolved, as P).
- **Effluent volume gaps:** daily volume (m³) is absent at Amsterdam West, Blaricum and Weesp.
- **Phosphorus chain:**
  - Default plant Uithoorn: Amstel-linked, upstream, nearest to the river.
  - No Amstel-linked plant has effluent phosphate, so step 1 shows that gap explicitly rather than borrowing another plant's series.
  - The window is ±3 km along the river (`ui.phosphorus_chain`).
- **"Near a plant":** within 2,000 m of the plant site. This is a placeholder analysis choice, shown in captions; not a norm.
- **Plotly quirk:** shared y-axes per column switched autorange off (all panels showed 0–4), so autorange is forced on in the RWZI grid.
- **Fonts:** serif titles use a system font stack (Source Serif / Iowan / Georgia). No web-font download.
- **Fixtures:** `scripts/make_ui_fixtures.py` (seeded) produces SYNTHETIC values and `SYN…` station IDs.
  - Real reference geometry is used: the OSM Amstel line and the RWZI locations.
  - RWZI availability per metric mirrors the real files, so the UI shows the real gaps.

## 2026-10-28: Medicines and PFAS are present (correction)

- **Finding:** a check against the dictionary column `P_categorie` found 47 `MEDICIJN` codes. They are measured at only 3 locations AGV-wide, and all 3 are on the Amstel: `AMS003` and `AMS030` (km 0.75) and `ADM016` (km 21.2). An earlier search by name had missed them.
- **PFAS:** 42 codes at 16 locations; on the Amstel only `AMS030` and `ADM016`. The 35 FYCHEM codes without a dictionary entry are all PFAS (ng/l panel).
- **Decision:** both become sparse Tier 2 groups (`sparse: true`), shown as an upstream/downstream pair without source tracing. Instructions Section 1.1 is corrected.

## 2026-10-28: Parameter groups drafted

- **Decision:** `config/parameter_groups.yaml` assigns codes by exact code list (Tier 1, organic load, PFAS), dictionary `P_categorie` (METAL, BACT, BEST, MEDICIJN) or code prefix (biology). The first matching group wins.
- **Status:** a DRAFT for review by the team's marine biologist.

## 2026-10-28: RWZI and hydrology sensor locations from OpenStreetMap

- **Source:** two Overpass queries on 2026-10-28, with user approval: `man_made=wastewater_plant` within 52.10–52.45 N, 4.70–5.30 E, plus names matching zuiver/RWZI/AWZI and the lock gates at the Amstelsluizen. Saved as `data/external/rwzi_sensors_overpass.json` and `_2.json`. © OpenStreetMap contributors, ODbL.
- **Result:** `config/rwzi_locations.csv`, with 9 of the 12 AGV plants located.
  - 7 are mapped as plant sites.
  - Uithoorn and Blaricum use a **proxy**: the solar park on the plant grounds ("Zonnepark RWZI …"), the only named OSM feature.
  - Huizen, Loenen and Maarssen are **not located**: only unnamed plant polygons exist nearby, and they are not used. These plants appear in tables only.
- **Discharge points:** none are verified (`discharge_point_verified = False`). Map markers say "plant location (discharge point not verified)".
- **Distance to the Amstel** (from the plant site, not the discharge point):
  - Uithoorn: 0.8 km (nearest km 1.4)
  - Amstelveen: 1.0 km (km 15.5)
  - De Ronde Venen: 3.7 km (km 2.75)
  - all other plants: more than 7 km
- **Sensors:** Amstelsluizen is placed at the centroid of the OSM lock gates (km 21.02, 10 m from the centreline) and Berlagebrug at OSM relation 18580784 (km 19.23). Tagged ASSUMED, because the exact sensor position at each structure is unknown. Stored in `config/settings.yaml`.

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
  - Relation `12882829` (`waterway=river`, `name=Amstel`, version 12, last edited 2024-11-17), fetched from `https://www.openstreetmap.org/api/0.6/relation/12882829/full` and saved as `data/external/amstel_relation_12882829_full.osm`. The team's `map_overview/amstel_river_loc.xml` holds the same relation but without the way and node geometry, so it cannot be used on its own.
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
