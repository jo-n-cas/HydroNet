# HydroNet: Build Instructions for Claude Code

## 0. How to use this file

Read this whole file before writing code. Work through the phases in Section 9 in order. After each phase, run the app or tests, confirm the acceptance criteria for that phase, and only then continue. If something in the data contradicts an assumption here, inspect the data, adapt, and note the deviation in `docs/DECISIONS.md`. Do not silently guess.

This version of the instructions is scoped to the data that is actually available (see Section 4). Features that need data we do not have (raw chemistry values, KRW targets, EKR scores, water network topology) have been removed. Section 11 lists them so they can be re-added if AGV supplies the missing data.

---

## 1. Project summary

**Working title:** HydroNet
**Challenge:** AGV (Waterschap Amstel, Gooi en Vecht), water quality monitoring and interpretation for the Water Framework Directive (KRW). Challenge theme from the brief: "CSI the water": trackability, traceability and effect of pollutants.

**Problem:** AGV collects monitoring data across the Amstel area, spread over many files, systems and parameters. A water quality manager cannot easily see what is measured where, how often, what the known point-source pressures are, and how these relate along the Amstel.

**Solution:** An interactive, map-based dashboard that brings AGV's available data together:

- **Spatial focus: the Amstel river only.** All views are scoped to the Amstel corridor (Amstelhoek to Amsterdam centre, plus a configurable buffer). AGV-wide figures are shown only as context next to the Amstel figures, never as the main view.
- **Monitoring coverage map:** every chemistry (FYCHEM) and hydrobiology (HB) location in the Amstel corridor, styled by how much and what is measured there (from the aggregate counts in the location inventories).
- **Amstel corridor view:** the monitoring locations on or near the Amstel, ordered upstream to downstream along the river, together with the Amstel water level and flow series.
- **Biology time series:** for the 50 locations with raw hydrobiology data, time series per parameter / taxon group.
- **Point-source pressures:** AGV's 12 wastewater treatment plants (RWZI) with their daily effluent volume and effluent quality (phosphate, suspended solids where measured), and which monitoring locations lie near them.
- **Data gap report:** where parameters are measured but no values are available in the prototype, so AGV can see what data is needed for a full KRW assessment.

**Target user:** An AGV water quality manager exploring monitoring coverage and pressures, and deciding where extra data or investigation is needed.

**Demo goal:** Demonstrate the tool end to end with one real example from the data: one RWZI that discharges into (the catchment of) the Amstel, its effluent phosphate and volume over 2021–2025, the monitoring locations near it on the Amstel corridor, and what those locations measure.

### 1.1 Analytical focus: nutrients, led by phosphorus (approved)

The project's main focus has been approved by the team's marine biologist. All defaults, demo choices and the data request follow it.

**Rationale:** nutrients are the main reason AGV's waters miss KRW targets, phosphorus is the nutrient that limits Amstel ecology, and the effluent of the wastewater treatment plants is a known phosphorus load on the Amstel. Phosphorus is also the only pollutant that can be followed through the whole chain in our data: **pressure (RWZI effluent) → water chemistry → ecological effect (algae, water clarity, aquatic plants)**.

Parameter codes below are verified against `FYCHEM_unique_locations_with_measurements.geojson` and `HB_unique_locations_with_measurements.geojson`. Site counts are the number of locations with at least one observation.

**Tier 1, core focus (default selection everywhere in the app):**

| Role in the chain | Variable | Code | FYCHEM sites |
|---|---|---|---|
| Lead nutrient | Total phosphorus | `Ptot_mgP/l` | 1,054 |
| Lead nutrient | Ortho-phosphate (dissolved, plant-available) | `PO4_mgP/l_nf` | 954 |
| Nutrient | Total nitrogen | `Ntot_mgN/l` | 1,038 |
| Sewage signature | Ammonium | `NH4_mgN/l_nf` | 1,029 |
| Agricultural signature | Nitrate | `NO3_mgN/l_nf` | 998 |
| Effect: organic load | Oxygen saturation / concentration | `O2_%`, `O2_mg/l` | 1,001 / 1,091 |
| Effect: algae | Chlorophyll-a | `CHLFa_ug/l_spectro` | 1,058 |
| Effect: light | Water clarity | `ZICHT_m` | 1,001 (+3,511 HB) |
| Context | Temperature, pH, chloride | `T_oC`, `pH`, `Cl_mg/l` | 1,122 / 1,094 / 957 |

