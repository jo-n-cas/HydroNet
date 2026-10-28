"""Plotly figures: small multiples, rank-ordered dot plots, flagged values, overlap shading."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from . import theme

FLAG_STYLE = dict(symbol="x-thin-open", size=8, color=theme.ACCENT, line=dict(width=1.5, color=theme.ACCENT))


def overlap_band(fig: go.Figure, start, end, label: str = "overlap", row=None, col=None,
                 annotate: bool = True) -> None:
    """Shade a common period on a time axis, with a direct label."""
    if start is None or end is None:
        return
    kw = {} if row is None else {"row": row, "col": col}
    fig.add_vrect(x0=start, x1=end, fillcolor=theme.OVERLAP_FILL, line_width=0, layer="below", **kw)
    if annotate:
        mid = pd.Timestamp(start) + (pd.Timestamp(end) - pd.Timestamp(start)) / 2
        fig.add_annotation(x=mid, y=1.0, yref="paper", xanchor="center", yanchor="bottom", showarrow=False,
                           text=f"{label} {pd.Timestamp(start):%Y}–{pd.Timestamp(end):%Y}",
                           font=dict(size=10, color=theme.MUTED))


def spans_chart(spans: pd.DataFrame, overlap: tuple | None, overlap_label: str) -> go.Figure:
    """One hairline bar per dataset over time, with the overlap band."""
    fig = go.Figure()
    for i, r in spans.reset_index(drop=True).iterrows():
        fig.add_trace(go.Scatter(x=[r["start"], r["end"]], y=[r["dataset"]] * 2, mode="lines+markers",
                                 line=dict(color=theme.INK, width=3), marker=dict(size=6, color=theme.INK),
                                 hovertemplate=f"{r['dataset']}: %{{x|%Y-%m-%d}}<extra></extra>"))
        fig.add_annotation(x=r["end"], y=r["dataset"], xanchor="left", showarrow=False, xshift=6,
                           text=f"{pd.Timestamp(r['start']):%Y}–{pd.Timestamp(r['end']):%Y}",
                           font=dict(size=10, color=theme.MUTED))
    if overlap:
        overlap_band(fig, *overlap, label=overlap_label)
    fig.update_layout(height=60 + 34 * len(spans), margin=dict(l=150, r=70, t=30, b=30))
    fig.update_yaxes(showgrid=False, autorange="reversed")
    return fig


def dot_strip(df: pd.DataFrame, label_map: dict[str, str], highlight: str | None = None,
              title: str = "") -> go.Figure:
    """Rank-ordered dot plot of observations per group (log x), direct-labelled with locations."""
    d = df.sort_values("n_observations", ascending=True)
    labels = [f"{label_map.get(g, g)} · {n} loc." for g, n in zip(d["parameter_group"], d["n_locations"])]
    colors = [theme.ACCENT if g == highlight else theme.INK for g in d["parameter_group"]]
    fig = go.Figure(go.Scatter(
        x=d["n_observations"], y=labels, mode="markers", marker=dict(size=8, color=colors),
        customdata=np.stack([d["n_locations"], d["n_parameters"]], axis=-1),
        hovertemplate="%{y}<br>%{x:,} observations · %{customdata[0]} locations · "
                      "%{customdata[1]} parameters<extra></extra>"))
    for x, y in zip(d["n_observations"], labels):
        fig.add_shape(type="line", x0=1, x1=x, y0=y, y1=y, line=dict(color=theme.HAIRLINE, width=1))
    xmax = max(10, float(d["n_observations"].max() or 10))
    fig.update_xaxes(type="log", title="observations (log)", range=[0, math.log10(xmax) + 0.15])
    fig.update_layout(height=max(160, 24 * len(d) + 70), title=title, margin=dict(l=10, r=16, t=16, b=44))
    fig.update_yaxes(showgrid=False, automargin=True, tickfont=dict(size=11, color=theme.INK))
    return fig


def bio_small_multiples(bio: pd.DataFrame, x_range=None, overlap=None) -> go.Figure:
    """One panel per parameter (shared x), points styled by limit / quality / QA flags."""
    params = sorted(bio["parameter"].unique())
    fig = make_subplots(rows=len(params), cols=1, shared_xaxes=True, vertical_spacing=0.06,
                        subplot_titles=[f"{p} ({bio.loc[bio.parameter == p, 'unit'].iloc[0]})" for p in params])
    for i, p in enumerate(params, start=1):
        d = bio[bio["parameter"] == p].copy()
        d["dt"] = pd.to_datetime(d["datetime"])
        normal = d[d["limit_flag"].isna() & d["qa_flag"].isna()]
        low_q = normal["quality_code"].fillna(0) != 0
        for sub, opacity, name in [(normal[~low_q], 0.9, "quality code 0"),
                                   (normal[low_q], 0.35, "quality code 3/9 (meaning unconfirmed)")]:
            fig.add_trace(go.Scatter(
                x=sub["dt"], y=sub["value"], mode="markers", name=name,
                marker=dict(size=6, color=theme.INK, opacity=opacity),
                customdata=np.stack([sub["taxon"].fillna(""), sub["quality_code"].astype(str)], axis=-1)
                if len(sub) else None,
                hovertemplate="%{x|%Y-%m-%d} · %{y}<br>%{customdata[0]} · quality code %{customdata[1]}"
                              "<extra></extra>"), row=i, col=1)
        lim = d[d["limit_flag"].notna()]
        if len(lim):
            fig.add_trace(go.Scatter(
                x=lim["dt"], y=lim["value"], mode="markers", name="limit symbol",
                marker=dict(symbol=["triangle-up-open" if f == ">" else "triangle-down-open"
                                    for f in lim["limit_flag"]], size=9, color=theme.INK),
                hovertemplate="%{x|%Y-%m-%d} · value reported relative to a limit<extra></extra>"), row=i, col=1)
        qa = d[d["qa_flag"].notna()]
        if len(qa):
            fig.add_trace(go.Scatter(x=qa["dt"], y=qa["value"], mode="markers", name="QA flag",
                                     marker=FLAG_STYLE, text=qa["qa_flag"],
                                     hovertemplate="%{x|%Y-%m-%d} · %{y} · flagged: %{text}<extra></extra>"),
                          row=i, col=1)
        if overlap:
            overlap_band(fig, *overlap, row=i, col=1, annotate=(i == 1), label="overlap with RWZI data")
    fig.update_layout(height=170 * len(params) + 60, margin=dict(l=56, r=16, t=40, b=36))
    fig.update_annotations(font=dict(size=11, color=theme.MUTED), selector=dict(yref="paper"))
    if x_range:
        fig.update_xaxes(range=list(x_range))
    return fig


def hydrology_chart(hyd: pd.DataFrame, overlap=None, x_range=None) -> go.Figure:
    """Water level (both sensors) and Q as aligned small multiples; flagged values marked, not removed."""
    panels = [("Amstelsluizen", "level_mNAP", "Amstelsluizen · water level (m NAP)"),
              ("Berlagebrug", "level_mNAP", "Berlagebrug · water level (m NAP)"),
              ("Berlagebrug", "Q_m3_per_day", "Berlagebrug · Q (m³/day, sign convention unknown)")]
    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.07,
                        subplot_titles=[p[2] for p in panels])
    for i, (site, q, _) in enumerate(panels, start=1):
        d = hyd[(hyd["site"] == site) & (hyd["quantity"] == q)].copy()
        d["date"] = pd.to_datetime(d["date"])
        ok, flagged = d[d["qa_flag"].isna()], d[d["qa_flag"].notna()]
        fig.add_trace(go.Scattergl(x=ok["date"], y=ok["value"], mode="lines",
                                   line=dict(color=theme.INK, width=0.7),
                                   hovertemplate="%{x|%Y-%m-%d} · %{y:.3f}<extra></extra>"), row=i, col=1)
        if len(flagged):
            fig.add_trace(go.Scatter(x=flagged["date"], y=flagged["value"], mode="markers", marker=FLAG_STYLE,
                                     text=flagged["qa_flag"],
                                     hovertemplate="%{x|%Y-%m-%d} · %{y:,.3f} · flagged: %{text}<extra></extra>"),
                          row=i, col=1)
            fig.add_annotation(x=flagged["date"].iloc[0], y=flagged["value"].iloc[0], row=i, col=1,
                               text=f"{len(flagged)} flagged value(s), kept", showarrow=True, arrowhead=0,
                               ax=40, ay=-18, font=dict(size=10, color=theme.ACCENT), arrowcolor=theme.ACCENT)
        if overlap:
            overlap_band(fig, *overlap, row=i, col=1, annotate=(i == 1), label="common period")
    fig.update_layout(height=560, margin=dict(l=70, r=16, t=40, b=36))
    fig.update_annotations(font=dict(size=11), selector=dict(yref="paper"))
    if x_range:
        fig.update_xaxes(range=list(x_range))
    return fig


def corridor_longitudinal(corr: pd.DataFrame, counts: pd.DataFrame, group_rows: list[tuple[str, str]],
                          nodes: pd.DataFrame, links: pd.DataFrame, river_km: float,
                          selected: str | None, stretch_km: tuple[float, float]) -> go.Figure:
    """Stations along chainage (x, km). Top track: RWZIs and sensors with light proximity edges.

    One aligned row per parameter group; dot size = observations (sqrt), grey ring = 0.
    """
    n = len(group_rows) + 1
    fig = make_subplots(rows=n, cols=1, shared_xaxes=True, vertical_spacing=0.012,
                        row_heights=[1.6] + [1] * (n - 1))
    # top track: nodes; labels of nodes closer than 2 km are pushed apart (left / right)
    nodes = nodes.sort_values("km").reset_index(drop=True) if len(nodes) else nodes
    pos = ["top center"] * len(nodes)
    for k in range(1, len(nodes)):
        if nodes.loc[k, "km"] - nodes.loc[k - 1, "km"] < 2:
            pos[k - 1], pos[k] = "top left", "top right"
    for (_, r), tpos in zip(nodes.iterrows(), pos):
        sym = "triangle-up-open" if r["kind"] == "rwzi" else "line-ns-open"
        fig.add_trace(go.Scatter(x=[r["km"]], y=[1], mode="markers+text", text=[r["label"]],
                                 textposition=tpos, textfont=dict(size=10),
                                 marker=dict(symbol=sym, size=12, color=theme.INK, line=dict(width=1.6)),
                                 hovertemplate=f"{r['hover']}<extra></extra>"), row=1, col=1)
    st_km = dict(zip(corr["station_id"], corr["chainage_m"] / 1000))
    for _, l in links.iterrows():
        if l["station_id"] in st_km:
            fig.add_trace(go.Scatter(x=[l["node_km"], st_km[l["station_id"]]], y=[1, 0], mode="lines",
                                     line=dict(color=theme.HAIRLINE, width=1), hoverinfo="skip"), row=1, col=1)
    fig.add_trace(go.Scatter(x=corr["chainage_m"] / 1000, y=[0] * len(corr), mode="markers",
                             marker=dict(size=4, color=theme.MUTED), text=corr["station_id"],
                             hovertemplate="%{text} · km %{x:.2f}<extra></extra>"), row=1, col=1)
    fig.update_yaxes(range=[-0.4, 1.9], showticklabels=False, showgrid=False, showline=False, row=1, col=1)

    nmax = float(counts["n_observations"].max()) if len(counts) else 1.0
    for i, (gkey, glabel) in enumerate(group_rows, start=2):
        c = counts[counts["parameter_group"] == gkey].set_index("station_id")["n_observations"]
        x = corr["chainage_m"] / 1000
        vals = corr["station_id"].map(c).fillna(0)
        size = [4 if v == 0 else 5 + 16 * math.sqrt(v / nmax) for v in vals]
        color = [theme.PAPER if v == 0 else (theme.ACCENT if s == selected else theme.INK)
                 for v, s in zip(vals, corr["station_id"])]
        fig.add_trace(go.Scatter(
            x=x, y=[0] * len(corr), mode="markers",
            marker=dict(size=size, color=color, line=dict(width=0.8, color=[
                theme.ACCENT if s == selected else (theme.ZERO_GREY if v == 0 else theme.INK)
                for v, s in zip(vals, corr["station_id"])])),
            customdata=np.stack([corr["station_id"], vals], axis=-1),
            hovertemplate=f"{glabel}<br>%{{customdata[0]}} · km %{{x:.2f}} · %{{customdata[1]:,}} obs<extra></extra>"),
            row=i, col=1)
        fig.update_yaxes(showticklabels=False, showgrid=False, showline=False, range=[-1, 1], row=i, col=1)
        fig.add_annotation(x=0, xref="paper", y=0.5, yref=f"y{i} domain", xanchor="right", showarrow=False,
                           text=glabel.split(" · ")[-1], font=dict(size=10, color=theme.INK), xshift=-6)
    lo, hi = stretch_km
    if lo > 0 or hi < river_km - 0.05:
        fig.add_vrect(x0=lo, x1=hi, fillcolor="rgba(194,65,12,0.07)", line_width=0, layer="below")
    fig.update_xaxes(range=[-0.3, river_km + 0.3], title=None)
    fig.update_xaxes(title="position along the river, km from Amstelhoek (upstream → downstream, indicative)",
                     row=n, col=1)
    fig.update_layout(height=120 + 34 * n, margin=dict(l=250, r=20, t=20, b=50))
    return fig


def rwzi_grid(yearly: pd.DataFrame, gaps: pd.DataFrame, plants: list[tuple[str, str]],
              metrics: dict, x_years: tuple[int, int]) -> go.Figure:
    """Rows = plants, columns = metrics; yearly values with n_days; explicit 'not measured' cells."""
    keys = list(metrics)
    titles = [f"{metrics[k]['label']} ({metrics[k]['yearly']} · {metrics[k]['yearly_unit']})" for k in keys]
    n_rows, n_cols = len(plants), len(keys)
    fig = make_subplots(rows=n_rows, cols=n_cols, shared_xaxes=True, shared_yaxes="columns",
                        horizontal_spacing=0.07, vertical_spacing=0.09 if n_rows < 6 else 0.05,
                        column_titles=titles)
    fig.update_annotations(font=dict(size=11, color=theme.MUTED), yshift=22)   # column titles above row labels
    years = list(range(x_years[0], x_years[1] + 1))
    for i, (inst, label) in enumerate(plants, start=1):
        for j, k in enumerate(keys, start=1):
            n = (i - 1) * n_cols + j
            ax = "" if n == 1 else str(n)
            if j == 1:      # plant label, left-aligned above the row (direct label instead of a legend)
                fig.add_annotation(x=0, y=1, xref="x domain", yref=f"y{ax} domain", xanchor="left",
                                   yanchor="bottom", showarrow=False, text=f"<b>{label}</b>", yshift=4,
                                   font=dict(size=11, color=theme.INK))
            measured = inst in gaps.index and gaps.loc[inst, k] > 0
            if not measured:
                # invisible baseline keeps the empty panel's axes, so the gap is visible as a gap
                fig.add_trace(go.Scatter(x=years, y=[0] * len(years), mode="lines", line=dict(width=0),
                                         hoverinfo="skip"), row=i, col=j)
                fig.add_annotation(x=0.5, y=0.5, xref=f"x{ax} domain", yref=f"y{ax} domain", showarrow=False,
                                   text="not measured", font=dict(size=11, color=theme.MUTED))
                continue
            d = yearly[(yearly["installation"] == inst) & (yearly["metric"] == k)]
            fig.add_trace(go.Scatter(
                x=d["year"], y=d["value"], mode="lines+markers", line=dict(color=theme.INK, width=1),
                marker=dict(size=5, color=theme.INK), customdata=d["n_days"],
                hovertemplate="%{x}: %{y:,.3g} · %{customdata} days<extra></extra>"), row=i, col=j)
    fig.update_xaxes(range=[years[0] - 0.4, years[-1] + 0.4], dtick=1, tickformat="d")
    # shared axes switch autorange off in plotly.js; force it on so each column scales to its data
    fig.update_yaxes(autorange=True, rangemode="tozero", nticks=3)
    fig.update_layout(height=max(260, 110 * n_rows + 90), margin=dict(l=60, r=16, t=70, b=30))
    return fig
