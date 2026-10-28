# HydroNet: Build Instructions for Claude Code

## 0. How to use this file

Read this whole file before writing code. Work through the phases in Section 9 in order. After each phase, run the app or tests, confirm the acceptance criteria for that phase, and only then continue. If something in the data contradicts an assumption here, inspect the data, adapt, and note the deviation in `docs/DECISIONS.md`. Do not silently guess.

---

## 1. Project summary

**Working title:** HydroNet
**Challenge:** AGV (Waterschap Amstel, Gooi en Vecht), water quality monitoring and interpretation for the Water Framework Directive (KRW). Challenge questions from the brief: "CSI the water": trackability of pollutants, traceability of pollutants, and effect of pollutants in the water.

**Problem:** AGV collects large amounts of chemistry and hydrobiology data across the Amstel area, spread over many files and parameters. A water quality manager cannot easily see which locations are in poor condition, which pollutants are involved, or where to investigate first.

**Solution:** An interactive, map-based dashboard that turns AGV's monitoring data into a prioritized view of water quality:

- Each monitoring station is shown on a map, colored by its status against KRW targets.
- Clicking a station shows its measurements over time for chosen parameters, combining chemistry and biology.
- Arrows between neighbouring stations show indicative flow direction.
- Stretches where a pollutant rises downstream are flagged as likely source areas ("Priority Investigation Zones"), to be investigated first.

**Target user:** An AGV water quality manager deciding where to investigate or act first.

**Demo goal:** Demonstrate the tool end to end with one real example from the data (a pollutant, a stretch, a flagged zone, a probable origin profile).

---

## 2. Tech stack and constraints

- Python 3.11+
- Streamlit for the UI
- folium (with `streamlit-folium`) or pydeck for the map. Pick one early and justify it in `docs/DECISIONS.md`. Prefer folium unless arrows/animation need pydeck.
- pandas, numpy, geopandas, shapely, pyproj
- networkx for the station graph
- plotly for time series
- pytest for tests
- Open Dutch geodata only (PDOK, AHN, CBS, etc.). No paid services, no special infrastructure.
- The pipeline must be re-runnable when new measurement files arrive: `python -m hydronet.pipeline` rebuilds all derived data from raw inputs.
- No hardcoded absolute paths. All paths and thresholds come from `config/`.

---

## 3. Repository layout

```
hydronet/
  README.md
  HYDRONET_INSTRUCTIONS.md
  requirements.txt
  config/
    kpi_parameters.yaml      # focused parameter set + KRW targets
    signatures.yaml          # pollutant origin profiles
    settings.yaml            # distances, thresholds, time windows
  data/
    raw/                     # AGV files, never modified
    interim/
    processed/               # parquet outputs of the pipeline
    external/                # open data (AHN, pressures)
  docs/
    DECISIONS.md             # assumptions and deviations log
    LIMITATIONS.md
    DEMO_SCRIPT.md
  src/hydronet/
    __init__.py
    io.py                    # loading raw files
    cleaning.py              # validation, unit harmonisation
    stations.py              # station table, geometry
    status.py                # KRW status per station and parameter
    krw_aggregation.py       # one-out-all-out, what-if
    network.py               # elevation, flow graph, distances
    source_detection.py      # upstream/downstream jump detection
    signatures.py            # origin profile matching
    travel_time.py           # plume propagation, back-tracking
    pressures.py             # wastewater plants, farmland, urban
    pipeline.py              # orchestrates all steps
  app/
    streamlit_app.py
    components/              # map, charts, sidebar, panels
  tests/
```

---

## 4. Data inputs

Expected inputs (inspect the real files first; formats may differ from this description):

1. **Monitoring locations:** two GeoJSON files, FYCHEM (chemistry stations) and HB (hydrobiology stations).
2. **Measurement values:** chemistry and hydrobiology measurements (likely CSV or Excel, possibly several files).
3. **Parameter dictionary ("parameter uitleg"):** parameter names, units, and valid ranges.
4. **Flow velocity data** from AGV, if available, for travel-time estimation.
5. **External open data:**
   - AHN elevation (sampled per station)
   - Known pressures: wastewater treatment plants, farmland, urban/industrial land use

**First task:** write `scripts/profile_data.py` that prints, for every raw file: shape, columns and dtypes, null counts, date range, unique station IDs, unique parameters and units, and CRS for GeoJSON. Save the output to `docs/DATA_PROFILE.md`. Use it to fix column names, station ID join keys, and encodings (Dutch decimal commas, date formats) before building anything else.

---

## 5. Pipeline specification

### 5.1 Cleaning and validation (`cleaning.py`)

- Join measurements to the parameter dictionary.
- Harmonise units to one canonical unit per parameter (implement explicit conversion factors, log every conversion).
- Remove impossible values using the valid ranges from the dictionary. Never delete silently: write removed rows to `data/processed/rejected_values.parquet` with a reason column.
- Handle values below detection limit (e.g. "<0.05") explicitly: keep a flag column and a configurable substitution rule (default: half the limit).
- Output a tidy long table: `station_id, datetime, parameter, value, unit, source (chem|bio), qa_flag`.