**Tier 2, secondary tracers (selectable, not default):**
- Metals (urban/industrial): `Cu_ug/l`, `Zn_ug/l`, `Ni_ug/l`, `Pb_ug/l`, `Cd_ug/l` (215–294 sites; Ni, Pb, Cd are EU priority substances).
- Faecal bacteria (sewage/overflows): `E_COLI_nKVE/dl`, `INTTNLETRCCN_nKVE/dl`, `THERMTLRTCLS_nKVE/ml` (138–515 sites).
- Organic load: `BZV5a_mgO2/l`, `CZV_mgO2/l` (222–417 sites).
- Pesticides (agricultural): e.g. `atzne_ug/l`, `simzne_ug/l` (~80 sites).

**Tier 3, biological effect (KRW biological quality elements):**
- Aquatic plants `PTN_BEDKG_%` (3,665 sites; best biological coverage), fish `VSLC_*` (~570), macroinvertebrates `MEA_n` (289), phytoplankton `FPA_*` (~85). These are raw counts / cover, not EKR scores; raw values exist only for the 50 sampled locations.

**Pressure side (RWZI data):** effluent phosphate (`fosfaat`) is available daily 2021–2025 for 4 AGV plants (Amsterdam West, Blaricum, Huizen, Weesp); effluent suspended solids and volume for most plants. Determine in Phase 5 which plants discharge into the Amstel catchment. Uithoorn, De Ronde Venen and Amstelveen are the Amstel-linked plants but have no effluent phosphate in the current data; if so, the demo uses effluent volume for those plants and states the gap, or uses a plant with phosphate data and documents why.

