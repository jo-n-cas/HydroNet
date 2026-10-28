"""'About this view' panel and figure exports (table CSV + settings/provenance JSON)."""

from __future__ import annotations

import json
from collections.abc import Iterable

import pandas as pd
import streamlit as st

from .captions import current_settings


def about_view(view_id: str, bundle, *, sources: Iterable[str], steps: Iterable[str],
               outputs: Iterable[str], table: pd.DataFrame | None = None) -> None:
    """Collapsible provenance: source files, processing steps, row counts, run date, exports."""
    manifest = bundle.manifest
    rejected = bundle.get("rejected_values.parquet")
    with st.expander("About this view"):
        st.markdown("**Source files** · " + " · ".join(f"`{s}`" for s in sources))
        st.markdown("**Processing** · " + " → ".join(steps))
        rows = []
        for out in outputs:
            info = (manifest or {}).get("outputs", {}).get(out, {})
            rows.append({"output": out, "rows before cleaning": info.get("rows_in"),
                         "rows after cleaning": info.get("rows_out"),
                         "rejected": ", ".join(f"{k}: {v}" for k, v in info.get("rejected", {}).items()) or None})
        st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
        if manifest:
            st.caption(f"Pipeline run: {manifest.get('run_at', 'unknown')}"
                       + (" · SYNTHETIC fixtures" if manifest.get("synthetic") else ""))
        else:
            st.caption("Run information not available: `pipeline_manifest.json` is missing in the data directory.")
        if rejected is not None and not rejected.empty:
            st.caption("Rejected rows by reason (all outputs): " + ", ".join(
                f"{k}: {v}" for k, v in rejected["reason"].value_counts().items()))
        meta = {"view": view_id, "settings": current_settings(), "sources": list(sources),
                "steps": list(steps), "outputs": list(outputs), "data_dir": str(bundle.data_dir),
                "pipeline_run_at": (manifest or {}).get("run_at"), "synthetic": bundle.synthetic}
        c1, c2 = st.columns(2)
        if table is not None:
            c1.download_button("Export table (CSV)", table.to_csv(index=False).encode(),
                               file_name=f"hydronet_{view_id}.csv", mime="text/csv", key=f"csv_{view_id}")
        c2.download_button("Export settings (JSON)", json.dumps(meta, indent=2, default=str).encode(),
                           file_name=f"hydronet_{view_id}_settings.json", mime="application/json",
                           key=f"json_{view_id}")


def empty_state(reason: str, filled_by: str) -> None:
    """Explain why a view is empty and what data would fill it."""
    st.markdown(f'<div class="hn-empty"><b>Empty because</b> {reason}<br>'
                f'<b>Would be filled by</b> {filled_by}</div>', unsafe_allow_html=True)