### 5.2 Station table (`stations.py`)

- Merge FYCHEM and HB GeoJSON into one GeoDataFrame in EPSG:28992 (RD New), with an EPSG:4326 copy for mapping.
- Columns: `station_id, name, type, geometry, water_body_id (if available), elevation_m`.
- Where chemistry and biology stations are different points on the same water body, link them via water body ID if present, otherwise by nearest-neighbour within a configurable distance. Document the rule.

### 5.3 KRW status per station (`status.py`)

- Focused parameter set defined in `config/kpi_parameters.yaml` (for example total phosphorus, total nitrogen, dissolved oxygen, and selected biological indicators such as macroinvertebrate and macrophyte scores).
- Each parameter entry: `name, unit, direction (lower_is_better|higher_is_better), class thresholds (very good/good/moderate/poor/bad), aggregation (e.g. summer mean, annual mean, percentile), source reference`.
- **Do not invent KRW norms.** Use placeholder values clearly marked `TODO: verify against AGV/KRW targets` where the real value is not available, and surface this in the UI's methodology panel.
- Output per station and parameter: latest assessed value, class, and the period used.

### 5.4 One-Out, All-Out aggregation (`krw_aggregation.py`)

- Overall status per station / water body = worst class among all assessed parameters (the KRW "one-out, all-out" rule).
- Keep ecological and chemical results as separate components and combine them into a single compliance indicator.
- Return which parameter is the limiting ("deciding") one, so the UI can say "Status Moderate because of total phosphorus."
- **What-If engine:** function `simulate(station_or_waterbody, adjustments)` where adjustments is a dict like `{"total_nitrogen": -0.20}` (relative change) and optional parameter toggles (exclude a parameter). Recompute class per parameter and overall status, and report whether the overall status changes and which parameter becomes the new limiting factor. Include the clear message when reducing one parameter will not change the overall status because another parameter still limits it.

### 5.5 Flow network (`network.py`)

- Sample AHN elevation per station (document the AHN product and resolution used).
- Build a directed graph: connect each station to nearby stations (k nearest neighbours within a max distance from `settings.yaml`), with the edge directed from higher to lower elevation.
- Edge attributes: `distance_m`, `elevation_drop_m`, `confidence` (low when elevation drop is below a configurable threshold, which is common in the flat Amstel area).
- Allow manual overrides via `config/flow_overrides.csv` (`from_station, to_station, action: add|remove|reverse`) so AGV can correct directions with their water network data.
- **The UI must always label flow arrows as indicative.**

### 5.6 Source detection (`source_detection.py`)

- For each directed edge A→B and each KPI parameter, compare concentrations using a common time window (e.g. same season or matched sampling dates within N days).
- Compute `delta = B - A`, relative increase, and a significance check (minimum number of paired samples, configurable). Compare against an "expected runoff" baseline: start simple, using the distribution of deltas across all edges for that parameter (e.g. flag when delta exceeds a configurable percentile such as the 90th, and exceeds a minimum absolute step).
- Apply a distance-along-network decay: weight the jump by edge distance so that short reaches with large jumps rank higher than long reaches with the same jump. Keep the formula in one documented function and expose its parameters in `settings.yaml`.
- Output a table of flagged reaches: `edge, parameter, delta, relative_increase, n_pairs, score, rank`. Rank to give the "Priority Investigation Zone" list.
- Report "no clear source found" as a valid outcome, especially for diffuse pollutants (e.g. PFAS).

### 5.7 Origin signatures (`signatures.py`)

- Define origin profiles in `config/signatures.yaml`, for example:
  - Agricultural runoff: elevated phosphate and nitrogen (nitrate/ammonium)
  - Industrial / urban overflow: elevated heavy metals, possibly with temperature rise
  - Wastewater effluent: elevated ammonium, phosphate, low oxygen
- Each profile lists parameters, expected direction, and weight.
- For a flagged reach, compute a **heuristic similarity score** between its observed jump pattern and each profile (e.g. weighted share of profile parameters that rise, or cosine similarity on normalised deltas).
- Label output as a "signature match score" (for example "85% signature match with agricultural runoff"). **Do not present this as a probability or as proof of cause.** Show the contributing parameters.

### 5.8 Pressures (`pressures.py`)

- Collect open data on wastewater treatment plants, farmland, and urban areas (document the source and date).
- For each flagged reach, find pressures within a configurable buffer and list them with distance. Phrase results as "consistent with", never "caused by".

### 5.9 Travel time and back-tracking (`travel_time.py`)

