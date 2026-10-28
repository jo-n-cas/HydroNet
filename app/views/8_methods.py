import json
import re

import streamlit as st

from components import captions, data
from hydronet.config import repo_path

ctx = st.session_state["ctx"]
b, cfg = ctx.bundle, data.settings()

st.title("Methods & limitations")

st.markdown("## Limitations")
instr = repo_path("HYDRONET_INSTRUCTIONS.md")
text = instr.read_text() if instr.exists() else ""
m = re.search(r"## 8\. Limitations.*?\n(.*?)\n---", text, re.S)
st.markdown(m.group(1).strip() if m else "_Limitations section not found in HYDRONET_INSTRUCTIONS.md._")

st.markdown("## How to read this tool")
st.markdown(
    f"- {captions.tag('observed')} directly from the data. {captions.tag('assumed')} assumptions or indicative "
    "orderings.\n"
    "- **Counts are not results.** The location inventories report how often something was measured, not "
    "what was found.\n"
    "- **No KRW norms are used.** No class boundaries or status are computed; none were available.\n"
    "- **Flagged values are kept** and drawn as orange crosses; nothing is removed silently "
    "(rejected rows are listed in each view's 'About this view').\n"
    "- **Every figure states its settings**, so a screenshot documents itself.", unsafe_allow_html=True)

st.markdown("## Key analysis choices")
st.markdown(
    f"- Amstel corridor: OSM centreline (22.0 km, Amstelhoek → Binnen-Amstel); pipeline keeps locations within "
    f"**{cfg['amstel']['max_distance_m']} m**; the UI offers {', '.join(map(str, cfg['amstel']['ui_buffer_options_m']))} m "
    "as a sensitivity view.\n"
    f"- 'Near a plant': within **{cfg['pressures']['nearby_station_buffer_m']:,} m** of the plant site "
    "(placeholder, not a norm).\n"
    f"- Amstel-linked plants: {', '.join(cfg['pressures']['amstel_linked_rwzi'])} (from public sources; assumed).\n"
    "- Effluent metrics are matched on quantity + parameter + unit; pulse volumes are not flows.\n"
    "- Parameter groups: `config/parameter_groups.yaml` (draft, to be reviewed by the team's marine biologist).")

st.markdown("## Data source in use")
st.markdown(f"`ui.data_dir = {cfg['ui']['data_dir']}` · {'SYNTHETIC fixtures' if b.synthetic else 'processed outputs'}")
if b.problems:
    st.markdown("**Unavailable inputs:**\n" + "\n".join(f"- {v}" for v in b.problems.values()))
with st.expander("Pipeline manifest"):
    st.code(json.dumps(b.manifest, indent=2) if b.manifest else "pipeline_manifest.json not found", language="json")

st.markdown("## Decisions log")
dec = repo_path("docs/DECISIONS.md")
with st.expander("docs/DECISIONS.md", expanded=False):
    st.markdown(dec.read_text() if dec.exists() else "_docs/DECISIONS.md not found._")
st.caption("Map data © OpenStreetMap contributors (ODbL).")