**Sparse tracers: shown as an upstream/downstream pair, not analysed for sources** (corrected 2026-10-28 after a full check against the dictionary's `P_categorie`):
- **Medicine residues** (`P_categorie = MEDICIJN`): 47 codes (e.g. carbamazepine, metoprolol), measured at only **3 locations AGV-wide, all on the Amstel**: `AMS003` and `AMS030` at km 0.75 (upstream, just below Uithoorn) and `ADM016` at km 21.2 (downstream, Amsterdam). This matches AGV's current Amstel priority (ozone and activated-carbon upgrades at the Uithoorn and De Ronde Venen RWZIs). An earlier search by name missed these codes.
- **PFAS**: 42 codes at 16 locations AGV-wide. On the Amstel only `AMS030` (km 0.75) and `ADM016` (km 21.2). 35 of the 42 codes (the ng/l panel, including GenX `FRD-903` and `ADONA`) have no entry in `Parameter_uitleg.xlsx`: they are exactly the dictionary's 35 "NOT FOUND" FYCHEM codes.
- Both are too sparse to trace a source. Present them as "measured at the upstream and downstream ends of the Amstel only; no source tracing possible", and request the values from AGV with priority.

**Rules that follow from the focus:**
- `config/parameter_groups.yaml` defines the groups (Tier 1 nutrients; Tier 2 metals, bacteria, organic load, pesticides, medicines, PFAS; Tier 3 macrophytes, fish, macroinvertebrates, phytoplankton, other biology) by exact codes, dictionary category (`P_categorie`) or code prefix. Tier 1 is the default group in the sidebar. Sparse groups are marked `sparse: true`.
- `docs/DATA_REQUEST.md` lists Tier 1 first, then Tier 2, and asks AGV for raw values on the Amstel corridor plus the water-type-specific KRW targets for the Amstel waterbody. Note that KRW waterbody `NL11_1_1` is the "Amstellandboezem" (the wider regional canal system), not the Amstel river alone.
- No KRW norm values are hard-coded. Any target quoted from literature (e.g. an earlier Ptot target of 0.21 mg/l for the Amstel) is shown only as a cited reference with source and year, never as a current norm.

---

## 2. Tech stack and constraints

- Python 3.11+
- Streamlit for the UI
- folium with `streamlit-folium` for the map. Justify in `docs/DECISIONS.md`.
- pandas, numpy, geopandas, shapely, pyproj, pyarrow
- plotly for time series
- pytest for tests
- Open Dutch geodata only (PDOK, CBS, OpenStreetMap, etc.). No paid services, no special infrastructure. Every downloaded dataset is stored under `data/external/` with source URL and download date recorded in `docs/DECISIONS.md`.
- The pipeline must be re-runnable when new files arrive: `python -m hydronet.pipeline` rebuilds all derived data from raw inputs.
- No hardcoded absolute paths. All paths and thresholds come from `config/`.

---

## 3. Repository layout

```
hydronet/
  README.md
  HYDRONET_INSTRUCTIONS.md
  requirements.txt
  config/
    settings.yaml            # paths, distances, buffers, filters
    parameter_groups.yaml    # grouping of parameter codes for the coverage map
    rwzi_locations.csv       # manually curated RWZI coordinates (see 5.5)
  data/
    raw/                     # AGV files, never modified
    interim/
    processed/               # parquet outputs of the pipeline
    external/                # open data (Amstel geometry, RWZI locations)
  docs/
    DATA_PROFILE.md
    DECISIONS.md             # assumptions and deviations log
    LIMITATIONS.md
    DATA_REQUEST.md          # what AGV needs to supply for the removed features
    DEMO_SCRIPT.md
  scripts/
    profile_data.py
  src/hydronet/
    __init__.py
    io.py                    # loading raw files
    cleaning.py              # validation, parsing, QA flags
    stations.py              # station table, geometry, coverage
    amstel.py                # Amstel corridor selection and ordering
    hydrology.py             # Amstel water level and flow series
    pressures.py             # RWZI effluent data and proximity
    pipeline.py              # orchestrates all steps
  app/
    streamlit_app.py
    components/              # map, charts, sidebar, panels
  tests/
    fixtures/
```

---

## 4. Data inputs (as actually available)

All raw files stay unchanged; the pipeline looks them up in `paths.raw_dirs` (`data/raw/`, `data/internal/` or the repo root, first match). The facts below were checked against the real files; re-verify them in Phase 1.

| File | Content | Key facts |
|---|---|---|
| `FYCHEM_unique_locations_with_measurements.geojson` | 1,321 chemistry locations | Point per `locatiecode`, `total_observations`, `parameter_counts`, RD and WGS84 coordinates. **Counts only: no measurement values, no dates.** |
| `HB_unique_locations_with_measurements.geojson` | 4,093 hydrobiology locations | Same structure as FYCHEM. Counts only. |
| `HB_sampled50locations.csv` | 13,340 raw hydrobiology rows, 50 locations, 1998–2024 | `;` separated, 78 columns. Join keys: `locatiecode`, `monsterident`, `fewsparameter`. Contains water body attributes (`locatie KRW watertype`, `locatie EAG`, `locatie KRWmeetpuntlocatie`) for these 50 locations only. |
| `Parameter_uitleg.xlsx` | 3,061 parameter definitions | Join `ID` to `fewsparameter` and to `parameter_counts` keys. 35 FYCHEM codes have no entry. `H_MIN/H_MAX/Z_MIN/Z_MAX` are sparse and undocumented; `P_normkader` names a norm framework but **contains no threshold values**. |
| `Amstelsluizen_waterhoogte.csv` | Daily water level, sensor `MPP00013_LIT054_1`, 1993–2025 | `;` separated, two header rows (sensor ID, then label `WATHTE.mNAP.dag.gem`), dates `d-m-yyyy HH:MM`, `GMT+1`. |
| `Berlagebrug_debiet_waterhoogte.csv` | Daily water level and `Q.m3.dag`, 2012–2025 | Same format. Q is mostly negative; sign convention unknown; minimum −28,300,000 is suspicious. |
| `csv/Installations.csv` | 412 installations (RWZIs, regions, water boards) for all Dutch water boards | `,` separated, quoted, **latin-1 encoded**. AGV = `NL.11`, 12 RWZIs (`NL.11.AM` Amstelveen, `NL.11.UI` Uithoorn, `NL.11.RV` Ronde Venen, …). **No coordinates.** |
| `csv/MeasurementPoints.csv` | 32,418 RWZI measurement point definitions | Describes each `MeasurementPointID`: `ProductDescription` (Effluent, Influent, Actief slib, …), `QuantityDescription`, `ParameterDescription`, `Unit`. latin-1. |
| `csv/MeasurementValues.csv` | 3.4 GB of daily RWZI operational values, all water boards | Columns `InstallationCodeOrigin, MeasurementPointID, …, Date, Value, Unit`. AGV rows (`"NL.11.*`) ≈ 1.33M, 2021-01-01 to 2026-01-01. **Must be streamed / chunked and filtered to `NL.11`; never loaded whole.** |

**Not available** (and therefore out of scope): raw chemistry measurement values, raw biology for locations other than the 50, KRW targets/class boundaries, EKR scores, water network topology / flow directions, flow velocities other than the single Berlagebrug Q series.

**First task:** write `scripts/profile_data.py` that prints, for every raw file: shape, columns and dtypes, encoding used, null counts, date range, unique station IDs, unique parameters and units, and CRS for GeoJSON. For `MeasurementValues.csv`, profile only the `NL.11` subset (chunked). Save the output to `docs/DATA_PROFILE.md`.

---

## 5. Pipeline specification

### 5.1 Loading and cleaning (`io.py`, `cleaning.py`)

- **Location inventories:** `parameter_counts` is a serialized Python dict string containing `np.int64(...)` wrappers (e.g. `"{'MEA_n': np.int64(426)}"`). Parse it safely (strip the wrapper with a regex, then `ast.literal_eval`; never `eval`). Validate that the counts sum to `total_observations`; log mismatches.
- Output a long table `data/processed/coverage.parquet`: `station_id, source (chem|bio), parameter, n_observations`, joined to the dictionary (`NAME`, `UNIT`, `GROUP`); unknown codes get `NAME = "NOT FOUND"` rather than being dropped.
- **Biology sample (50 locations):** parse `datum` as datetime, `meetwaarde` as float (handle decimal commas if present).
  - Keep `limietsymbool` (`<`, `>`) as a flag column; do not substitute values for biology counts. Record the rule in `DECISIONS.md`.
  - Treat `-999` as a missing-value sentinel (6 rows): move to rejected with reason `sentinel_-999`. Check for other sentinels during profiling.
  - Keep `kwaliteitsoordeelcode` as-is (`0`, `3`, `9`); do not filter on it unless the code meanings are confirmed from the Aquo table. Expose it as a filter in the UI.
  - Range checks: only apply dictionary bounds where they exist and only as `qa_flag = out_of_range`, never as deletion, because the bounds are undocumented.
  - Output tidy long table `data/processed/bio_values.parquet`: `station_id, sample_id, datetime, parameter, taxon, taxon_group, value, unit, limit_flag, quality_code, qa_flag`.
- **Never delete silently:** all removed rows go to `data/processed/rejected_values.parquet` with a `reason` column.
- **Hydrology CSVs:** skip the second header row, parse `d-m-yyyy HH:MM` with `dayfirst=True`, keep the timezone label as stated (`GMT+1`, no DST conversion). Output `data/processed/hydrology.parquet`: `sensor_id, site (Amstelsluizen|Berlagebrug), date, quantity (level_mNAP|Q_m3_per_day), value, qa_flag`. Flag (do not remove) values more than a configurable number of robust standard deviations from the median; the Berlagebrug minimum must end up flagged. Do not reinterpret the Q sign; document it as unknown.
- **RWZI data:** read with `encoding="latin-1"`. Stream `MeasurementValues.csv` in chunks, keep rows with `InstallationCodeOrigin` starting with `NL.11`, write `data/interim/rwzi_values_nl11.parquet`. Join to `MeasurementPoints.csv` on `MeasurementPointID`.
  - A parameter is identified by the **combination** `ProductDescription + QuantityDescription + ParameterDescription + Unit`, not by `ParameterDescription` alone (many rows have `Niet van toepassing`, which then means e.g. effluent volume).
  - Keep only `ProductDescription == "Effluent"` for the pressures layer; the full NL.11 subset stays in interim for later use.
  - Output `data/processed/rwzi_effluent.parquet`: `installation, installation_name, measurement_point, date, product, quantity, parameter, unit, value`. If one plant has several measurement points for the same parameter, keep them separate and document which one is shown by default.

### 5.2 Station table (`stations.py`)

- Merge FYCHEM and HB GeoJSON into one GeoDataFrame in EPSG:28992 (RD New, from `rd_x_original`/`rd_y_original`), with an EPSG:4326 copy for mapping. Check that RD and WGS84 coordinates agree after reprojection (tolerance in `settings.yaml`); log mismatches.
- One row per `station_id`. Columns: `station_id, is_chem, is_bio, has_raw_bio (one of the 50), n_chem_obs, n_bio_obs, n_parameters, krw_watertype, eag, krw_waterbody, geometry`. The water body columns are filled only for the 50 sampled locations; leave them empty elsewhere (do not infer them).
- The 443 codes present in both inventories are the same station (same code). Codes that differ but share identical coordinates are kept as separate stations; log them.
- Output `data/processed/stations.parquet` (GeoParquet).

### 5.3 Coverage and data gaps (`stations.py`)

- Group parameter codes into readable groups via `config/parameter_groups.yaml`, using the tiers and gap groups from Section 1.1. Codes not matched by any group go to `other`; report how many.
- Per station: observations per group, number of distinct parameters, and a flag for whether raw values are available in the prototype (only the 50 HB locations).
- Generate `docs/DATA_REQUEST.md` automatically from the coverage table: per parameter group, how many observations exist in AGV's systems (from the counts) versus how many values are available in the prototype. This is the quantified basis for requesting the raw FYCHEM export.

### 5.4 Amstel corridor (`amstel.py`)

- The Amstel centreline is built by `scripts/build_amstel_line.py` from OpenStreetMap (© OpenStreetMap contributors, ODbL). It combines relation `12882829` (the Amstel, 39 `main_stream` ways, Nes aan de Amstel to Amsterdam) with way `96361977` (Amstelhoek to Nes aan de Amstel, which OSM names "Amstel-Drechtkanaal"). Where the river splits into parallel lock channels (the Amstelsluizen), the shortest channel is kept. Outputs: `data/external/amstel.geojson` (EPSG:4326), `amstel_rd.geojson` (EPSG:28992) and `amstel_segments.geojson` (the way IDs used). Source files and download date are in `DECISIONS.md`.
- The Amstel is defined as the river from the confluence of the Drecht and the Kromme Mijdrecht at Amstelhoek (52.2288 N, 4.8207 E) to the Binnen-Amstel in Amsterdam centre (52.3674 N, 4.8940 E): 22.0 km.
- Do not select Amstel stations by code prefix. Most corridor stations are `AMS…`, but some `AMS` codes lie elsewhere (e.g. AMS186 on the Ringvaart), and the corridor also contains other prefixes (KMU, UHP, PEB, VGD, ADM, …).
- **Selection rule (team decision):** the pipeline keeps every location within **100 m** of the centreline (`settings.yaml`: `amstel.max_distance_m`), with all its data. The exact procedure, edge cases and expected results are in `docs/AMSTEL_STATION_SELECTION.md`. The real inventories give 30 / 58 / 76 locations at 25 / 50 / 100 m. Output `data/processed/amstel_stations.parquet` with `station_id, is_chem, is_bio, distance_to_river_m, chainage_m, beyond_river_end`, not pre-filtered below 100 m. The UI offers 25 / 50 / 100 m as a sensitivity filter on top of this table.
- `chainage_m` = position along the centreline measured from the upstream start (shapely `project`). Ordering by chainage gives an upstream→downstream sequence along the Amstel. This replaces elevation-based flow direction: the Amstel's general flow direction is towards Amsterdam, but the system is managed (sluices, pumping), so ordering is labelled **"position along the river (upstream → downstream, indicative)"**.
- Stations in side canals or polders close to the river may fall within the buffer. Add `config/amstel_overrides.csv` (`station_id, action: include|exclude, reason`) so a user can correct the selection.
- Place the two hydrology sensors (Amstelsluizen, Berlagebrug) on the corridor by chainage. Their coordinates are not in the data: take them from an open source or the known structure locations, put them in `settings.yaml`, and document the source.

### 5.5 Pressures: wastewater treatment plants (`pressures.py`)

- The RWZI files have no coordinates. Create `config/rwzi_locations.csv` (`installation, name, x_rd, y_rd, source`) for the 12 AGV plants, filled from open data (e.g. PDOK / Emissieregistratie RWZI locations or OpenStreetMap `man_made=wastewater_plant`). Every row must have a source. Plants without a verified location are shown in tables but not on the map.
- Where an RWZI discharges is not the same as where the plant stands. If the discharge point is not known from open data, use the plant location and label the map marker "plant location (discharge point not verified)".
- For each RWZI: nearby monitoring stations within a configurable buffer (`settings.yaml`), with distance, and whether the RWZI lies within the Amstel buffer zone, plus its nearest Amstel chainage.
- Summaries per RWZI per year: total effluent volume and mean/median effluent phosphate and suspended solids where measured. Units come from the data; check the units of `fosfaat` (mg P/l vs mg PO4/l) in the measurement point description and document it.
- Phrase results as "near" / "consistent with", never "caused by". Note that the RWZI data (2021–2025) and the biology data (1998–2024) overlap only in 2021–2024; show the overlapping period explicitly in any comparison.

### 5.6 Hydrology (`hydrology.py`)

- Daily Amstel water level at Amstelsluizen and Berlagebrug, and Q at Berlagebrug, as time series with flagged values highlighted (not hidden).
- Simple derived views: monthly mean level, monthly mean Q, and the level difference between the two sensors over their common period (2012–2025).
- No travel-time computation: one Q series without cross-section data does not support velocity estimates. State this in the limitations.

---

## 6. UI specification (Streamlit)

**Spatial scope:** the whole UI is scoped to the Amstel corridor (Section 5.4). AGV-wide numbers appear only as context next to the Amstel numbers (e.g. "Amstel corridor: 58 locations · AGV-wide: 5,414"). The detailed page design is in `docs/UI_PLAN.md`.

**Layout:** sidebar for controls, main area with map on top and detail panels below.

**Sidebar**
- Station source filter: chemistry, biology, both
- Parameter group selector (from `parameter_groups.yaml`, default Tier 1 nutrients) and optional single parameter (default `Ptot_mgP/l`)
- Amstel buffer distance: 25 / 50 / 100 m (default 100 m, matching the pipeline selection rule; smaller values are a sensitivity view)
- River stretch: chainage range slider in km along the Amstel (default: the whole river). It selects a stretch of river and drives the map highlight, the small-multiples strip, the corridor view and the phosphorus chain. It replaces free-form area selection on the map.
- Date range selector (applies to biology, hydrology and RWZI time series)
- Layer toggles: corridor stations, Amstel centreline and buffer, RWZIs, hydrology sensors, context stations outside the corridor (off by default)
- Quality code filter for biology data (default: show all, with codes visible)

**Map**
- Opens on the Amstel corridor extent. Only corridor stations are drawn as data markers; stations outside the corridor are hidden unless the context layer is on, in which case they are tiny grey dots without counts.
- Corridor stations are sized or coloured by number of observations for the selected parameter group (colorblind-safe sequential palette, with legend; grey for zero). Distinguish chemistry, biology and both by marker shape.
- Stations with raw biology data in the prototype are highlighted. If none lie in the corridor, say so on the map and point to the nearest one with its distance.
- Amstel centreline with the buffer zone and the selected stretch highlighted; corridor stations labelled with their chainage; credit "© OpenStreetMap contributors".
- RWZIs: the Amstel-linked plants (within the pressure buffer of the corridor, plus Uithoorn, De Ronde Venen and Amstelveen as named in `settings.yaml`) are drawn prominently, with the "discharge point not verified" label where applicable. Other AGV plants appear only in a collapsed context section of the Pressures page.
- Click a station or RWZI to open its detail panel.

**Station detail panel**
- Station ID, source(s), water body attributes if known, distance to the Amstel and chainage if on the corridor.
- Coverage table: parameter, dictionary name, unit, number of observations.
- If raw biology data exists: time series per selected parameter / taxon group (plotly), with limit and quality flags visible.
- Nearby RWZIs with distance.

**RWZI detail panel**
- Effluent volume and quality time series, yearly summaries, nearby stations.

**Amstel corridor view**
- Longitudinal chart: stations along chainage (x-axis) with observation counts per parameter group, RWZI and sensor positions marked, labelled "upstream → downstream (indicative)".
- Water level and Q time series below.

**Data gaps view**
- The table from 5.3 / `DATA_REQUEST.md`, with columns for the Amstel corridor and AGV-wide side by side.

**Methodology and limitations panel** (always reachable): states Section 8 in plain language.

**Performance:** load processed parquet files with `st.cache_data`; never run the pipeline from the app.

---

## 7. Testing

- Unit tests for: `parameter_counts` parsing (including `np.int64` wrappers and malformed strings), counts summing to totals, biology value parsing and sentinel rejection, rejected-rows logging, hydrology CSV parsing (two header rows, day-first dates), outlier flagging, RWZI chunked filtering to `NL.11` and parameter identification by the full combination, station merge (shared codes, duplicate coordinates), Amstel buffer selection and chainage ordering, overrides (include/exclude), RWZI proximity.
- Use small synthetic fixtures in `tests/fixtures/` (e.g. a straight synthetic river line with 5 stations at known chainages, a tiny MeasurementValues file with mixed water boards).
- A smoke test that runs the full pipeline on the real data and asserts that the output files exist and are non-empty.

---

## 8. Limitations (must appear in the app, README, and `docs/LIMITATIONS.md`)

1. No raw chemistry values are available: chemistry is shown as coverage (what is measured, how often), not as concentrations or status.
2. No KRW status is computed: KRW class boundaries and EKR scores are not in the data, and raw biology covers only 50 locations.
3. Biology values are raw counts, cover percentages and scale values; they are not comparable across parameters or protocols without the parameter, unit and method.
4. Upstream/downstream ordering along the Amstel is based on position along the river, not on measured flow. The system is managed (sluices, pumping); ordering is indicative only.
5. The Amstel station selection depends on the buffer distance and the centreline used; it can include stations in adjacent waters.
6. RWZI locations come from open data, and discharge points may differ from plant locations. Proximity to an RWZI is not evidence that it affects a station.
7. The Berlagebrug Q series has an unknown sign convention and at least one suspicious extreme; values are flagged, not corrected.
8. Time periods differ between datasets (biology 1998–2024, RWZI 2021–2025, hydrology 1993/2012–2025); comparisons are limited to overlapping periods.

---

## 9. Build phases and acceptance criteria

**Phase 1: Data profiling.**
Deliver `docs/DATA_PROFILE.md`. *Accept when* all join keys, encodings, units and date formats in Section 4 are verified (or deviations logged).

**Phase 2: Cleaning, station table and coverage.**
*Accept when* `coverage.parquet`, `bio_values.parquet`, `hydrology.parquet`, `rwzi_effluent.parquet`, `stations.parquet` and `rejected_values.parquet` exist, `DATA_REQUEST.md` is generated, and tests pass.

**Phase 3: Coverage map.**
*Accept when* the app shows all stations coloured by coverage for a selected parameter group, with a working station detail panel and biology time series for the 50 locations.

**Phase 4: Amstel corridor and hydrology.**
*Accept when* the Amstel stations are selected and ordered by chainage, overrides work, the corridor view renders with the indicative label, and the water level / Q series are shown with flagged values.

**Phase 5: RWZI pressures.**
*Accept when* the AGV RWZIs with sourced coordinates appear on the map, effluent time series and yearly summaries are shown, and nearby stations are listed per RWZI.

**Phase 6: Polish and demo.**
Write `docs/DEMO_SCRIPT.md` around the example in Section 1, following the phosphorus chain from Section 1.1 (RWZI effluent → Tier 1 coverage on the Amstel corridor → Tier 3 biology near it). Pick an RWZI in the Amstel catchment with effluent phosphate data, or document why another one was chosen, finalize README (install, run, re-run pipeline, how to edit overrides and RWZI locations), and make sure the limitations are visible in the app. *Accept when* a new user can go from clone to running dashboard in under 10 minutes following the README.

---

## 10. Working rules for Claude Code

- Plan briefly, then build in small steps. Commit-sized changes, with tests alongside.
- Keep all thresholds, distances, buffers, parameter groups and coordinates in `config/`, never in code.
- Log every assumption and deviation in `docs/DECISIONS.md` with date and reason.
- Never modify files in `data/raw/`.
- Ask the user before downloading external data; record source and date.
- Use cautious wording in the UI: "near", "consistent with", "indicative".
- Keep code typed and documented with short docstrings; format with `ruff`/`black`.
- If a requirement here is ambiguous or the data makes it infeasible, pick the simplest reasonable option, document it, and continue, flagging it in your end-of-phase summary.

---

## 11. Out of scope until AGV supplies more data

These were removed because the current data cannot support them. Keep the code structure open so they can be added later.

| Feature | Data needed |
|---|---|
| KRW status per station, one-out-all-out, What-If | Raw FYCHEM values (station, date, parameter, value, unit, detection-limit flag); KRW class boundaries per water type / water body; EKR scores for biology |
| Source detection (upstream/downstream jumps), Priority Investigation Zones | Raw FYCHEM values with sufficient paired sampling along the network |
| Origin signature matching | Raw FYCHEM values for nutrients, metals, oxygen, temperature |
| Flow network with directions, Trace Backwards, travel times | AGV water network (legger) with flow directions, water level areas (peilgebieden), pumping stations, flow velocities or cross-sections |
