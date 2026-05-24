"""
Generate the architecture diagram for the reservoir analytics pipeline.

Produces a layered diagram showing data sources, processing modules, and
outputs, with arrows indicating data flow. Pure matplotlib — no external
graph tools required.

Output: outputs/figures/00_architecture.png
Usage:  python scripts/build_architecture_diagram.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import matplotlib
matplotlib.use("Agg")
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch


# Wong colour-blind safe palette (matches ZONE_COLORS / SUBZONE_COLORS in repo)
LAYER_COLORS = {
    "data":          "#0072B2",   # blue   — input/raw + IO
    "analytics":     "#009E73",   # green  — pure numeric pipelines
    "clustering":    "#E69F00",   # orange — ML
    "visualization": "#D55E00",   # red    — outputs to humans
    "cli":           "#999999",   # grey   — entry points
}


def add_box(ax, x, y, w, h, label, sublabel=None, color="#CCCCCC", text_color="white"):
    """Add a rounded box with one or two lines of text."""
    box = FancyBboxPatch(
        (x, y), w, h,
        boxstyle="round,pad=0.02,rounding_size=0.05",
        linewidth=1.5, edgecolor="black", facecolor=color, alpha=0.9,
    )
    ax.add_patch(box)
    if sublabel:
        ax.text(x + w / 2, y + h * 0.62, label,
                ha="center", va="center", fontsize=10, weight="bold", color=text_color)
        ax.text(x + w / 2, y + h * 0.30, sublabel,
                ha="center", va="center", fontsize=7.5, color=text_color, style="italic")
    else:
        ax.text(x + w / 2, y + h / 2, label,
                ha="center", va="center", fontsize=10, weight="bold", color=text_color)


def add_arrow(ax, x1, y1, x2, y2, color="#444444"):
    arr = FancyArrowPatch(
        (x1, y1), (x2, y2),
        arrowstyle="->", mutation_scale=14,
        linewidth=1.2, color=color,
    )
    ax.add_patch(arr)


def main():
    fig, ax = plt.subplots(figsize=(14, 9))
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 9)
    ax.set_aspect("equal")
    ax.axis("off")

    ax.text(7, 8.5, "Reservoir Analytics Pipeline — Architecture",
            ha="center", fontsize=16, weight="bold")
    ax.text(7, 8.1, "7 wells · 5 zones · 18,167 samples · single-command reproducible",
            ha="center", fontsize=10, style="italic", color="#666666")
    # Inline colour key (replaces legend, avoids layout conflicts)
    ax.text(
        7, 7.8,
        "Blue = data layer    Green = analytics    Orange = clustering (ML)    "
        "Red = visualization    Grey = CLI / orchestration",
        ha="center", fontsize=8.5, color="#444444",
    )

    # =========================================================================
    # LAYER 1 — Inputs (data sources, top of diagram)
    # =========================================================================
    add_box(ax, 0.3, 6.8, 2.0, 0.9, "7 well CSVs",
            sublabel="depth, vsh, phit, sw, perm",
            color=LAYER_COLORS["data"])
    add_box(ax, 2.6, 6.8, 1.8, 0.9, "zones.csv",
            sublabel="35 zone tops", color=LAYER_COLORS["data"])
    add_box(ax, 4.7, 6.8, 1.8, 0.9, "config.yaml",
            sublabel="Hydra · cutoffs · clustering",
            color=LAYER_COLORS["data"])

    # =========================================================================
    # LAYER 2 — Data ingestion
    # =========================================================================
    add_box(ax, 0.3, 5.4, 2.0, 0.9, "loader.py",
            sublabel="schema, dtype, validation",
            color=LAYER_COLORS["data"])
    add_box(ax, 2.6, 5.4, 1.8, 0.9, "joiner.py",
            sublabel="merge_asof, per-well dz",
            color=LAYER_COLORS["data"])
    add_box(ax, 4.7, 5.4, 1.8, 0.9, "quality.py",
            sublabel="NaN, range, saturation flags",
            color=LAYER_COLORS["data"])

    # Arrows: layer 1 -> layer 2
    add_arrow(ax, 1.3, 6.8, 1.3, 6.3)
    add_arrow(ax, 3.5, 6.8, 3.5, 6.3)
    add_arrow(ax, 5.6, 6.8, 5.6, 6.3)

    # =========================================================================
    # LAYER 3 — Master table (the single source of truth)
    # =========================================================================
    add_box(ax, 1.7, 4.1, 4.3, 0.9, "master_table.parquet",
            sublabel="(well, depth, zone, vsh, phit, sw, perm, dz)",
            color=LAYER_COLORS["data"], text_color="white")
    # Arrows: data layer -> master
    add_arrow(ax, 1.3, 5.4, 2.5, 5.0)
    add_arrow(ax, 3.5, 5.4, 3.85, 5.0)
    add_arrow(ax, 5.6, 5.4, 5.0, 5.0)

    # =========================================================================
    # LAYER 4 — Analytics
    # =========================================================================
    add_box(ax, 0.3, 2.7, 1.9, 0.9, "metrics.py",
            sublabel="Part B — 12 metrics/zone",
            color=LAYER_COLORS["analytics"])
    add_box(ax, 2.4, 2.7, 1.9, 0.9, "sensitivity.py",
            sublabel="Part C.1 — sweep + CI + knee",
            color=LAYER_COLORS["analytics"])
    add_box(ax, 4.5, 2.7, 1.9, 0.9, "subzone.py",
            sublabel="Part D — pooled clustering",
            color=LAYER_COLORS["clustering"])

    # Arrows: master -> analytics
    add_arrow(ax, 3.5, 4.1, 1.3, 3.6)
    add_arrow(ax, 3.85, 4.1, 3.35, 3.6)
    add_arrow(ax, 4.0, 4.1, 5.45, 3.6)

    # =========================================================================
    # LAYER 5 — Visualization
    # =========================================================================
    add_box(ax, 1.0, 1.3, 2.4, 0.9, "field.py",
            sublabel="charts 01-05 (PNG + HTML)",
            color=LAYER_COLORS["visualization"])
    add_box(ax, 3.7, 1.3, 2.4, 0.9, "clustering.py",
            sublabel="charts 06-08 (PNG + HTML)",
            color=LAYER_COLORS["visualization"])

    # Arrows: analytics -> viz
    add_arrow(ax, 1.3, 2.7, 1.9, 2.2)
    add_arrow(ax, 3.35, 2.7, 2.5, 2.2)
    add_arrow(ax, 3.35, 2.7, 4.5, 2.2)
    add_arrow(ax, 5.45, 2.7, 4.9, 2.2)

    # =========================================================================
    # LAYER 6 — Outputs (left bottom)
    # =========================================================================
    add_box(ax, 1.0, 0.1, 2.4, 0.7, "outputs/figures/",
            sublabel="10 PNG + 10 HTML",
            color="#888888")
    add_box(ax, 3.7, 0.1, 2.4, 0.7, "outputs/reports/",
            sublabel="CSV + parquet + markdown",
            color="#888888")
    add_arrow(ax, 2.2, 1.3, 2.2, 0.85)
    add_arrow(ax, 4.9, 1.3, 4.9, 0.85)

    # =========================================================================
    # RIGHT COLUMN — CLI + tests + glue
    # =========================================================================
    # CLI orchestrator
    add_box(ax, 8.2, 6.8, 5.4, 0.9, "src/cli.py  (typer)",
            sublabel="quality · metrics · sweep · field · subzones",
            color=LAYER_COLORS["cli"])

    # CLI -> all modules (one arrow visually summarises)
    add_arrow(ax, 10.9, 6.8, 6.0, 4.6)

    # Tests
    add_box(ax, 8.2, 5.2, 5.4, 1.0, "tests/  (105 tests, pytest)",
            sublabel="invariants · NaN handling · saturation · clustering · LOWO ARI",
            color="#555555")

    # Config arrow
    ax.annotate("", xy=(8.2, 7.2), xytext=(6.5, 7.2),
                arrowprops=dict(arrowstyle="->", color="#444444", lw=1.2))

    # Engineering principles box (right bottom)
    add_box(ax, 8.2, 2.7, 5.4, 1.8, "Engineering principles",
            sublabel="• Hydra config (single source of truth)\n"
                     "• 96-100% test coverage on hot paths\n"
                     "• Pure functions, dependency-injected\n"
                     "• PNG + HTML for every chart\n"
                     "• ~10× CLI surface area, fail-loud",
            color="#444444")

    # Caveats box
    add_box(ax, 8.2, 0.4, 5.4, 1.9, "Real-data findings",
            sublabel="• 88% Zone B samples at 15,000 mD cap\n"
                     "• Zone D NTG never exceeds 32%\n"
                     "• Lorenz=0 on Zone B is a tool artefact\n"
                     "• well_5 dz=0.5m (others 0.2m), handled per-well\n"
                     "• Zone C splits into 3 reproducible sub-zones",
            color="#222222")

    # =========================================================================
    # LAYER LEGEND
    # =========================================================================
    legend_handles = [
        mpatches.Patch(color=LAYER_COLORS["data"], label="Data layer"),
        mpatches.Patch(color=LAYER_COLORS["analytics"], label="Analytics"),
        mpatches.Patch(color=LAYER_COLORS["clustering"], label="Clustering (ML)"),
        mpatches.Patch(color=LAYER_COLORS["visualization"], label="Visualization"),
        mpatches.Patch(color=LAYER_COLORS["cli"], label="CLI / orchestration"),
    ]
    # (Colour key is in subtitle; matplotlib legend removed to avoid layout conflicts.)

    out_path = Path("outputs/figures/00_architecture.png")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