- If AGV flow velocity data exists: estimate travel time per edge as `distance / velocity`. Otherwise use a configurable default velocity range and clearly mark results as assumption-based.
- **Forward plume:** given a source station and a start time, compute estimated arrival times downstream along the graph (Dijkstra on travel time).
- **Trace Backwards:** given a downstream station with an anomaly, return all upstream stations and edges reachable within a given time window (default 48 hours, user-adjustable), with the cumulative travel time per node. Include tributaries (all inbound branches).
- Handle cycles and pumped sections gracefully (graph may not be a DAG; guard against infinite loops).

---

## 6. UI specification (Streamlit)

**Layout:** sidebar for controls, main area with map on top and detail panels below.

**Sidebar**
- Date range selector
- Parameter multi-select (from the focused set, plus an "all parameters" option)
- Toggle layers: stations, flow arrows, flagged reaches, pressures
- What-If controls: per-parameter percentage-change sliders and parameter on/off toggles
- Trace Backwards: time window slider (hours)

**Map**
- Stations colored by overall KRW status (consistent, colorblind-safe palette, with legend; grey for insufficient data).
- Click a station to open its detail panel.
- Directed arrows between stations, with tooltip "Indicative flow direction (from elevation)".
- Flagged reaches highlighted as "Priority Investigation Zones", styled by rank.
- Optional pressure markers.

**Station detail panel**
- Station name, ID, water body, current overall status and the limiting parameter.
- Time series chart(s) for the selected parameters, chemistry and biology together, with KRW class threshold bands.
- Table of parameter classes.
- Buttons: "Trace Backwards" and "What-If".

**Priority list view**
- Ranked table of flagged reaches: parameter, size of jump, signature match label, nearby pressures, score. Click a row to zoom the map.

**Methodology and limitations panel** (always reachable): states the assumptions in Section 8 in plain language.

**Performance:** cache pipeline outputs (`st.cache_data`), load processed parquet files, never recompute the full pipeline on every interaction.

---

## 7. Testing

- Unit tests for: unit conversion, invalid-value removal, detection-limit handling, status classification boundaries, one-out-all-out logic (including the case where one bad parameter dominates), what-if status changes, graph direction from elevation, delta calculation, back-tracking within a time window, cycle safety.
- Use small synthetic fixtures in `tests/fixtures/` (for example a 5-station chain with known jump).
- A smoke test that runs the full pipeline on the real data and asserts that the output files exist and are non-empty.

---

## 8. Limitations (must appear in the app, README, and `docs/LIMITATIONS.md`)

1. Flow direction is assumed from elevation. The Amstel area is flat and pumped, so arrows are indicative only and must be confirmed against AGV's water network data.
2. PFAS and other diffuse pollutants may show no clear source. Report that openly as a result. Proximity to industry is not proof of causation.
3. Flagged source areas are hypotheses, not proof. Matches with known pressures show consistency, not causation.
4. The prototype covers a focused set of parameters, not the full KRW assessment.
5. Signature match scores are heuristic similarity scores, not probabilities.
6. Travel times are estimates and depend on the velocity data or default assumptions used.

---

## 9. Build phases and acceptance criteria

**Phase 1: Data profiling.**
Deliver `docs/DATA_PROFILE.md`. *Accept when* all join keys and units are understood and documented.

**Phase 2: Cleaning and station table.**
*Accept when* the tidy long table and merged station GeoDataFrame exist, rejected values are logged, and tests pass.

**Phase 3: KRW status and aggregation.**
*Accept when* every station has per-parameter classes and an overall one-out-all-out status with its limiting parameter, and a minimal map shows stations colored by status.

**Phase 4: Flow network and time series UI.**
*Accept when* arrows render, are labeled indicative, and clicking a station shows time series with threshold bands.

**Phase 5: Source detection and signatures.**
*Accept when* a ranked list of Priority Investigation Zones exists with signature labels and pressure context, and "no clear source" is a handled outcome.

**Phase 6: What-If and Trace Backwards.**
*Accept when* the what-if panel reports status changes correctly (including no-change cases) and Trace Backwards highlights upstream stations within the chosen window.

**Phase 7: Polish and demo.**
Write `docs/DEMO_SCRIPT.md` around one real example from the data (pick the strongest flagged reach), finalize README (install, run, re-run pipeline, how to override flow directions), and make sure the limitations are visible in the app. *Accept when* a new user can go from clone to running dashboard in under 10 minutes following the README.

---

## 10. Working rules for Claude Code

- Plan briefly, then build in small steps. Commit-sized changes, with tests alongside.
- Keep all thresholds, distances, time windows, and parameter lists in `config/`, never in code.
- Log every assumption and deviation in `docs/DECISIONS.md` with date and reason.
- Never modify files in `data/raw/`.
- Where real values are missing (KRW targets, flow velocities), use clearly marked placeholders and expose them in the UI methodology panel. Never present placeholders as official norms.
- Use cautious wording in the UI: "likely", "consistent with", "indicative", "hypothesis".
- Keep code typed and documented with short docstrings; format with `ruff`/`black`.
- If a requirement here is ambiguous or the data makes it infeasible, pick the simplest reasonable option, document it, and continue, flagging it in your end-of-phase summary.
