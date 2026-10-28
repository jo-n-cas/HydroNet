# HydroNet data guide: plain-language explanation

This guide explains the files and field names in `data_overview.md`. The complete original overview, including every measured count, column profile, parameter code, description, and unit, follows the guide. The files are Dutch water-monitoring exports. Some field names and code values come from Waternet/Aquo systems; a code’s exact approved definition is not always included in these files, so opaque codes are described as identifiers rather than guessed at.

## Start here: what each file contains

| File | What it is | What a row/feature represents |
| --- | --- | --- |
| `Amstelsluizen_waterhoogte.csv` | A daily water-level series for sensor `MPP00013_LIT054_1`, from 1 July 1993 to 7 May 2025. | One day and one daily-average height. |
| `Berlagebrug_debiet_waterhoogte.csv` | Daily water height plus a flow/volume series at Berlagebrug, from 27 July 2012 to 7 May 2025. | One day, one height, and one flow/volume reading. |
| `HB_sampled50locations.csv` | A biological and habitat sample export from 50 sites. It includes fish, plants, macroinvertebrates and habitat measurements. | One recorded result or descriptive observation. Many rows can belong to a single sample, date and site. |
| `HB_unique_locations_with_measurements.geojson` | A map-ready inventory of 4,093 biological-monitoring locations, with summary counts by parameter. | One location, with its coordinates and aggregate counts. It does not contain the underlying observations or dates. |
| `FYCHEM_unique_locations_with_measurements.geojson` | A map-ready inventory of 1,321 physical/chemical monitoring locations, with summary counts by parameter. | One location, with coordinates and aggregate counts, not raw chemistry measurements. |
| `Parameter_uitleg.xlsx` | A dictionary of 3,061 parameter definitions. `Parameter_uitleg` means “parameter explanation.” | One parameter’s metadata: readable name, unit, group, bounds and source-system identifiers. |

The two time-series files have sensor codes and timestamps, but no site-code crosswalk to the location inventories. Their measurements can be compared by date; they cannot be reliably attached to a monitoring site from these files alone. Their timestamps match exactly on 4,668 days, the full Berlagebrug series. The Amstelsluizen series extends further back.

## How the files connect

`locatiecode` is the location key in the sample CSV and both GeoJSONs. All 50 sampled biological locations occur in the HB inventory. Three of those 50 also occur in FYCHEM. The two full location inventories share 443 codes. A shared code says the same site identifier occurs in both inventories; it does not show that the measurements happened on the same date, used the same method, or refer to the same sample.

The biological CSV uses `fewsparameter` for a parameter code. The dictionary’s `ID` is the candidate matching key. The GeoJSON `parameter_counts` keys are also parameter codes. The dictionary describes 39/39 codes in the sample CSV, 79/79 codes in the HB inventory and 749/784 codes in FYCHEM; 35 FYCHEM codes have no dictionary entry. Where a dictionary entry is absent, the overview says `NOT FOUND`; it does not mean the parameter had no measurements.

The sample CSV has 13,340 rows, while the HB location inventory reports 1,336,248 observations across all sites. These are different scopes: the CSV is a selected sample of 50 locations and does not represent every observation in the full inventory. FYCHEM reports 2,090,352 aggregate observations but supplies no observation rows here.

## Reading the summary statistics

- **Rows**: records read from the file. For the biological export, a row is an observation/result and can repeat a site or date.
- **Features**: GeoJSON map objects. Here each is a point representing a location.
- **Empty**: blank cells. This is different from a zero, `0`, or a zero-length measurement.
- **Distinct nonempty**: number of different nonblank values, not necessarily number of meaningful categories.
- **Numeric/nonempty**: how many populated cells could be read as finite numbers, out of all populated cells. Codes that look numeric can be identifiers rather than measurements.
- **Numeric range**: smallest and largest finite numeric values as stored. No unit conversion, plausibility filtering or quality-control correction was applied. A range alone does not establish that a value is valid.
- **Most common values**: top three exact strings and their row counts. They are not necessarily the most important values.
- **Date coverage**: first and last parsed timestamp, number of unique timestamps and repeated timestamp rows. Repeats are expected in biological records because multiple taxa, parameters or samples can share a timestamp. The “spacing” is the gap between distinct timestamps; it is not a promise that every possible sampling day is represented.
- **Parameter count**: in the HB sample it is a count of CSV rows; in GeoJSON it is a source-reported aggregate. They are not directly comparable totals.

## The two sensor files

