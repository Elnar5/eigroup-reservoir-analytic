"""Generate an updated pipeline architecture diagram for slide 3.

Run from project root:
    python scripts/build_architecture_v2.py

Output:
    outputs/figures/00_architecture.png

Replaces the older 00_architecture.png. The new diagram reflects the
final state of the pipeline: 5 CLI commands, 12 charts, 4 walkthrough
documents, 133 tests.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

# -----------------------------------------------------------------------------
# Color palette (matches the presentation deck)
# -----------------------------------------------------------------------------
BG = "#F5F1E8"        # warm cream background
NAVY = "#1A4D7A"      # primary
GOLD = "#C9A769"      # section accent
INK = "#1A1A1A"
MUTED = "#555555"
WHITE = "#FFFFFF"
BORDER = "#E5E5E0"
HIGHLIGHT = "#FFF3D6"
SUCCESS = "#2D7D47"

# -----------------------------------------------------------------------------
# Figure setup
# -----------------------------------------------------------------------------
FIG_W = 14
FIG_H = 6.5

# Output path
OUTPATH = Path(__file__).parent.parent / "outputs" / "figures" / "00_architecture.png"
OUTPATH.parent.mkdir(parents=True, exist_ok=True)


def draw_box(ax, x, y, w, h, *, text="", color=NAVY, text_color=WHITE,
             font_size=10, bold=False, rounded=True, subtitle=None,
             subtitle_color=None, subtitle_size=8,
             border_color=None, border_width=0):
    """Draw a labelled box on the axes."""
    boxstyle = "round,pad=0.02,rounding_size=0.05" if rounded else "square"
    box = FancyBboxPatch(
        (x, y), w, h,
        boxstyle=boxstyle,
        facecolor=color,
        edgecolor=border_color if border_color else color,
        linewidth=border_width,
        zorder=2,
    )
    ax.add_patch(box)
    if text:
        weight = "bold" if bold else "normal"
        # If subtitle, place title above center
        if subtitle:
            ax.text(
                x + w / 2, y + h * 0.65,
                text,
                ha="center", va="center",
                color=text_color, fontsize=font_size, weight=weight,
                zorder=3,
            )
            ax.text(
                x + w / 2, y + h * 0.30,
                subtitle,
                ha="center", va="center",
                color=subtitle_color or text_color, fontsize=subtitle_size,
                style="italic",
                zorder=3,
            )
        else:
            ax.text(
                x + w / 2, y + h / 2,
                text,
                ha="center", va="center",
                color=text_color, fontsize=font_size, weight=weight,
                zorder=3,
            )


def draw_arrow(ax, x1, y1, x2, y2, color=NAVY, lw=1.5, style="->"):
    """Draw an arrow between two points."""
    arrow = FancyArrowPatch(
        (x1, y1), (x2, y2),
        arrowstyle=style,
        color=color,
        linewidth=lw,
        mutation_scale=15,
        zorder=1,
    )
    ax.add_patch(arrow)


def build_diagram():
    fig, ax = plt.subplots(figsize=(FIG_W, FIG_H), facecolor=BG)
    ax.set_facecolor(BG)
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 6.5)
    ax.axis("off")

    # Title (small, top-left)
    ax.text(0.3, 6.20, "PIPELINE ARCHITECTURE",
            color=GOLD, fontsize=10, weight="bold")
    ax.text(0.3, 5.95, "One CLI command per part. All outputs reproducible.",
            color=MUTED, fontsize=10, style="italic")

    # ----- LAYER 1: RAW INPUT -----
    layer1_y = 4.85
    layer1_h = 0.6
    ax.text(0.3, layer1_y + layer1_h + 0.15, "01  ·  RAW INPUTS",
            color=GOLD, fontsize=8, weight="bold")
    # 7 well CSVs
    draw_box(ax, 0.3, layer1_y, 2.8, layer1_h,
             text="7 well CSVs",
             subtitle="well_1.csv … well_7.csv  ·  18,167 rows total",
             subtitle_color="#D0D8E8",
             color=NAVY, font_size=11, bold=True)
    # zones.csv
    draw_box(ax, 3.4, layer1_y, 2.6, layer1_h,
             text="zones.csv",
             subtitle="35 zone tops  ·  5 zones × 7 wells",
             subtitle_color="#D0D8E8",
             color=NAVY, font_size=11, bold=True)

    # ----- LAYER 2: 5 CLI COMMANDS -----
    layer2_y = 3.0
    cmd_w = 2.5
    cmd_h = 1.15
    cmd_gap = 0.2
    layer2_total_w = 5 * cmd_w + 4 * cmd_gap
    layer2_start_x = (14 - layer2_total_w) / 2

    ax.text(0.3, layer2_y + cmd_h + 0.2, "02  ·  CLI PIPELINE  ·  src.cli",
            color=GOLD, fontsize=8, weight="bold")

    commands = [
        ("quality", "Part A",
         "load · join (asof) · QC",
         "data_quality.md"),
        ("metrics", "Part B",
         "5 required + 7 bonus",
         "metrics_per_zone.csv"),
        ("sweep", "Part C.1",
         "9 cutoffs × 35 groups",
         "sweep_results.csv"),
        ("field", "Part C.2",
         "6 field-view charts",
         "01-05.png + 09.png"),
        ("subzones", "Part D",
         "KMeans + GMM + LOWO",
         "subzone_*.csv"),
    ]

    for i, (cmd, part, summary, output) in enumerate(commands):
        x = layer2_start_x + i * (cmd_w + cmd_gap)
        # Card
        card = FancyBboxPatch(
            (x, layer2_y), cmd_w, cmd_h,
            boxstyle="round,pad=0.02,rounding_size=0.05",
            facecolor=WHITE,
            edgecolor=BORDER,
            linewidth=0.8,
            zorder=2,
        )
        ax.add_patch(card)
        # Top gold strip
        strip = FancyBboxPatch(
            (x, layer2_y + cmd_h - 0.12), cmd_w, 0.12,
            boxstyle="round,pad=0,rounding_size=0",
            facecolor=GOLD,
            edgecolor=GOLD,
            linewidth=0,
            zorder=3,
        )
        ax.add_patch(strip)
        # Part label
        ax.text(x + cmd_w / 2, layer2_y + cmd_h - 0.06,
                part, ha="center", va="center",
                color=WHITE, fontsize=8, weight="bold", zorder=4)
        # Command name
        ax.text(x + cmd_w / 2, layer2_y + cmd_h - 0.35,
                cmd, ha="center", va="center",
                color=NAVY, fontsize=14, weight="bold", zorder=4,
                family="monospace")
        # Summary
        ax.text(x + cmd_w / 2, layer2_y + cmd_h - 0.65,
                summary, ha="center", va="center",
                color=INK, fontsize=8, zorder=4)
        # Output (italics)
        ax.text(x + cmd_w / 2, layer2_y + 0.2,
                output, ha="center", va="center",
                color=MUTED, fontsize=7.5, style="italic",
                family="monospace", zorder=4)

    # ----- LAYER 3: DELIVERABLES -----
    layer3_y = 0.9
    layer3_h = 1.1
    ax.text(0.3, layer3_y + layer3_h + 0.2, "03  ·  DELIVERABLES",
            color=GOLD, fontsize=8, weight="bold")

    # Deliverable boxes
    deliv_w = 2.5
    deliv_gap = 0.2
    deliv_total_w = 5 * deliv_w + 4 * deliv_gap
    deliv_start_x = (14 - deliv_total_w) / 2
    deliverables = [
        ("Walkthroughs",     "4 unified MD\n~2,800 lines"),
        ("Charts",           "12 PNG + HTML\n+ architecture"),
        ("CSV tables",       "35 rows ×\n12 metrics"),
        ("Dashboard",        "9 charts in\none HTML"),
        ("Presentation",     "26-slide PPTX\nthis deck"),
    ]
    for i, (head, body) in enumerate(deliverables):
        x = deliv_start_x + i * (deliv_w + deliv_gap)
        card = FancyBboxPatch(
            (x, layer3_y), deliv_w, layer3_h,
            boxstyle="round,pad=0.02,rounding_size=0.05",
            facecolor=BG,
            edgecolor=NAVY,
            linewidth=1,
            zorder=2,
        )
        ax.add_patch(card)
        ax.text(x + deliv_w / 2, layer3_y + layer3_h * 0.70,
                head, ha="center", va="center",
                color=NAVY, fontsize=11, weight="bold", zorder=3)
        ax.text(x + deliv_w / 2, layer3_y + layer3_h * 0.32,
                body, ha="center", va="center",
                color=MUTED, fontsize=8.5, zorder=3,
                linespacing=1.3)

    # ----- ARROWS -----
    # Wells + zones merge → CLI pipeline center
    cli_center_x = 14 / 2
    cli_top_y = layer2_y + cmd_h
    # From the two input boxes down to the row of commands
    draw_arrow(ax, 1.7, layer1_y, layer2_start_x + 1 * (cmd_w + cmd_gap) + cmd_w / 2,
               cli_top_y + 0.05, color=NAVY, lw=1.8)
    draw_arrow(ax, 4.7, layer1_y,
               layer2_start_x + 2 * (cmd_w + cmd_gap) + cmd_w / 2,
               cli_top_y + 0.05, color=NAVY, lw=1.8)

    # CLI commands → deliverables
    # Each command writes to multiple deliverables, so use converging lines
    # All 5 commands → converge to a single "outputs bus", then fan out to deliverables
    cli_bottom_y = layer2_y - 0.05
    deliv_top_y = layer3_y + layer3_h + 0.05
    bus_y = (cli_bottom_y + deliv_top_y) / 2

    # Vertical lines from each CLI command down to the bus
    for i in range(5):
        cmd_x = layer2_start_x + i * (cmd_w + cmd_gap) + cmd_w / 2
        ax.plot([cmd_x, cmd_x], [cli_bottom_y, bus_y],
                color=GOLD, linewidth=1.0, zorder=1)
    # Horizontal bus line connecting all CLI columns
    bus_left = layer2_start_x + cmd_w / 2
    bus_right = layer2_start_x + 4 * (cmd_w + cmd_gap) + cmd_w / 2
    ax.plot([bus_left, bus_right], [bus_y, bus_y],
            color=GOLD, linewidth=1.2, zorder=1)
    # Vertical arrows from bus down to each deliverable
    for i in range(5):
        deliv_x = deliv_start_x + i * (deliv_w + deliv_gap) + deliv_w / 2
        draw_arrow(ax, deliv_x, bus_y, deliv_x, deliv_top_y,
                   color=GOLD, lw=1.2)

    # ----- FOOTER STATS -----
    footer_y = 0.35
    stat_w = 2.4
    stat_gap = 0.4
    stats = [
        ("18,167",  "depth samples"),
        ("133",     "pytest tests"),
        ("79%",     "code coverage"),
        ("12",      "charts produced"),
        ("4",       "walkthrough docs"),
    ]
    stats_total_w = 5 * stat_w + 4 * stat_gap
    stat_start_x = (14 - stats_total_w) / 2

    for i, (val, lbl) in enumerate(stats):
        x = stat_start_x + i * (stat_w + stat_gap)
        ax.text(x + stat_w / 2, footer_y + 0.05,
                val, ha="center", va="bottom",
                color=NAVY, fontsize=16, weight="bold")
        ax.text(x + stat_w / 2, footer_y - 0.15,
                lbl, ha="center", va="top",
                color=MUTED, fontsize=8, style="italic")

    plt.tight_layout()
    plt.savefig(OUTPATH, dpi=200, bbox_inches="tight",
                facecolor=BG, edgecolor="none")
    plt.close()
    print(f"Wrote {OUTPATH}")


if __name__ == "__main__":
    build_diagram()