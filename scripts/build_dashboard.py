"""
Build a single-page interactive HTML dashboard combining the field-view
charts (Day 3) and the clustering results (Day 4).

The dashboard is meant for the presentation: one URL, opens in any browser,
lets the audience hover/zoom each chart, and tells the full story top to
bottom.

Layout:
    Row 1: kh heatmap (Zone × Well)
    Row 2: NTG sensitivity curves           |  Lorenz curves
    Row 3: Cross-plot (phit vs log_perm)    |  Stacked bar (kh per well)
    Row 4: Zone B depth profile             |  Zone C depth profile
    Row 5: Zone C optimal-K (silhouette only) | Zone C cross-well centroids

Output: outputs/dashboard.html
Usage:  python scripts/build_dashboard.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import matplotlib
matplotlib.use("Agg")
import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
from plotly.subplots import make_subplots

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
from src.visualization.clustering import (
    SUBZONE_COLORS,
    cross_well_centroids,
    depth_profile_per_well,
    optimal_k_plot,
)


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------

def load_data():
    """Load (or rebuild) the master table, metrics, sweep, and clustering
    labels for Zone B and Zone C."""
    raw_dir = Path("data/raw")
    processed_dir = Path("data/processed")
    reports_dir = Path("outputs/reports")

    master_path = processed_dir / "master_table.parquet"
    metrics_path = processed_dir / "metrics_per_zone.parquet"
    sweep_path = processed_dir / "sweep_results.parquet"

    if master_path.exists():
        master = pd.read_parquet(master_path)
    else:
        logs = load_all_wells(raw_dir)
        zones = load_zones(raw_dir)
        master = build_master_table(logs, zones)

    metrics = (
        pd.read_parquet(metrics_path)
        if metrics_path.exists()
        else compute_all_zone_metrics(master)
    )

    sweep = (
        pd.read_parquet(sweep_path)
        if sweep_path.exists()
        else run_vsh_sweep(master, vsh_min=0.3, vsh_max=0.7, vsh_step=0.05)
    )

    # Reload clustering assignments for both zones
    labels = {}
    for target_zone in ("B", "C"):
        z = target_zone.lower()
        assignments_path = reports_dir / f"subzone_assignments_zone{z}_kmeans.csv"
        if assignments_path.exists():
            assignments = pd.read_csv(assignments_path)
            merged = master.reset_index().merge(
                assignments[["well", "depth", "sub_zone"]],
                on=["well", "depth"], how="inner",
            )
            labels[target_zone] = pd.Series(
                merged["sub_zone"].values,
                index=merged["index"].values,
                name="label",
            )

    opt_k = {}
    for target_zone in ("B", "C"):
        z = target_zone.lower()
        opt_path = reports_dir / f"optimal_k_analysis_zone{z}.csv"
        if opt_path.exists():
            opt_k[target_zone] = pd.read_csv(opt_path)

    return master, metrics, sweep, labels, opt_k


# -----------------------------------------------------------------------------
# Build dashboard
# -----------------------------------------------------------------------------

def main():
    print("Loading data…")
    master, metrics, sweep, labels, opt_k = load_data()
    print(f"  Master: {len(master):,} rows; metrics: {len(metrics)}; "
          f"sweep: {len(sweep)}; clustering zones: {list(labels.keys())}")

    # Build each individual figure
    print("Rebuilding charts…")
    _, heat_p = heatmap_kh_by_well_zone(metrics)
    _, sens_p = sensitivity_ntg_curves(sweep)
    _, lor_p = lorenz_curves(master, vsh_max=0.5, phit_min=0.08)
    _, cross_p = crossplot_phit_perm(master, sample_frac=0.40)
    _, bar_p = stacked_bar_kh_per_well(metrics)

    sub_charts = {}
    if "B" in labels:
        _, dp_b = depth_profile_per_well(master, "B", labels["B"])
        sub_charts["B_depth"] = dp_b
    if "C" in labels:
        _, dp_c = depth_profile_per_well(master, "C", labels["C"])
        sub_charts["C_depth"] = dp_c

        features = ["vsh", "phit", "log_perm", "sw",
                    "effective_porosity", "hc_porosity"]
        _, cwc_c = cross_well_centroids(master, "C", labels["C"], features)
        sub_charts["C_centroid"] = cwc_c

    # Compose into one big HTML
    print("Composing HTML dashboard…")
    html_parts = []
    html_parts.append("""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<title>Reservoir Analytics Dashboard</title>