Both CSVs use semicolons. Their first row contains the time column and machine sensor IDs; their second row gives human-readable measurement labels. `GMT+1` labels the timestamp zone. The overview preserves the label as supplied; it does not apply daylight-saving corrections.

`WATHTE.mNAP.dag.gem` means daily average water height (`WATHTE`), in metres (`m`), relative to NAP (`NAP` is the Dutch national vertical datum; `dag.gem` means daily average). A negative number is below the NAP reference level, not automatically an error.

`Q.m3.dag` is a flow/volume-related quantity labelled in cubic metres per day. The name suggests a daily amount, but the files do not define whether it is a daily sum, which direction is positive, or whether a sentinel value is used. Do not reinterpret it as m³/s without source documentation. Berlagebrug’s reported minimum, −28,300,000, is unusually extreme and should be checked with the data provider; the overview does not classify it as missing or invalid.

## The biological sample file: how to read a row

A row combines several kinds of information: who/what was sampled, where and when, what was measured, the result and its qualifiers. The key fields are:

- `monsterident`: sample identifier. One sample can generate many rows.
- `locatiecode`: monitoring-site identifier; use it to join to a location inventory.
- `datum`: observation/sample date and time as recorded.
- `fewsparameter`: parameter identifier; join to dictionary `ID` for a longer name and unit.
- `meetwaarde`: recorded result. It can be a number, count, percentage, scale value or encoded category depending on the parameter. Never interpret it without the parameter and unit.
- `eenheid`: unit/code attached to the result. `n` means a count; `%` a percentage; `m`, `m²`, `cm²`, `l`, `g`, `kg/ha` and `n/ha` are lengths, areas, volumes, mass or area-normalized counts. `DIMSLS` means dimensionless: a score/category without a physical unit, not necessarily a continuous quantity.
- `limietsymbool`: measurement qualifier. `<` and `>` mean the result is reported relative to a limit (for example, below or above a reporting threshold); it is not an ordinary exact value. The overview finds 32 `>` and 2 `<` rows.
- `kwaliteitsoordeelcode`: a code describing the reliability/interpretation assessment of a measurement under the Aquo vocabulary. The file contains mostly `0`, plus `3` and `9`; this overview cannot map those individual codes to approved labels. Preserve the code and consult the applicable current Aquo table before filtering or treating records as accepted/rejected. [Aquo defines this field as the reliability and interpretation assessment of a value](https://www.aquo.nl/index.php/Id-1e17d9e6-4e0e-4f88-8fe5-c71f6a7931db).
- `waardebewerkingsmethode`: code for how the value was processed/derived; observed values include `MET`, `RENDMT_BER` and `BER`, whose precise definitions are not supplied here.
- `afronding`: whether the value was rounded (`Ja`/`Nee`).
- `opmerkingmeting`: field notes. Examples say the site had recently been mown, dredged, or had soft silt. These can explain unusual observations.

The sample’s `xcoormonster`/`ycoormonster` are coordinates attached to the sample. `locatie x`/`locatie y` are coordinates attached to its site. They are close but not identical in the data; don’t silently substitute one pair for the other. These values look like Dutch RD grid coordinates in metres. The GeoJSON additionally gives longitude/latitude in WGS84 and original RD coordinates.

### Biological CSV columns, translated by meaning

The overview lists all 78 columns. This glossary explains what each family and field means. Dutch words are translated literally where that is safe; acronyms and controlled values are left as codes if their exact expansion is not present in the files.

| Column(s) | Plain-language meaning |
| --- | --- |
| `monsterident`, `externereferentie` | Internal sample ID and an external/source reference for the sample. |
| `xcoormonster`, `ycoormonster` | Sample’s X and Y coordinates. |
| `monsternemer`, `analist` | Sampler/field collector and analyst. Often staff or organization codes. |
| `planvanaanpak` | “Plan of approach”: survey/project plan reference. |
| `bemonsteringssoort` | Sampling type code (`PO`, `MB`); meanings of these two codes are not defined in this file. |
| `bron` | Source file/system or dataset from which the record originated. |
| `veldapparaat` | Field equipment used (examples include rake and seine/net types). |
| `bemonsteringsprotocol`, `analyseprotocol`, `analysecode` | Sampling protocol, analysis protocol and analysis method/code. Keep these because methods can affect comparability. |
| `locatiecode`, `locatie namespace`, `locatie omschrijving` | Site key, identifier namespace (`NL11` here), and human-readable site/monitoring description. |
| `locatie x`, `locatie y`, `locatie z`, `locatie referentievlakzcoord` | Site coordinates and elevation/depth fields. Z and its reference-plane field are empty in all 13,340 rows. |
| `locatie KRW watertype` | European Water Framework Directive (KRW) water-body type code. `M10`, `M1a`, etc. are codes; their full definitions are not included. |
| `locatie EAG`, `locatie afaanvoergebied` | Ecological area/management-area and drainage/supply-area identifiers. Exact local code definitions are not included. |
| `locatie KRWmeetpuntlocatie` | Water Framework Directive monitoring-point identifier; missing on 4,762 rows. |
| `locatie morfologielocatie` | Site shape/type description: `lijnvormig` = linear, `plas` = pond, `plas_dras` = pond/wet area. |
| `locatie bodemsoortlocatie` | Recorded soil/bed type (for example peat, water, light clay). |
| `locatie meetprogrammahistorie`, `locatie meetprogrammaactueel` | Historical and currently listed monitoring programmes. The “current” field is missing on 7,721 older/other rows; blank does not mean the historical programme never existed. |
| `locatie meetnethistorie`, `locatie meetnetactueel` | Historical and current monitoring network membership. Values are concatenated system codes. Current is blank on 7,721 rows. |
| `compartiment` | Monitored medium/compartment code. Aquo uses compartment codes for media such as surface water (`OW`) and organisms (`OE`); this file also has `EZ` and `OR`, whose precise local meanings should be checked in the source vocabulary. [Aquo’s measurement guidance describes compartment as the environmental medium](https://www.aquo.nl/images/aquo/archive/2/27/20250122084235%21Praktijkrichtlijn-domeintabellen-im-metingen.pdf). |
| `datum` | Observation date/time. 148 distinct dates are repeated across the 13,340 result rows. |
| `fewsparameter`, `fewsparameternaam` | Machine parameter key and readable parameter name. |
| `fewsparametercategorie` | System category for the parameter (`HYBIO`, `VELD`, `MONSVAR`, etc.); the complete codebook is not supplied. |
| `fewsparametergrootheid`, `grootheid` | Quantity/type measured (for example plant cover, count, mass). The former is the FEWS-specific quantity and the latter the parameter’s quantity classification. |
| `parametercode`, `parameterfractie`, `parametergroep`, `parametertypering` | Additional source parameter, fraction/substance form, group and type metadata. Often blank; exact code vocabularies are not included. |
| `biotaxonnaam`, `confertaxon`, `TWN naam`, `TWN taxontype`, `TWN taxonlevel`, `TWN taxongroup` | Organism/taxon identity and taxonomy metadata. TWN is the Dutch taxonomy name system used by the source. Taxon types include plants, fish and macroinvertebrates; taxon levels include species, genus and subspecies. `confertaxon` is empty throughout. |
| `WNA nederlandse soortnaam` | Dutch common name for the taxon (e.g. Baars = European perch, Blankvoorn = common roach). |
| `beschermingsstatus florafaunawet` | A flora/fauna legal-protection status code; only 156 rows are populated. The legal code definitions/time context are not in this export, so don’t infer current legal status from the numbers. |
| `WNA oeverplantensoorten`, `WNA emerse plantensoorten`, `WNA soorten met drijvend blad`, `WNA kroossoorten`, `WNA onderwaterplantensoorten` | Boolean-like 0/1 flags for shoreline plants, emergent plants, floating-leaf plants, duckweed and submerged plants. These flags only apply to a subset of rows; blank means not populated, not “no.” |
| `WNA stromingsgilde vis`, `WNA migratiegilde vis`, `WNA habitatvoorkeur vis`, `WNA plantminnendheid vis` | Fish ecological guild classifications: flow preference, migration behaviour, habitat preference and affinity for vegetation. Values are short codes; the full code descriptions aren’t provided. |
| `WNA reynolds groep cyanobacterieen`, `WNA zuurstoftolerante vis`, `WNA fytoplankton groep`, `WNA fytoplankton subgroep`, `WNA toxische blauwalg` | Cyanobacteria/Reynolds grouping, oxygen-tolerance classification for fish, phytoplankton group/subgroup and toxic-blue-green-algae flag. The first two fields are empty; only small subsets of the other three are filled. |
| `gedrag`, `lengteklasse`, `levensstadium`, `levensvorm`, `verschijningsvorm`, `geslacht` | Behaviour; fish length class; life stage; life form; observed form (e.g. floating/submerged); sex. Several are mostly empty, and code meanings are not fully supplied. |
| `limietsymbool`, `meetwaarde`, `eenheid`, `eenheidequivalent`, `eenheidreferentie` | Limit qualifier; result; reported unit; source-specific unit equivalent; reference position/basis for the measurement. |
| `waardebewerkingsmethode`, `kwaliteitsoordeelcode`, `afronding`, `opmerkingmeting` | Value processing method; quality/reliability assessment; rounded flag; free-text field observation. |

## The two GeoJSON location inventories

GeoJSON is a standard way to store map features. Each `Feature` is a point with a property record and point geometry. In these files:

- `locatiecode`: site key for joining.
- `total_observations`: number of observations reported for that site in the source aggregation.
- `parameter_counts`: a text-serialized dictionary mapping each parameter code to its observation count at that site. It is not a table of the measurements themselves.
- `rd_x_original`, `rd_y_original`: original Dutch RD (Rijksdriehoeksmeting) projected grid coordinates, in metres.
- `wgs84_lon`, `wgs84_lat`: longitude and latitude in WGS84 geographic coordinates; these match the point geometry coordinate order `[longitude, latitude]`.
- `geometry`: the point used by mapping software.
- `crs`: coordinate reference system declaration. The files declare CRS84, the longitude/latitude geographic coordinate system.

The FYCHEM and HB inventories have no missing site IDs, coordinates, or aggregate observation totals. Some coordinates repeat across distinct codes, which may mean nearby sites share a mapped point; the inventory alone cannot say why. All 1,321 FYCHEM records and all 4,093 HB records have parameter counts that sum to their `total_observations` value.

## Parameter dictionary: what its columns mean

There are 3,061 parameter rows and 29 metadata columns. The workbook contains definitions, not measurements. `ID` is the best candidate join key. `NAME` is a display name; `SHORT_NAME` a compact display name. Several columns have sparse values because they apply only to particular sources or parameter families.

| Column | Plain-language meaning |
| --- | --- |
| `ID` | Parameter dictionary key; candidate join to `fewsparameter` and GeoJSON parameter keys. |
| `NAME`, `SHORT_NAME` | Long and shorter display labels. Some are blank or say “not to use”; don’t assume every entry is a recommended parameter. |
| `GROUP` | Group/measurement family, often concentration by unit. |
| `TYPE` | Data behaviour: `instantaneous` or `accumulative`; definition is source metadata. |
| `UNIT` | Dictionary’s standard/display unit. `DIMSLS` means dimensionless. Do not assume it always matches a separate export’s unit field without checking. |
| `VALUE_RESOLUTION` | Declared measurement precision/increment. |
| `ALLOW_MISSING` | Whether missing values are allowed by this parameter definition (all rows say `true`). |
| `STANDARD_NAME`, `CELL_METHOD` | Standardized variable name and aggregation method metadata; all say `none` here. |
| `tijdstap` | Dutch “time step”: declared interval such as day (`dag`) or hour (`uur`). Mostly blank. |
| `Bron` | Source system (`HYB`, `FYCHEM`, `KWAN`). |
| `InternalParameterId` | Internal/source-system parameter key; frequently matches `ID` when present. |
| `P_naam`, `P_grootheid`, `P_categorie` | Original parameter name, quantity kind and category metadata. |
| `P_normkader` | Associated standards/policy framework, when applicable. It is not itself an observed result or a pass/fail judgement. |
| `P_parameter`, `P_eenheidequivalent`, `P_eenheidreferentie`, `P_parameterfractie` | Original parameter code, equivalent unit, reference basis and measured fraction/form. |
| `H_MAX`, `H_MIN`, `Z_MAX`, `Z_MIN` | Source-specific upper/lower bounds or warning/limit fields. The export does not define the H/Z distinction; don’t treat them as observed ranges or legal standards without data documentation. |
| `grootheid`, `categorie`, `PAR_ID`, `eenheid` | Alternative/source quantity name, category, source parameter ID and source unit. These are populated for only a small subset of dictionary entries. |

Units in the catalog: `mg/l` = milligrams per litre; `ug/l` = micrograms per litre; `ng/l` = nanograms per litre; `mS/m` = millisiemens per metre (electrical conductivity); `oC` = degrees Celsius; `m`, `cm2`, `m2` = metres/square centimetres/square metres; `l` = litres; `g` = grams; `kg/ha` = kilograms per hectare; `n`, `n/l`, `n/ml`, `n/dl`, `n/ha` = count or count per stated volume/area; `mm3/l` = cubic millimetres per litre; `umol/m2.s` = micromoles per square metre per second (light quantity per area and time); `%` = percent; `/m` = inverse metres, an attenuation/extinction measure; `graad` = degrees; `FTU` = Formazin Turbidity Units; `DIMSLS` = dimensionless score/category; `wb` is a Tansley cover-abundance scale code in one parameter definition. A unit label describes the intended quantity; it cannot fix mislabeled source values.

## What the parameter codes tell you

The code is a compact name; the dictionary `NAME` and `UNIT` give the most readable interpretation. Suffixes often hint at the unit or variant (`_mg/l`, `_ug/l`, `_m`, `_n`, `_%`). `nf` in chemistry codes/names means “na filtratie” (after filtration). Codes such as `T_oC`, `pH`, `O2_mg/l`, `Ntot_mgN/l`, `Ptot_mgP/l`, `Cl_mg/l` refer respectively to temperature, acidity/alkalinity scale, dissolved oxygen, total nitrogen, total phosphorus and chloride. The chemistry list also includes nutrients, ions, metals, bacteria, algae pigments, clarity, oxygen demand, pesticides, industrial compounds and medicines. Individual names and their source counts are preserved in the complete catalogs below; formulas and naming are not standardized consistently enough to infer an unknown abbreviation safely.

The biological catalog describes:

- **Aquatic vegetation**: plant cover (`PTN_BEDKG_%`), cover scales (`PTN_BEDKG_TansleyS`, `PTN_BEDKG_NatS`, `PTN_BEDKG_RwsS`), plant width/length fractions, and groups such as emergent, floating-leaf, duckweed and submerged plants.
- **Fish**: counts, biomass and density by length class (`VSLC_n`, `_g`, `_n/ha`, `_kg/ha`), plus incidental fish, catch factors and fish ecological guilds.
- **Small aquatic organisms**: macroinvertebrates/macrofauna (`MEA`, `MACEV`), phytoplankton (`FPA`), zooplankton (`ZPT`/`ZOOPT`), diatoms (`DTA`), nematodes (`NEMTD`), algae and amphibians (`AMFBE`). Suffixes state whether the value is a count, density, volume or mass where documented.
- **Habitat and sampling setup**: water depth/clarity, sample width/length/area/volume, mud/silt thickness, bank slope, substrate/soil, flow, shading and photos.
- **Water chemistry/field observations**: temperature, pH, conductivity, chlorophyll, pheophytin, suspended solids, visible color/smell/dirt, and several measurements made at locations where submerged plants end (`grensWTP`).

In the catalogs, the exact parameter name is the dictionary’s Dutch/source label and each row’s count is its occurrence count. The sample CSV’s counts are rows. GeoJSON counts are aggregate source counts. Counts tell you coverage, not whether a reading was high, low, safe or environmentally good.

## Important cautions before analysis

1. **Check source quality and units.** The overview summarizes raw strings and numeric ranges without cleaning. The Berlagebrug flow series has an extreme minimum. The sample biological values range from −999 to 740,030; this could include parameter-specific encodings or sentinel values, but the overview cannot identify which. Check `limietsymbool`, `kwaliteitsoordeelcode`, parameter, unit and source protocol before using such values.
2. **Do not merge on dates alone.** Biological records contain many repeated dates and multiple rows per sample. Join samples with `monsterident`, sites with `locatiecode`, and parameter meanings with the parameter key; check whether a join multiplies records.
3. **Do not merge unlike units or variants.** The same substance can have filtered/unfiltered variants, different units, or different methods. Convert only after checking the exact dictionary definition and protocol.
4. **Do not mistake aggregate inventories for raw data.** The GeoJSON files can map sites and summarize parameter coverage, but cannot produce a chemistry or biology time series.
5. **Do not assume blanks are zero.** Empty site height fields, taxon fields, current programme fields and parameter metadata indicate absent information in that row.
6. **Interpret category/quality codes through the applicable codebook.** This export contains shorthand values but not every code definition; the Aquo quality table can change over time.

---

# Complete original overview

The remainder reproduces `data_overview.md` so every field profile, count, parameter name, unit, overlap and source caveat is retained alongside this explanation.

# HydroNet data overview

Generated from all rows in the supported files in this directory. Empty means a blank/null cell; numeric ranges exclude non-finite values. Values are summarized as stored, without unit conversion or quality filtering.

| File | Bytes |
| --- | --- |
| Amstelsluizen_waterhoogte.csv | 277447 |
| Berlagebrug_debiet_waterhoogte.csv | 159004 |
| FYCHEM_unique_locations_with_measurements.geojson | 1845367 |
| HB_sampled50locations.csv | 6098900 |
| HB_unique_locations_with_measurements.geojson | 2715968 |
| Parameter_uitleg.xlsx | 271228 |