# Demo script: the phosphorus chain on the Amstel

A walkthrough of about 8 minutes. It works on fixtures (layout) and on real outputs (switch `ui.data_dir`). Numbers marked *(real)* come from the real inventories and files, checked on 2026-10-28. On fixtures, the app shows synthetic numbers instead.

**Story in one sentence:** we follow phosphorus from a wastewater plant on the Amstel, to what is monitored in the river next to it, to the biology nearby, and we show honestly where the data stop.

## 0. Set-up (before the audience arrives)
- Run `streamlit run app/streamlit_app.py` and use the defaults: Tier 1, `Ptot_mgP/l`, 100 m buffer, the whole river.
- Open **Overview**.

## 1. Overview: what this tool is (1 min)
- Read the "It can say / It cannot say" lines aloud.
- **Data card:** 76 locations within 100 m of the Amstel *(real)*, against 5,414 AGV-wide. Point out how little of AGV's monitoring is on the river, and that raw values exist for only 1 Amstel location (VGD125, biology) *(real)*.
- **Time-span chart:** biology runs 1998–2024 and RWZI effluent 2021–2025 *(real)*. Every comparison is limited to the 2021–2024 overlap.
- **Observed / Assumed tags:** "every figure tells you which parts are measured and which are our assumptions."

## 2. Coverage map: where is phosphorus measured? (1.5 min)
- **The map:** the river runs from Amstelhoek (km 0) to Amsterdam (km 22). Marker size and colour show how many `Ptot_mgP/l` observations each location has.
- **Click a location** near Uithoorn, then show that the selection carries over to Station detail.
- **The strip on the right:** move the river-stretch slider to km 0–5 and show how the coverage per group changes.

## 3. Amstel corridor: the river as a line (1.5 min)
- **Top track:** RWZI Uithoorn sits at km 1.4 (0.8 km from the river) and Amstelveen at km 15.5 (1.0 km) *(real)*. The hydrology sensors are at km 19.2 (Berlagebrug) and km 21.0 (Amstelsluizen).
- **Rows:** coverage per parameter group along the river. The medicine and PFAS rows only have dots at the two river ends (km 0.75 and km 21.2) *(real)*.
- **Buffer sensitivity:** 30 / 58 / 76 locations at 25 / 50 / 100 m *(real)*. "What counts as the river is a choice, and we show it."

## 4. Phosphorus chain: the demo (3 min)
Open **Phosphorus chain** (default plant: Uithoorn).
1. **Pressure.** Uithoorn's daily effluent volume is shown (about 8,900 m³/day median) *(real)*. Effluent phosphate is **not measured** at Uithoorn. None of the Amstel-linked plants has effluent phosphate in the files; only Amsterdam West, Blaricum, Huizen and Weesp do *(real)*. Say it plainly: this is a data gap, not a finding.
2. **Water chemistry near the plant.** The grid shows which Tier 1 parameters are measured at the corridor locations within ±3 km, ordered upstream → downstream. These are counts only: "we know phosphorus is measured here; we cannot yet show how much."
3. **Biology nearby.** This is the nearest corridor location with raw biology values (on real data: VGD125, about 11 km along the river from Uithoorn's river km, 63 m from the centreline), on the same time axis with the overlap band.
- Close with "What this chain can and cannot say", and the causation note.

## 5. Data gaps: what we need from AGV (1 min)
- **Dumbbell chart:** for each group, filled dots show the observations AGV has and open dots the values we have.
- **Priorities:**
  1. raw Tier 1 FYCHEM values for the Amstel corridor
  2. effluent phosphate for Uithoorn, De Ronde Venen and Amstelveen
  3. values for the medicine and PFAS pairs at km 0.75 and km 21.2
- **Export `DATA_REQUEST.md`.**

## 6. Methods (30 s)
- Point to the limitations, the key analysis choices and the decisions log.
- Every screenshot carries its own settings caption.

## Likely questions
- **"Is the river status bad?"** We do not compute KRW status: no norms or raw chemistry values are in the prototype.
- **"Does Uithoorn pollute the Amstel?"** The tool shows proximity and coverage, not effect. The discharge point is not verified and no concentrations are available.
- **"Why 100 m?"** It is a team decision. Many river stations lie 20–45 m from the centreline because the river is wide. The sensitivity panel shows the result at 25 m and 50 m.
