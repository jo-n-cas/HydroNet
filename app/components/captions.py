"""Small text components: tags, n-lines, analysis-settings captions, notes."""

from __future__ import annotations

from collections.abc import Iterable

import pandas as pd
import streamlit as st

CAUSATION_NOTE = ("Association shown, not causation. Being near each other or measured in the same "
                  "period does not show that one affects the other.")


def tag(kind: str) -> str:
    """HTML for an OBSERVED or ASSUMED / INDICATIVE tag."""
    if kind == "observed":
        return '<span class="hn-tag hn-tag-observed" title="Directly from the data">Observed</span>'
    return ('<span class="hn-tag hn-tag-assumed" title="Assumption or indicative ordering, '
            'not measured">Assumed / indicative</span>')


def tagged(text: str, kind: str) -> None:
    st.markdown(f'<div class="hn-nline">{tag(kind)}{text}</div>', unsafe_allow_html=True)


def n_line(n_obs: int | None = None, n_loc: int | None = None, start=None, end=None,
           extra: str | None = None) -> None:
    """'n = X observations · Y locations · date span' under a figure."""
    parts = []
    if n_obs is not None:
        parts.append(f"n = {n_obs:,} observations")
    if n_loc is not None:
        parts.append(f"{n_loc:,} locations")
    if start is not None and end is not None and not pd.isna(start):
        parts.append(f"{pd.Timestamp(start):%Y-%m-%d} – {pd.Timestamp(end):%Y-%m-%d}")
    if extra:
        parts.append(extra)
    st.markdown(f'<div class="hn-nline">{" · ".join(parts)}</div>', unsafe_allow_html=True)


def current_settings(keys: Iterable[str] | None = None) -> dict[str, str]:
    """The analysis choices that affect what is shown, from session state."""
    s = st.session_state
    d0, d1 = s.get("date_range", (None, None))
    all_ = {
        "group": s.get("group_label", "-"),
        "parameter": s.get("parameter") or "all in group",
        "buffer": f"{s.get('buffer_m', '-')} m",
        "stretch": "km {:.1f}–{:.1f}".format(*s.get("stretch_km", (0, 0))),
        "source": s.get("source", "both"),
        "dates": f"{d0}–{d1}" if d0 else "-",
        "quality codes": ",".join(str(q) for q in s.get("quality_codes", [])) or "none",
        "data": s.get("data_label", "-"),
    }
    return all_ if keys is None else {k: all_[k] for k in keys}


def settings_caption(keys: Iterable[str] | None = None, extra: str | None = None) -> None:
    """Self-documenting line under a figure: the choices currently applied."""
    text = " · ".join(f"{k}={v}" for k, v in current_settings(keys).items())
    if extra:
        text += f" · {extra}"
    st.markdown(f'<div class="hn-caption">Settings: {text}</div>', unsafe_allow_html=True)


def note(text: str) -> None:
    st.markdown(f'<div class="hn-note">{text}</div>', unsafe_allow_html=True)


def causation_note() -> None:
    note(CAUSATION_NOTE)


def figure_caption(text: str) -> None:
    """Plain-language description of a figure (doubles as alt text for screen readers)."""
    st.markdown(f'<div class="hn-caption" role="note">Figure: {text}</div>', unsafe_allow_html=True)
