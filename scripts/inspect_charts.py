"""
Chart validation — inspect the underlying figure data without rendering pixels.

Usage:
    python scripts/inspect_charts.py

For each chart we rebuild the matplotlib Figure object in-memory and print:
    * Figure size and DPI
    * Axes title / labels / tick labels
    * Number and types of artists (lines, bars, scatter points)
    * Colour assignment per zone (verify ZONE_COLORS mapping)
    * Annotation text content
    * Legend entries
    * Axis ranges and grid state

This lets a remote reviewer confirm the charts are well-formed without
ever opening the PNG/HTML files.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Make `src.*` imports work when this script is run directly (not via -m)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.analytics.metrics import compute_all_zone_metrics
from src.analytics.sensitivity import run_vsh_sweep
from src.data.joiner import build_master_table
from src.data.loader import load_all_wells, load_zones
from src.visualization.field import (
    ZONE_COLORS,
    crossplot_phit_perm,
    heatmap_kh_by_well_zone,
    lorenz_curves,
    sensitivity_ntg_curves,
    stacked_bar_kh_per_well,
)


# -----------------------------------------------------------------------------
# Pretty-print helpers
# -----------------------------------------------------------------------------

def header(name: str) -> None:
    bar = "=" * 78
    print(f"\n{bar}\n{name}\n{bar}")


def section(name: str) -> None:
    print(f"\n--- {name} ---")


def kv(key: str, value) -> None:
    print(f"  {key:32s} {value}")


# -----------------------------------------------------------------------------
# Per-chart inspectors
# -----------------------------------------------------------------------------

def inspect_heatmap(metrics: pd.DataFrame) -> None:
    header("CHART 01: kh heatmap")
    fig, _ = heatmap_kh_by_well_zone(metrics)
    ax = fig.axes[0]  # main axes (the colour bar is a 2nd axes)

    section("Figure")
    kv("size (inches)", fig.get_size_inches())
    kv("dpi", fig.dpi)

    section("Axes")
    kv("title", ax.get_title())
    kv("xlabel", ax.get_xlabel())
    kv("ylabel", ax.get_ylabel())
    kv("xtick labels", [t.get_text() for t in ax.get_xticklabels()])
    kv("ytick labels", [t.get_text() for t in ax.get_yticklabels()])

    section("Artists")
    images = ax.get_images()
    kv("# images (heatmap layer)", len(images))
    if images:
        arr = images[0].get_array()
        kv("heatmap shape", arr.shape)
        kv("colour map", images[0].get_cmap().name)

    section("Annotations (cell labels)")
    annotations = [t.get_text() for t in ax.texts]
    kv("# annotations", len(annotations))
    sat_annots = [a for a in annotations if "⚠" in a]
    kv("# annotations with ⚠ marker", len(sat_annots))
    kv("first 5 annotations", annotations[:5])

    plt.close(fig)


def inspect_stacked_bar(metrics: pd.DataFrame) -> None:
    header("CHART 02: stacked bar (kh per well by zone)")
    fig, _ = stacked_bar_kh_per_well(metrics)
    ax = fig.axes[0]

    section("Axes")
    kv("title", ax.get_title())
    kv("ylabel", ax.get_ylabel())
    kv("xtick labels", [t.get_text() for t in ax.get_xticklabels()])

    section("Bar groups")
    containers = ax.containers
    kv("# bar containers (= # zones)", len(containers))
    for c in containers:
        label = c.get_label()
        # All bars in container share the same colour
        colour = c.patches[0].get_facecolor()
        rgb_hex = "#" + "".join(f"{int(c * 255):02X}" for c in colour[:3])
        expected = ZONE_COLORS.get(label.replace("Zone ", ""))
        match = "✓" if expected and expected.upper() == rgb_hex.upper() else "✗"
        kv(f"  {label}", f"colour={rgb_hex}  expected={expected}  {match}")

    section("Legend")
    leg = ax.get_legend()
    if leg:
        kv("legend entries", [t.get_text() for t in leg.get_texts()])

    plt.close(fig)


def inspect_crossplot(master: pd.DataFrame) -> None:
    header("CHART 03: phit vs log10(perm) cross-plot")
    fig, _ = crossplot_phit_perm(master)
    ax = fig.axes[0]

    section("Axes")
    kv("title", ax.get_title())
    kv("xlabel", ax.get_xlabel())
    kv("ylabel", ax.get_ylabel())
    kv("xlim", ax.get_xlim())
    kv("ylim", ax.get_ylim())

    section("Scatter collections")
    collections = ax.collections
    kv("# scatter layers", len(collections))
    for c in collections:
        label = c.get_label()
        offsets = c.get_offsets()
        kv(f"  {label}", f"{len(offsets)} points")

    section("Legend")
    leg = ax.get_legend()
    if leg:
        kv("legend entries", [t.get_text() for t in leg.get_texts()])

    plt.close(fig)


def inspect_sensitivity(sweep: pd.DataFrame) -> None:
    header("CHART 04: NTG sensitivity curves")
    fig, _ = sensitivity_ntg_curves(sweep)
    ax = fig.axes[0]

    section("Axes")
    kv("title", ax.get_title())
    kv("xlabel", ax.get_xlabel())
    kv("ylabel", ax.get_ylabel())
    kv("xlim", ax.get_xlim())
    kv("ylim", ax.get_ylim())

    section("Lines")
    lines = ax.get_lines()
    kv("# total line2D artists", len(lines))

    # Group by colour (= zone)
    by_colour = {}
    for line in lines:
        c = line.get_color()
        if isinstance(c, str):
            colour_key = c
        else:
            colour_key = "#" + "".join(f"{int(x * 255):02X}" for x in c[:3])
        by_colour.setdefault(colour_key.upper(), []).append(line)

    for hexcol, lines_with_col in by_colour.items():
        # Identify which zone this colour belongs to
        zone = next(
            (z for z, c in ZONE_COLORS.items() if c.upper() == hexcol), "?"
        )
        # Bold lines (linewidth > 1.5) are the zone-averages; thin ones the per-well
        thin = [l for l in lines_with_col if l.get_linewidth() < 1.5]
        bold = [l for l in lines_with_col if l.get_linewidth() >= 1.5]
        kv(
            f"  {hexcol}  (Zone {zone})",
            f"{len(thin)} thin (per-well) + {len(bold)} bold (zone-avg)",
        )

    section("Legend")
    leg = ax.get_legend()
    if leg:
        kv("legend entries", [t.get_text() for t in leg.get_texts()])

    section("Vertical references")
    # The axvline shows up as a line with xdata constant
    for line in lines:
        xd = line.get_xdata()
        if len(xd) > 1 and xd[0] == xd[-1]:
            kv(f"  vline at x={xd[0]}", line.get_linestyle())

    plt.close(fig)


def inspect_lorenz(master: pd.DataFrame) -> None:
    header("CHART 05: Lorenz curves")
    fig, _ = lorenz_curves(master, vsh_max=0.5, phit_min=0.08)
    ax = fig.axes[0]

    section("Axes")
    kv("title", ax.get_title())
    kv("xlabel", ax.get_xlabel())
    kv("ylabel", ax.get_ylabel())
    kv("xlim", ax.get_xlim())
    kv("ylim", ax.get_ylim())
    kv("aspect", ax.get_aspect())

    section("Curves")
    lines = ax.get_lines()
    kv("# line2D artists", len(lines))
    leg = ax.get_legend()
    if leg:
        for t in leg.get_texts():
            kv("  legend entry", t.get_text())

    section("Endpoint check (each curve must end at (1, 1))")
    for line in lines:
        xd, yd = line.get_xdata(), line.get_ydata()
        if len(xd) >= 2:
            kv(
                f"  '{line.get_label()}'",
                f"start=({xd[0]:.2f},{yd[0]:.2f}) end=({xd[-1]:.2f},{yd[-1]:.2f})",
            )

    plt.close(fig)


# -----------------------------------------------------------------------------
# File system check
# -----------------------------------------------------------------------------

def inspect_output_files() -> None:
    header("OUTPUT FILES on disk")
    figures_dir = Path("outputs/figures")
    if not figures_dir.exists():
        print("  outputs/figures/ does not exist")
        return
    for f in sorted(figures_dir.iterdir()):
        if f.is_file():
            size_kb = f.stat().st_size / 1024
            kv(f.name, f"{size_kb:7.1f} KB")


# -----------------------------------------------------------------------------
# Clustering chart inspectors (Day 4)
# -----------------------------------------------------------------------------

def inspect_depth_profile(
    master: pd.DataFrame,
    target_zone: str,
    smoothed_labels,
) -> None:
    from src.visualization.clustering import (
        SUBZONE_COLORS,
        depth_profile_per_well,
    )
    header(f"CHART 06 (Zone {target_zone}): depth profile per well")
    fig, _ = depth_profile_per_well(master, target_zone, smoothed_labels)
    ax = fig.axes[0]

    section("Axes")
    kv("title", ax.get_title())
    kv("ylabel", ax.get_ylabel())
    kv("xtick labels", [t.get_text() for t in ax.get_xticklabels()])
    kv("y-axis inverted (depth down)", ax.yaxis_inverted())

    section("Sub-zone scatter layers")
    collections = ax.collections
    kv("# scatter layers (= # sub-zones)", len(collections))

    # Verify colour mapping by counting points per sub-zone in the data
    by_sub = smoothed_labels.value_counts().sort_index()
    for sub_id, count in by_sub.items():
        expected_hex = SUBZONE_COLORS.get(sub_id, "?").upper()
        kv(f"  sub-zone {sub_id}", f"{count} samples  (expected colour {expected_hex})")

    section("Vertical depth ordering check")
    # Group by well and report mean depth of each sub-zone — does ordering
    # match the expected vertical stack?
    zone_df = master.loc[smoothed_labels.index, ["well", "depth"]].copy()
    zone_df["sub_zone"] = smoothed_labels.values
    mean_depths = (
        zone_df.groupby(["well", "sub_zone"])["depth"].mean()
        .unstack().sort_index()
    )
    kv("Mean depth (m) per (well, sub_zone):", "")
    for well, row in mean_depths.iterrows():
        depths_str = "  ".join(
            f"sub{int(s)}={d:.1f}" for s, d in row.items() if pd.notna(d)
        )
        kv(f"  well {well}", depths_str)

    plt.close(fig)


def inspect_optimal_k(opt_csv_path: Path, target_zone: str) -> None:
    header(f"CHART 07 (Zone {target_zone}): optimal-K analysis")

    if not opt_csv_path.exists():
        print(f"  {opt_csv_path} not found")
        return

    df = pd.read_csv(opt_csv_path)
    section("Values from CSV")
    print(df.to_string(index=False))

    section("Implied best k")
    best_km_sil_k = int(df.loc[df["kmeans_silhouette"].idxmax(), "k"])
    best_gmm_bic_k = int(df.loc[df["gmm_bic"].idxmin(), "k"])
    kv("best k by KMeans silhouette", f"k={best_km_sil_k}  (silhouette={df['kmeans_silhouette'].max():.3f})")
    kv("best k by GMM BIC (lower=better)", f"k={best_gmm_bic_k}  (BIC={df['gmm_bic'].min():.0f})")

    # Inertia monotonicity check
    diffs = np.diff(df["kmeans_inertia"].values)
    kv("KMeans inertia monotone decreasing", bool((diffs <= 1e-6).all()))


def inspect_cross_well(
    master: pd.DataFrame,
    target_zone: str,
    smoothed_labels,
    features: list[str],
) -> None:
    from src.visualization.clustering import cross_well_centroids
    header(f"CHART 08 (Zone {target_zone}): cross-well centroid consistency")

    fig, _ = cross_well_centroids(master, target_zone, smoothed_labels, features)
    ax = fig.axes[0]

    section("Axes")
    kv("title", ax.get_title())
    kv("xlabel", ax.get_xlabel())
    kv("ylabel", ax.get_ylabel())
    kv("xlim", ax.get_xlim())
    kv("ylim", ax.get_ylim())

    section("Cluster centroids (pooled)")
    from src.clustering.subzone import DERIVED_FEATURE_FORMULAE
    zd = master.loc[smoothed_labels.index, ["well", "vsh", "perm"]].copy()
    zd["log_perm"] = DERIVED_FEATURE_FORMULAE["log_perm"](zd)
    zd["sub_zone"] = smoothed_labels.values

    pooled = zd.groupby("sub_zone")[["vsh", "log_perm"]].mean()
    for sub_id, row in pooled.iterrows():
        kv(f"  sub-zone {sub_id}", f"vsh={row['vsh']:.3f}  log_perm={row['log_perm']:.2f}")

    section("Per-well centroid spread (lower = more reproducible)")
    per_well = zd.groupby(["well", "sub_zone"])[["vsh", "log_perm"]].mean()
    for sub_id in pooled.index:
        sub_centroids = per_well.xs(sub_id, level="sub_zone")
        vsh_std = sub_centroids["vsh"].std()
        lp_std = sub_centroids["log_perm"].std()
        kv(
            f"  sub-zone {sub_id} std across wells",
            f"vsh_std={vsh_std:.3f}  log_perm_std={lp_std:.3f}",
        )

    plt.close(fig)


def inspect_subzone_metrics_csv(csv_path: Path, target_zone: str) -> None:
    header(f"PER-(WELL, SUB_ZONE) METRICS for Zone {target_zone}")

    if not csv_path.exists():
        print(f"  {csv_path} not found — run `subzones --target-zone {target_zone}` first")
        return

    df = pd.read_csv(csv_path)
    section("First rows of per-(well, sub_zone) metrics")
    print(df.to_string(index=False))

    section("Per sub-zone (field-aggregated) summary")
    summary = df.groupby("sub_zone").agg(
        n_wells=("well", "nunique"),
        thickness_total=("thickness_m", "sum"),
        kh_total=("kh_mD_m", "sum"),
        avg_phit_mean=("avg_phit", "mean"),
        avg_perm_kh_w_mean=("avg_perm_kh_weighted_mD", "mean"),
        frac_saturated_mean=("frac_saturated", "mean"),
    ).round(3)
    print(summary.to_string())


# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------

def main() -> None:
    print("Loading data...")
    raw_dir = Path("data/raw")
    processed_dir = Path("data/processed")
    reports_dir = Path("outputs/reports")

    master_path = processed_dir / "master_table.parquet"
    metrics_path = processed_dir / "metrics_per_zone.parquet"
    sweep_path = processed_dir / "sweep_results.parquet"

    if master_path.exists():
        master = pd.read_parquet(master_path)
        print(f"  Loaded master: {len(master):,} rows")
    else:
        logs = load_all_wells(raw_dir)
        zones = load_zones(raw_dir)
        master = build_master_table(logs, zones)

    if metrics_path.exists():
        metrics = pd.read_parquet(metrics_path)
    else:
        metrics = compute_all_zone_metrics(master)
    print(f"  Loaded metrics: {len(metrics)} rows")

    if sweep_path.exists():
        sweep = pd.read_parquet(sweep_path)
    else:
        sweep = run_vsh_sweep(master, vsh_min=0.3, vsh_max=0.7, vsh_step=0.05)
    print(f"  Loaded sweep: {len(sweep)} rows")

    # --- Field-view charts (01-05) ---
    inspect_heatmap(metrics)
    inspect_stacked_bar(metrics)
    inspect_crossplot(master)
    inspect_sensitivity(sweep)
    inspect_lorenz(master)

    # --- Clustering charts (06-08), one pass per zone ---
    for target_zone in ("B", "C"):
        z = target_zone.lower()
        assignments_path = reports_dir / f"subzone_assignments_zone{z}_kmeans.csv"
        opt_path = reports_dir / f"optimal_k_analysis_zone{z}.csv"
        metrics_path_zone = reports_dir / f"subzone_metrics_zone{z}_kmeans.csv"

        if not assignments_path.exists():
            print(
                f"\n*** No clustering assignments for Zone {target_zone} "
                f"({assignments_path} not found). "
                f"Run `python -m src.cli subzones --target-zone {target_zone}` first. ***"
            )
            continue

        # Load sample-level cluster labels back into a Series aligned with master
        assignments = pd.read_csv(assignments_path)
        # Re-align by (well, depth) so labels index matches master.index
        merged = master.reset_index().merge(
            assignments[["well", "depth", "sub_zone"]], on=["well", "depth"], how="inner"
        )
        smoothed = pd.Series(
            merged["sub_zone"].values, index=merged["index"].values, name="label"
        )

        features = [
            "vsh", "phit", "log_perm", "sw",
            "effective_porosity", "hc_porosity",
        ]

        inspect_depth_profile(master, target_zone, smoothed)
        inspect_optimal_k(opt_path, target_zone)
        inspect_cross_well(master, target_zone, smoothed, features)
        inspect_subzone_metrics_csv(metrics_path_zone, target_zone)

    inspect_output_files()

    print("\n" + "=" * 78)
    print("DONE — paste the entire output above into the chat.")
    print("=" * 78)


if __name__ == "__main__":
    main()