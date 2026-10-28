"""Folium map of the Amstel corridor: stations, centreline, buffer, selected stretch, RWZIs, sensors."""

from __future__ import annotations

import math

import folium
import geopandas as gpd
import pandas as pd
from shapely.ops import substring

from . import theme

TOOLTIP_SEP = " · "


def station_id_from_tooltip(text: str | None) -> str | None:
    """Clicked tooltips start with the station ID (see :func:`build_map`)."""
    if not text:
        return None
    first = str(text).split(TOOLTIP_SEP)[0].strip()
    return first if first and not first.startswith("RWZI") and not first.startswith("Sensor") else None


def _radius(n: float, n_max: float) -> float:
    """Marker radius in px, sqrt-scaled so area is proportional to the count (3 px for zero)."""
    if n <= 0 or n_max <= 0:
        return 3.0
    return 3.5 + 9.5 * math.sqrt(n / n_max)


def _colour(n: float, n_max: float) -> str:
    if n <= 0:
        return theme.ZERO_GREY
    return theme.viridis(math.log1p(n) / math.log1p(n_max)) if n_max > 0 else theme.VIRIDIS[0]


def build_map(ctx, counts: pd.Series, selected: str | None, settings: dict) -> folium.Map:
    """Build the corridor map.

    ``counts``: observations per station for the selected group/parameter (missing = 0).
    """
    b = ctx.bundle
    stations: gpd.GeoDataFrame = b.get("stations.parquet")
    m = folium.Map(tiles=None, control_scale=True, zoom_control=True, prefer_canvas=False)
    folium.TileLayer("OpenStreetMap", name="Base map",
                     attr='© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors').add_to(m)
    # quiet, paper-like base map: greyscale and faded so data marks carry the colour
    m.get_root().header.add_child(folium.Element(
        "<style>.leaflet-tile-pane{filter:grayscale(1) contrast(.8) brightness(1.1);opacity:.6}"
        f".leaflet-container{{background:{theme.PAPER}}}</style>"))

    # centreline, buffer, selected stretch
    if b.line_rd is not None:
        buf = gpd.GeoSeries([b.line_rd.buffer(ctx.buffer_m)], crs=28992).to_crs(4326)
        folium.GeoJson(buf.__geo_interface__, name=f"Buffer {ctx.buffer_m} m",
                       style_function=lambda _: {"color": theme.HAIRLINE, "weight": 0.5,
                                                 "fillColor": "#1A1A1A", "fillOpacity": 0.04},
                       tooltip=f"Amstel buffer {ctx.buffer_m} m (analysis choice)").add_to(m)
        folium.PolyLine([(y, x) for x, y in b.line_wgs84.coords], color=theme.INK, weight=1.6,
                        tooltip="Amstel centreline (OpenStreetMap)").add_to(m)
        lo, hi = ctx.stretch_m
        if lo > 0 or hi < ctx.river_length_m - 1:
            seg = gpd.GeoSeries([substring(b.line_rd, lo, hi)], crs=28992).to_crs(4326).iloc[0]
            folium.PolyLine([(y, x) for x, y in seg.coords], color=theme.ACCENT, weight=6, opacity=0.35,
                            tooltip=f"Selected stretch km {lo / 1000:.1f}–{hi / 1000:.1f}").add_to(m)

    if stations is not None:
        wgs = stations.to_crs(4326)
        geo = dict(zip(wgs["station_id"], wgs.geometry))
        info = stations.set_index("station_id")

        if ctx.show_context:
            ctx_ids = [s for s in info.index if s not in ctx.amstel_ids_all_buffers]
            for sid in ctx_ids:
                p = geo[sid]
                folium.CircleMarker((p.y, p.x), radius=1.8, color=theme.ZERO_GREY, weight=0, fill=True,
                                    fill_opacity=0.9, tooltip=f"{sid}{TOOLTIP_SEP}outside corridor").add_to(m)

        corridor = ctx.corridor_all.set_index("station_id")
        in_stretch = ctx.corridor_ids
        n_max = float(counts.reindex(corridor.index).fillna(0).max() or 0)
        for sid, row in corridor.iterrows():
            if sid not in geo:
                continue
            p = geo[sid]
            n = float(counts.get(sid, 0))
            kind = "both" if (row["is_chem"] and row["is_bio"]) else ("chem" if row["is_chem"] else "bio")
            r, col = _radius(n, n_max), _colour(n, n_max)
            dim = sid not in in_stretch
            raw = bool(info.loc[sid, "has_raw_bio"]) if sid in info.index else False
            tip = (f"{sid}{TOOLTIP_SEP}{kind}{TOOLTIP_SEP}{int(n):,} obs (selection){TOOLTIP_SEP}"
                   f"km {row['chainage_m'] / 1000:.2f}{TOOLTIP_SEP}{row['distance_to_river_m']:.0f} m from centreline"
                   + (f"{TOOLTIP_SEP}raw biology values" if raw else ""))
            style = dict(color=theme.INK if not dim else theme.ZERO_GREY, weight=0.6, fill=True, fill_color=col,
                         fill_opacity=0.25 if dim else 0.92, tooltip=tip)
            if kind == "chem":
                folium.CircleMarker((p.y, p.x), radius=r, **style).add_to(m)
            else:
                folium.RegularPolygonMarker((p.y, p.x), number_of_sides=4, radius=r * 1.15,
                                            rotation=45 if kind == "bio" else 0, **style).add_to(m)
            if raw:
                folium.CircleMarker((p.y, p.x), radius=r + 4, color=theme.ACCENT, weight=1.6, fill=False,
                                    tooltip=tip).add_to(m)
            if sid == selected:
                folium.CircleMarker((p.y, p.x), radius=r + 7, color=theme.ACCENT, weight=3, fill=False,
                                    tooltip=tip).add_to(m)

    # RWZIs (Amstel-linked prominent) and sensors
    if b.rwzi is not None:
        linked = set(settings["pressures"]["amstel_linked_rwzi"])
        r_wgs = b.rwzi[b.rwzi.geometry.notna()].to_crs(4326)
        for _, row in r_wgs.iterrows():
            if row["installation"] not in linked and not ctx.show_context:
                continue
            p = row.geometry
            label = row["name"].replace("rwzi ", "RWZI ")
            basis = "proxy site" if str(row["location_basis"]).startswith("proxy") else "plant location"
            tip = f"{label}{TOOLTIP_SEP}{basis} (discharge point not verified)"
            prominent = row["installation"] in linked
            folium.RegularPolygonMarker((p.y, p.x), number_of_sides=3, radius=9 if prominent else 6,
                                        rotation=30, color=theme.INK, weight=1.6, fill=True, fill_color="white",
                                        fill_opacity=1, tooltip=tip).add_to(m)
            if prominent:
                folium.Marker((p.y, p.x), icon=folium.DivIcon(
                    html=f'<div style="font:600 11px Inter,sans-serif;color:{theme.INK};white-space:nowrap;'
                         f'transform:translate(12px,-6px)">{label}</div>')).add_to(m)
    for name, s in settings["amstel"]["sensors"].items():
        if s.get("lat") is None:
            continue
        folium.RegularPolygonMarker((s["lat"], s["lon"]), number_of_sides=4, radius=5, rotation=0,
                                    color=theme.INK, weight=1, fill=True, fill_color=theme.INK, fill_opacity=1,
                                    tooltip=f"Sensor {name}{TOOLTIP_SEP}km {s['chainage_km']}"
                                            f"{TOOLTIP_SEP}position assumed at structure").add_to(m)

    # fit to the corridor (or selected stretch)
    if b.line_rd is not None:
        lo, hi = ctx.stretch_m
        seg = substring(b.line_rd, lo, hi) if hi > lo else b.line_rd
        bounds = gpd.GeoSeries([seg.buffer(400)], crs=28992).to_crs(4326).total_bounds
        m.fit_bounds([[bounds[1], bounds[0]], [bounds[3], bounds[2]]])
    return m


def legend_html() -> str:
    """Direct, inline legend: marker shapes and colour scale."""
    s = theme.shape_svg
    ramp = "".join(f'<span style="display:inline-block;width:14px;height:9px;background:{c}"></span>'
                   for c in theme.VIRIDIS[::2])
    return ('<div class="hn-legend">'
            f'<span>{s("chem")}chemistry</span><span>{s("bio")}biology</span><span>{s("both")}both</span>'
            f'<span>{s("ring", theme.ACCENT)}raw biology values</span>'
            f'<span>{s("rwzi")}RWZI (discharge point not verified)</span><span>{s("sensor")}hydrology sensor</span>'
            f'<span><span style="display:inline-block;width:14px;height:9px;background:{theme.ZERO_GREY}"></span>'
            f' 0 obs</span><span>{ramp} few → many obs (log colour, √ size)</span></div>')