<style>
  body {
    font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
    margin: 0 auto;
    max-width: 1600px;
    padding: 32px 40px;
    background: #fafafa;
    color: #222;
    line-height: 1.5;
  }
  h1 { color: #0072B2; margin-bottom: 4px; font-size: 28px; }
  h2 {
    color: #333;
    border-bottom: 2px solid #0072B2;
    padding-bottom: 6px;
    margin-top: 48px;
    margin-bottom: 12px;
    font-size: 18px;
  }
  .subtitle { color: #666; margin-top: 4px; margin-bottom: 24px; font-size: 14px; }
  .twocol {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 28px;
    margin-top: 16px;
  }
  /* On narrow viewports, stack into a single column */
  @media (max-width: 1100px) {
    .twocol { grid-template-columns: 1fr; }
  }
  /* Each plotly chart container — force a sensible minimum height */
  .plotly-graph-div {
    min-height: 420px !important;
    width: 100% !important;
  }
  .findings {
    background: #fff8e1;
    border-left: 5px solid #E69F00;
    padding: 16px 24px;
    margin: 20px 0;
    border-radius: 4px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.06);
  }
  .findings ul { margin: 8px 0; padding-left: 24px; }
  .findings li { margin: 6px 0; }
  .findings b { color: #b8860b; }
  .section-intro {
    color: #555;
    font-size: 14px;
    margin: -4px 0 14px;
    font-style: italic;
  }
  footer {
    margin-top: 64px;
    padding-top: 20px;
    border-top: 1px solid #ddd;
    color: #888;
    font-size: 0.85em;
  }
  code {
    background: #f0f0f0;
    padding: 2px 6px;
    border-radius: 3px;
    font-size: 0.92em;
  }
</style>
</head><body>
<h1>Reservoir Analytics Dashboard</h1>
<div class="subtitle">eiGroup Associate Data Scientist assessment · 7 wells · 5 zones · 18,167 samples · 105 tests · Kamil Muradli, May 2026</div>

<div class="findings">
  <b>Headline findings:</b>
  <ul>
    <li>Zone B is the dominant flow interval (kh ≈ 10.7 M mD·m, NTG 93%)
        — <b>but 88% of samples are at the 15,000 mD tool cap</b>, so its
        kh is a conservative lower bound, not a best estimate.</li>
    <li>Zone D is tight rock: NTG never exceeds 32% even at the loosest
        vsh cutoff. <b>Bypass it.</b></li>
    <li>Zone C splits into 3 reproducible sub-zones across all 7 wells.
        <b>Sub-zone 2 holds 48% of Zone C kh in just 29% of its thickness</b>
        — natural drilling target.</li>
    <li>Well-to-well kh ranking is partly an instrument artefact: well 7
        leads kh but has the highest saturation fraction (30%).</li>
  </ul>
</div>
""")

    def embed(fig, title, is_first=False):
        # First chart loads plotly.js from CDN; subsequent ones reuse it.
        # This avoids the "script-after-divs" timing issue we had before.
        return (
            f"<h2>{title}</h2>\n"
            + pio.to_html(
                fig,
                include_plotlyjs="cdn" if is_first else False,
                full_html=False,
                config={"displayModeBar": "hover", "responsive": True},
            )
        )

    # Section 1 — field overview
    html_parts.append(embed(heat_p, "1. Field overview — kh by well × zone", is_first=True))
    html_parts.append('<div class="twocol">')
    html_parts.append(embed(sens_p, "2a. NTG sensitivity to vsh cutoff"))
    html_parts.append(embed(lor_p, "2b. Lorenz curves — flow heterogeneity"))
    html_parts.append("</div>")

    html_parts.append('<div class="twocol">')
    html_parts.append(embed(cross_p, "3a. Porosity-permeability cross-plot"))
    html_parts.append(embed(bar_p, "3b. Total kh per well, decomposed by zone"))
    html_parts.append("</div>")

    # Section 2 — clustering (only if assignments exist)
    if "B_depth" in sub_charts or "C_depth" in sub_charts:
        html_parts.append('<div class="twocol">')
        if "B_depth" in sub_charts:
            html_parts.append(embed(sub_charts["B_depth"],
                                    "4a. Zone B clusters — saturation-blocked"))
        if "C_depth" in sub_charts:
            html_parts.append(embed(sub_charts["C_depth"],
                                    "4b. Zone C clusters — working clustering"))
        html_parts.append("</div>")

        if "C_centroid" in sub_charts:
            html_parts.append(embed(sub_charts["C_centroid"],
                                    "5. Zone C cross-well centroid consistency"))

    html_parts.append("""
<div style="margin-top: 40px; padding-top: 20px; border-top: 1px solid #ddd;
            color: #888; font-size: 0.85em;">
  Pipeline: <code>python -m src.cli quality → metrics → sweep → field → subzones</code><br>
  Full source tree, 105 pytest tests, and reproducibility instructions in repo.
</div>
</body></html>
""")

    out_path = Path("outputs/dashboard.html")
    out_path.write_text("\n".join(html_parts))
    print(f"Wrote {out_path} ({out_path.stat().st_size / 1024:.1f} KB)")


if __name__ == "__main__":
    main()