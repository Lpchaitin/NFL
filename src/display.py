"""Shared chart style and readable-table helpers for the notebooks.

    from src.display import show, season_line, season_axis, COLORS, BLUE, ORANGE, MUTED
"""
from __future__ import annotations

import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import pandas as pd
import polars as pl
from IPython.display import display

# Fixed categorical order (validated reference palette): blue, orange, aqua, yellow, magenta, green
BLUE, ORANGE, AQUA, YELLOW, MAGENTA, GREEN = "#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300"
COLORS = [BLUE, ORANGE, AQUA, YELLOW, MAGENTA, GREEN]
INK, MUTED, GRID = "#1f1f1e", "#6b6a64", "#e4e2dc"

plt.rcParams.update({
    "figure.dpi": 110, "figure.figsize": (11, 4),
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.edgecolor": MUTED, "axes.labelcolor": INK, "axes.labelsize": 10,
    "axes.titleweight": "bold", "axes.titlesize": 12, "axes.titlepad": 10,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8,
    "xtick.color": MUTED, "ytick.color": MUTED, "lines.linewidth": 2, "lines.markersize": 5,
    "legend.frameon": False, "legend.fontsize": 9,
})


def season_line(ax, seasons, values, last_full, color, label=None, **kw):
    """Solid line through complete seasons; dotted segment + hollow dot for an in-progress season."""
    seasons, values = list(seasons), list(values)
    done = [(s, v) for s, v in zip(seasons, values) if s <= last_full and v is not None]
    part = [(s, v) for s, v in zip(seasons, values) if s > last_full and v is not None]
    ax.plot([s for s, _ in done], [v for _, v in done], color=color, marker="o", label=label, **kw)
    if part and done:
        ax.plot([done[-1][0], part[0][0]], [done[-1][1], part[0][1]], color=color, linestyle=":", linewidth=kw.get("linewidth", 2))
        ax.scatter([s for s, _ in part], [v for _, v in part], facecolors="white", edgecolors=color, s=40, zorder=3, linewidths=1.5)


def season_axis(ax, ylabel, pct=False):
    """Standard x-axis (Season, whole years), y-axis label, optional percent formatting."""
    ax.set_xlabel("Season")
    ax.set_ylabel(ylabel)
    ax.xaxis.set_major_locator(mtick.MaxNLocator(integer=True))
    if pct:
        ax.yaxis.set_major_formatter(mtick.PercentFormatter(1, decimals=0))


def end_labels(ax, series: dict, colors: dict, fmt="{:.0%}"):
    """Direct-label each line at its last point: 'name  value'."""
    for name, (x, y) in series.items():
        ax.annotate(f"{name}  {fmt.format(y)}", (x, y), xytext=(6, 0), textcoords="offset points",
                    va="center", fontsize=8, color=INK)
    ax.set_xlim(right=ax.get_xlim()[1] + 1.6)


LABELS = {
    "season": "Season", "team": "Team", "plays": "Plays", "rows": "Rows", "dropbacks": "Dropbacks",
    "epa_per_play": "EPA / Play", "success_rate": "Success Rate", "share": "Share of Plays",
    "pass_epa": "EPA / Dropback", "rush_epa": "EPA / Designed Run",
    "explosive_rate": "Explosive Play Rate", "pressure_rate": "Pressure Rate", "sack_rate": "Sack Rate",
}
PCT = {"success_rate", "share", "explosive_rate", "pressure_rate", "sack_rate", "usage"}


def show(df, title, labels=None, pct=(), signed_pct=(), epa=(), ints=(), fmt=None, note=None):
    """Display a table with readable headers and number formats.

    Formatting is inferred from column names: rates/shares as %, anything with 'epa' as a signed
    3-decimal number, ranks and counts as whole numbers. Override with pct / epa / ints / fmt.
    """
    pdf = df.to_pandas() if isinstance(df, pl.DataFrame) else df.copy()
    formats = {}
    for c in pdf.columns:
        if c in PCT or c in pct or str(c).startswith("has_") or str(c).endswith("_rate") or str(c).endswith("_share"):
            formats[c] = "{:.1%}"
        elif c in signed_pct:
            formats[c] = "{:+.1%}"
        elif ("epa" in str(c) and "rank" not in str(c)) or c in epa:
            formats[c] = "{:+.3f}"
        elif str(c).endswith("rank") or c in ints or c in ("plays", "rows", "dropbacks"):
            formats[c] = "{:,.0f}"
    formats.update(fmt or {})
    names = {**LABELS, **(labels or {})}
    pdf = pdf.rename(columns={c: names.get(c, c) for c in pdf.columns})
    formats = {names.get(c, c): f for c, f in formats.items()}
    caption = f"<b>{title}</b>" + (f"<br><span style='font-weight:normal;color:#6b6a64'>{note}</span>" if note else "")
    styler = (pdf.style.format(formats, na_rep="—")
              .hide(axis="index")
              .set_caption(caption)
              .set_table_styles([
                  {"selector": "caption", "props": "caption-side: top; text-align: left; font-size: 13px; padding-bottom: 6px;"},
                  {"selector": "th", "props": "text-align: center; padding: 4px 10px;"},
                  {"selector": "td", "props": "text-align: center; padding: 3px 10px;"},
              ]))
    display(styler)
