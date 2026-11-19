"""
Server-side SVG price-history chart (no JavaScript charting library needed).

Design follows the dataviz method:
  * one line per retailer, 2 px, round joins; end-dot with a 2 px surface ring
  * categorical colours are assigned per RETAILER in a fixed order (a retailer
    keeps its colour whatever the filters), taken from the validated palette
    (adjacent-pair CVD ΔE ≥ 8, normal-vision ΔE ≥ 15).  Three of the colours are
    below 3:1 on white, so the chart ALWAYS ships with a legend, a hover
    tooltip (static/js/price-chart.js) and a data table (the history table on
    the product page) as the required "relief".
  * hairline solid grid, recessive axes, text in ink colours (never series colour)
"""

import json
from datetime import datetime
from decimal import Decimal
from math import ceil, floor, log10

from django.conf import settings
from django.utils.html import escape
from django.utils.safestring import mark_safe

from .models import RETAILER_NAMES

# Fixed order == fixed identity (see module docstring).
RETAILER_COLORS = dict(zip(RETAILER_NAMES, ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"]))

WIDTH, HEIGHT = 760, 300
PAD_L, PAD_R, PAD_T, PAD_B = 58, 22, 14, 30
SURFACE = "#ffffff"
GRID = "#e1e0d9"
AXIS = "#c3c2b7"
INK_MUTED = "#6f6e69"


def _nice_ticks(low, high, target=5):
    """Round-number tick values covering [low, high]."""
    if high <= low:
        high = low + 1
    raw = (high - low) / target
    magnitude = 10 ** floor(log10(raw))
    step = next(m * magnitude for m in (1, 2, 2.5, 5, 10) if m * magnitude >= raw)
    start = floor(low / step) * step
    end = ceil(high / step) * step
    ticks, value = [], start
    while value <= end + step / 1000:
        ticks.append(round(value, 6))
        value += step
    return ticks


def build_price_chart(records):
    """
    records: iterable of PriceRecord (any order).
    Returns {"svg": SafeString, "data": dict for the hover script, "series": legend list}
    or None when there is nothing to draw.
    """
    by_retailer = {}
    for record in records:
        by_retailer.setdefault(record.retailer, []).append((record.recorded_at, Decimal(record.price)))
    if not by_retailer:
        return None

    for points in by_retailer.values():
        points.sort(key=lambda pt: pt[0])

    all_points = [pt for pts in by_retailer.values() for pt in pts]
    t_min = min(t for t, _ in all_points).timestamp() * 1000
    t_max = max(t for t, _ in all_points).timestamp() * 1000
    if t_max - t_min < 86_400_000:  # a single day (or single record): pad so the line has width
        t_min, t_max = t_min - 43_200_000, t_max + 43_200_000
    p_min = float(min(p for _, p in all_points))
    p_max = float(max(p for _, p in all_points))
    pad = (p_max - p_min) * 0.08 or max(p_max * 0.05, 1)
    ticks = _nice_ticks(p_min - pad, p_max + pad)
    y_lo, y_hi = ticks[0], ticks[-1]

    x0, x1 = PAD_L, WIDTH - PAD_R
    y_top, y_bot = PAD_T, HEIGHT - PAD_B

    def sx(ms):
        return x0 + (ms - t_min) / (t_max - t_min) * (x1 - x0)

    def sy(price):
        return y_bot - (float(price) - y_lo) / (y_hi - y_lo) * (y_bot - y_top)

    symbol = settings.CURRENCY_SYMBOL
    parts = [
        f'<svg id="price-chart-svg" viewBox="0 0 {WIDTH} {HEIGHT}" role="img" tabindex="0" '
        f'aria-label="Price history line chart. A table with the same data follows the chart." '
        f'xmlns="http://www.w3.org/2000/svg" class="price-chart-svg">'
    ]

    # horizontal grid + y labels
    for tick in ticks:
        y = sy(tick)
        is_base = tick == ticks[0]
        parts.append(
            f'<line x1="{x0}" x2="{x1}" y1="{y:.1f}" y2="{y:.1f}" stroke="{AXIS if is_base else GRID}" stroke-width="1"/>'
        )
        label = f"{symbol}{tick:,.0f}" if float(tick).is_integer() else f"{symbol}{tick:,.2f}"
        parts.append(
            f'<text x="{x0 - 8}" y="{y + 4:.1f}" text-anchor="end" font-size="13" fill="{INK_MUTED}">{escape(label)}</text>'
        )

    # x labels (5 evenly spaced dates)
    for i in range(5):
        ms = t_min + (t_max - t_min) * i / 4
        label = datetime.fromtimestamp(ms / 1000).astimezone().strftime("%d %b")
        anchor = "start" if i == 0 else "end" if i == 4 else "middle"
        parts.append(
            f'<text x="{sx(ms):.1f}" y="{HEIGHT - 8}" text-anchor="{anchor}" font-size="13" fill="{INK_MUTED}">{escape(label)}</text>'
        )

    series_out, legend = [], []
    for retailer in RETAILER_NAMES:
        points = by_retailer.get(retailer)
        if not points:
            continue
        color = RETAILER_COLORS[retailer]
        coords = [(sx(t.timestamp() * 1000), sy(p)) for t, p in points]
        path = " ".join(f"{'M' if i == 0 else 'L'}{x:.1f} {y:.1f}" for i, (x, y) in enumerate(coords))
        parts.append(
            f'<path d="{path}" fill="none" stroke="{color}" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/>'
        )
        ex, ey = coords[-1]
        parts.append(f'<circle cx="{ex:.1f}" cy="{ey:.1f}" r="4" fill="{color}" stroke="{SURFACE}" stroke-width="2"/>')
        series_out.append(
            {"name": retailer, "color": color, "points": [[int(t.timestamp() * 1000), float(p)] for t, p in points]}
        )
        legend.append({"name": retailer, "color": color, "latest": points[-1][1]})

    parts.append("</svg>")
    data = {
        "series": series_out,
        "currency": symbol,
        "geometry": {"x0": x0, "x1": x1, "yTop": y_top, "yBottom": y_bot, "width": WIDTH, "height": HEIGHT},
        "tMin": t_min,
        "tMax": t_max,
    }
    return {"svg": mark_safe("".join(parts)), "data": data, "series": legend}


def chart_json(data):
    """Used only by tests: stable JSON representation of the chart data."""
    return json.dumps(data, sort_keys=True)
