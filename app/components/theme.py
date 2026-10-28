"""Visual system: paper-like CSS, palette, marker vocabulary and the Plotly template."""

from __future__ import annotations

import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st

PAPER = "#FAF8F3"
INK = "#1A1A1A"
MUTED = "#5F5B53"          # secondary text; contrast on PAPER > 6:1
HAIRLINE = "#D9D5CC"
ZERO_GREY = "#BDBDBD"
ACCENT = "#C2410C"          # selection / highlight only
OVERLAP_FILL = "rgba(26,26,26,0.06)"

# viridis stops (colorblind-safe, perceptually uniform)
VIRIDIS = ["#440154", "#482878", "#3E4989", "#31688E", "#26828E", "#1F9E89", "#35B779", "#6DCD59",
           "#B4DE2C", "#FDE725"]

SERIF = '"Source Serif 4", "Source Serif Pro", "Iowan Old Style", Georgia, "Times New Roman", serif'
SANS = 'Inter, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif'

CSS = f"""
<style>
  html, body, [class*="css"] {{ font-family: {SANS}; }}
  h1, h2, h3, h4 {{ font-family: {SERIF} !important; font-weight: 600 !important; color: {INK};
                   letter-spacing: -0.005em; }}
  h1 {{ font-size: 1.9rem !important; margin-bottom: .2rem !important; }}
  h2 {{ font-size: 1.35rem !important; border-top: 1px solid {HAIRLINE}; padding-top: .9rem !important;
       margin-top: 1.2rem !important; }}
  h3 {{ font-size: 1.1rem !important; }}
  .block-container {{ padding-top: 2.2rem; max-width: 1280px; }}
  [data-testid="stSidebar"] {{ border-right: 1px solid {HAIRLINE}; }}
  [data-testid="stMetric"] {{ border-top: 1px solid {HAIRLINE}; padding-top: .4rem; }}
  [data-testid="stExpander"] details {{ border: none; border-top: 1px solid {HAIRLINE}; border-radius: 0; }}
  .hn-caption {{ font-size: .78rem; color: {MUTED}; line-height: 1.35; margin: .15rem 0 .6rem 0; }}
  .hn-nline {{ font-size: .8rem; color: {INK}; font-variant-numeric: tabular-nums; margin: .1rem 0; }}
  .hn-note {{ font-size: .8rem; color: {MUTED}; font-style: italic; border-left: 2px solid {HAIRLINE};
             padding-left: .6rem; margin: .4rem 0 .8rem 0; }}
  .hn-tag {{ display: inline-block; font-size: .68rem; letter-spacing: .06em; text-transform: uppercase;
            padding: 0 .35rem; margin-right: .35rem; color: {INK}; vertical-align: 1px; }}
  .hn-tag-observed {{ border: 1px solid {INK}; }}
  .hn-tag-assumed {{ border: 1px dashed {MUTED}; color: {MUTED}; font-style: italic; }}
  .hn-banner {{ border: 1px solid {ACCENT}; color: {ACCENT}; padding: .35rem .7rem; font-size: .85rem;
               margin-bottom: .8rem; }}
  .hn-empty {{ border-top: 1px solid {HAIRLINE}; border-bottom: 1px solid {HAIRLINE}; padding: .7rem 0;
              font-size: .9rem; color: {INK}; margin: .5rem 0 1rem 0; }}
  .hn-empty b {{ font-weight: 600; }}
  .hn-card {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: .2rem 1.6rem;
             border-top: 1px solid {INK}; border-bottom: 1px solid {HAIRLINE}; padding: .7rem 0; }}
  .hn-card .k {{ font-size: .72rem; color: {MUTED}; text-transform: uppercase; letter-spacing: .05em; }}
  .hn-card .v {{ font-family: {SERIF}; font-size: 1.45rem; font-variant-numeric: tabular-nums; }}
  .hn-card .s {{ font-size: .75rem; color: {MUTED}; }}
  .hn-legend span {{ margin-right: 1.1rem; font-size: .78rem; color: {INK}; white-space: nowrap; }}
  .hn-legend svg {{ vertical-align: -2px; margin-right: .25rem; }}
  :focus-visible {{ outline: 2px solid {ACCENT} !important; outline-offset: 2px; }}
</style>
"""


