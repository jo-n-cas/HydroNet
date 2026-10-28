# HydroNet: Amstel monitoring explorer

An exploratory, map-based tool for AGV (Waterschap Amstel, Gooi en Vecht). It shows **what is measured along the Amstel, where and how often**, next to the wastewater treatment plants (RWZIs) near the river and the river's water level. Scope, data and rules are in `HYDRONET_INSTRUCTIONS.md`.

It is an observational research instrument:
- **No KRW status** is computed, because no norms are available.
- **No causal claims** are made.
- **Assumptions are tagged** ("Assumed / indicative") wherever they shape what you see.

## Install

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

Python 3.11+ is required; the project is tested on 3.13.5.

## Build the Amstel centreline (once)

The centreline is built from the OpenStreetMap exports in `data/external/`. Its output is git-ignored, so everyone builds it locally:

```bash
.venv/bin/python scripts/build_amstel_line.py data/external/amstel_relation_12882829_full.osm \
    data/external/amstel.geojson \
    --extra data/external/uithoorn_waterways_overpass.json --extra-way 96361977
```

## Clean the data (pipeline)

```bash
PYTHONPATH=src .venv/bin/python -m hydronet.pipeline              # full run (~15 s)
PYTHONPATH=src .venv/bin/python -m hydronet.pipeline --skip-rwzi  # re-use the cached RWZI extract
PYTHONPATH=src .venv/bin/python -m hydronet.pipeline --without-rwzi # build available real data if RWZI CSVs are absent
```

The pipeline reads the raw AGV files from the first folder in `paths.raw_dirs` that has them (`data/raw`, `data/internal` or the repo root). It writes `data/processed/*.parquet`, `rejected_values.parquet` and `pipeline_manifest.json` (row counts, rejected reasons, checks). Nothing is deleted silently: invalid rows go to `rejected_values.parquet` with a reason, and suspect values are kept with a `qa_flag`. `--without-rwzi` leaves the RWZI effluent output unavailable; the overview, coverage map and corridor still use real data.

## Run the app

```bash
.venv/bin/streamlit run app/streamlit_app.py
```

The app opens at http://localhost:8501. It only *reads* processed files and never runs the pipeline.

### Fixture data vs real data

The UI reads the folder named in `config/settings.yaml`:

```yaml
ui:
  data_dir: data/processed             # real pipeline outputs (default)
  # data_dir: tests/fixtures/processed # synthetic fixtures for layout work
```

The environment variable `HYDRONET_DATA_DIR` overrides this; the tests use it to always run on the fixtures.

With fixture data selected, the app shows a **synthetic data** banner. The other dashboard
pages use `SYN` station IDs. Regenerate the fixtures with:

```bash
.venv/bin/python scripts/make_ui_fixtures.py
```

The **Chemical detection reach** page uses real station locations and chemistry coverage in
`amstel_subset/`. Select chloride (blue), ammonium (orange) or total phosphorus (purple).
Choose **Map 1 · Chemical locations** to highlight stations with records for the selected chemical in that color;
other selected stations are grey. Hover over any station to see recorded observation counts
for all three chemicals. A colored marker means **assumed detected** under the explicit
assumption that an observation means presence;
grey means detection status is unknown, not absent. Choose **Map 2 · Possible entry and downstream
route** to see an assumed south-to-north path for the same chemical. Thicker segments and larger
station markers represent higher observation counts; they do not represent concentration.
A hollow circle marks the first assumed presence, diamonds mark station intervals where counts
rise, and the dashed line shows a possible continuation beyond the last recorded station.
These are possible entry reaches, not verified sources: counts may rise because a station was
sampled more often, and records at several stations do not prove a shared pollution event.

The column contract both sides must follow is in `src/hydronet/schemas.py`. If a real file misses a contract column, the app says which one instead of guessing.

## Pages

| Page | What it shows |
|---|---|
| **Overview** | What HydroNet can and cannot say; a data card (Amstel vs AGV-wide); the Observed/Assumed legend; dataset time spans and their overlap |
| **Coverage map** | Corridor locations sized and coloured by observations for the selected group or parameter; RWZIs and sensors; click a location to select it; a coverage strip for the selected river stretch |
| **Station detail** | Coverage table, raw biology small multiples with flags, distance to the river and position along it, nearby RWZIs |
| **Amstel corridor** | Locations along the river (km) per parameter group, RWZIs and sensors as nodes, water level and Q with flagged values, buffer sensitivity (25/50/100 m) |
| **Pressures (RWZI)** | Yearly effluent volume, phosphate and suspended solids per plant, "not measured" gaps, locations near each plant |
| **Phosphorus chain** | The demo story: effluent → Tier 1 coverage near the plant → nearest raw biology, on a shared time axis |
| **Data gaps** | Observations in AGV systems vs raw values in the prototype, per group; exports `DATA_REQUEST.md` |
| **Methods & limitations** | Limitations (instructions §8), key analysis choices, data source in use, decisions log |
| **Chemical detection reach** | Switches between assumed chemical presence and an indicative south-to-north route with count-rise entry candidates |

Every figure carries an n-line, a settings caption and an **About this view** panel. That panel lists source files, processing steps, rows before and after cleaning, and rejected rows, and has CSV and JSON exports.

## Configuration

| What | Where |
|---|---|
| Paths, Amstel rule (100 m), sensors, RWZI settings, effluent metric rules, UI defaults | `config/settings.yaml` |
| Parameter groups (Tier 1/2/3; draft for review by the marine biologist) | `config/parameter_groups.yaml` |
| RWZI locations (OSM, with source and location basis per plant) | `config/rwzi_locations.csv` |
| Manual corrections to the Amstel selection (`station_id, action, reason`) | `config/amstel_overrides.csv` (optional) |

Assumptions and deviations are logged in `docs/DECISIONS.md`.

## Tests

```bash
.venv/bin/python -m pytest -q
```

The suite covers four things:
- the pure view logic: aggregations, chainage ordering, buffer sensitivity, overlap periods, effluent metrics, data-gap labels
- the parameter-group rules
- that the fixtures conform to the column contract
- a headless smoke test of every page, including under narrowed settings

## Data credits

Map data and the Amstel centreline: © OpenStreetMap contributors, ODbL 1.0.
