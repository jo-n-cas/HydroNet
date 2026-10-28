# Structural monitoring locations

Sites from all three input files are grouped when **every pair** of RD-coordinate points is within 250 metres. Each group gets one `structural_location_id`; original `locatiecode` values remain available. A chain wider than the threshold is split.

A grouped location is structural when at least one biological parameter has observations on 4 distinct dates in 2 calendar years. Dates from different site codes in a group are combined; multiple rows on one date count as one visit. Only rows for qualifying group/parameter series are retained.

Across all inputs, 4,971 unique site codes form 2,071 groups; 1,418 groups contain multiple codes.

**Result:** 18 structural grouped locations, 158 qualifying parameter series, and 7,654 of 13,340 biological CSV rows retained. They contain 55 original HB site features.

The FYCHEM subset has 2 sites in those groups with at least 5 aggregate observations for one parameter. These are chemistry **candidates**: FYCHEM has no measurement dates, so its counts do not establish repeated measurements over time. Original GeoJSON aggregate counts describe the full inventory.

`location_groups.csv` maps every source code to a grouped location and source files. `structural_series.csv` gives dates and source codes for qualifying series. `structural_locations.geojson` has one point per group, placed at its first source site. The other GeoJSON outputs retain source points and add `structural_location_id`.

| Structural location | Source site codes | Qualifying parameters | Dates | Years | Chemistry candidates |
| --- | --- | ---: | ---: | ---: | --- |
| `LOC_BBO125` | `BBO125`, `AVW145` | 11 | 5 | 5 | none |
| `LOC_BKP114` | `BKP114`, `BKP113`, `BKP112` | 15 | 7 | 7 | none |
| `LOC_BKP124` | `BKP124`, `BKP125`, `BKP189`, `BKP128`, `BKP205` | 15 | 6 | 6 | none |
| `LOC_BLV100` | `BLV100`, `GWV833` | 12 | 5 | 5 | none |
| `LOC_BOT173` | `BOT173`, `BOT308`, `BOT193`, `BOT292`, `BOT192`, `BOT244`, `BOT194`, `BOT255`, `BOT191`, `BOT324`, `BOT293` | 9 | 12 | 10 | none |
| `LOC_GWV377` | `GWV377` | 15 | 7 | 5 | none |
| `LOC_GWV786` | `GWV786`, `GWV785` | 15 | 8 | 8 | none |
| `LOC_GWV835` | `GWV835`, `GWV850`, `GWV856` | 9 | 4 | 4 | none |
| `LOC_HBP216` | `HBP216`, `HBP170`, `HBP215`, `HBP245`, `HBP214`, `HBP213` | 4 | 16 | 16 | none |
| `LOC_MAP104` | `MAP104` | 12 | 4 | 4 | none |
| `LOC_NBW201` | `NBW201`, `AMS177`, `AMS175`, `GWV734` | 4 | 4 | 4 | none |
| `LOC_NLP115` | `NLP115` | 3 | 4 | 4 | none |
| `LOC_OBL105` | `OBL105` | 11 | 5 | 5 | `OBL105` |
| `LOC_PWV102` | `PWV102`, `PWV101`, `PWV148` | 4 | 4 | 4 | none |
| `LOC_PWV150` | `PWV150`, `PWV114` | 4 | 4 | 4 | none |
| `LOC_PZH120` | `PZH120` | 1 | 4 | 4 | none |
| `LOC_RLA109` | `RLA109`, `DBR100`, `SBI195`, `RLA112` | 12 | 4 | 4 | `RLA109` |
| `LOC_WAV102` | `WAV102`, `BOT223`, `BOT130` | 2 | 5 | 5 | none |

The daily water-level/flow CSVs have no `locatiecode` link to these sites. Proximity alone does not establish whether a group lies on the Amstel river or represents the same water body.