def apply() -> None:
    """Inject CSS and register the Plotly template (call once per run)."""
    st.markdown(CSS, unsafe_allow_html=True)
    _register_plotly_template()


def viridis(t: float) -> str:
    """Colour for t in [0, 1] by linear interpolation of the viridis stops."""
    t = min(max(float(t), 0.0), 1.0) * (len(VIRIDIS) - 1)
    i = int(t)
    if i >= len(VIRIDIS) - 1:
        return VIRIDIS[-1]
    a, b, f = VIRIDIS[i], VIRIDIS[i + 1], t - i
    ca = [int(a[k:k + 2], 16) for k in (1, 3, 5)]
    cb = [int(b[k:k + 2], 16) for k in (1, 3, 5)]
    return "#" + "".join(f"{round(x + (y - x) * f):02X}" for x, y in zip(ca, cb))


def _register_plotly_template() -> None:
    if "hydronet" in pio.templates:
        return
    axis = dict(showgrid=False, zeroline=False, showline=True, linecolor=HAIRLINE, linewidth=1,
                ticks="outside", tickcolor=HAIRLINE, ticklen=3, tickfont=dict(size=11, color=MUTED),
                title=dict(font=dict(size=11, color=MUTED)))
    pio.templates["hydronet"] = go.layout.Template(layout=dict(
        paper_bgcolor=PAPER, plot_bgcolor=PAPER,
        font=dict(family=SANS, size=12, color=INK),
        title=dict(font=dict(family=SERIF, size=14, color=INK), x=0, xanchor="left"),
        xaxis=axis, yaxis={**axis, "showgrid": True, "gridcolor": "#ECE8DF", "gridwidth": 1},
        margin=dict(l=56, r=16, t=36, b=40), showlegend=False,
        hoverlabel=dict(bgcolor="white", bordercolor=HAIRLINE, font=dict(family=SANS, size=12, color=INK)),
        colorway=[INK, VIRIDIS[3], VIRIDIS[6], ACCENT, MUTED],
    ))
    pio.templates.default = "hydronet"


def shape_svg(kind: str, color: str = INK, size: int = 11, ring: bool = False) -> str:
    """Inline SVG of a legend marker: chem = circle, bio = square, both = diamond."""
    h = size / 2
    if kind == "chem":
        body = f'<circle cx="{h}" cy="{h}" r="{h - 1.5}" fill="{color}"/>'
    elif kind == "bio":
        body = f'<rect x="1.5" y="1.5" width="{size - 3}" height="{size - 3}" fill="{color}"/>'
    elif kind == "both":
        body = f'<polygon points="{h},0.8 {size - 0.8},{h} {h},{size - 0.8} 0.8,{h}" fill="{color}"/>'
    elif kind == "rwzi":
        body = f'<polygon points="{h},1 {size - 1},{size - 1} 1,{size - 1}" fill="white" stroke="{INK}" stroke-width="1.4"/>'
    elif kind == "sensor":
        body = f'<rect x="{h - 1.5}" y="0.5" width="3" height="{size - 1}" fill="{INK}"/>'
    else:
        body = f'<circle cx="{h}" cy="{h}" r="{h - 2}" fill="none" stroke="{color}" stroke-width="2"/>'
    if ring:
        body += f'<circle cx="{h}" cy="{h}" r="{h - 0.8}" fill="none" stroke="{ACCENT}" stroke-width="1.4"/>'
    return f'<svg width="{size}" height="{size}" aria-hidden="true">{body}</svg>'
