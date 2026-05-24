"""
Part C.2: Field-level views.

Charts that turn the 35-row metrics frame into pictures a geoscientist or
asset team can act on. Each function takes a tidy DataFrame and returns
(matplotlib_fig, plotly_fig) so the same data flows into static reports
and the interactive dashboard.

Charts:
    1. heatmap_kh_by_well_zone   — which zone in which well delivers kh
    2. stacked_bar_kh_per_well   — total kh per well, decomposed by zone
    3. crossplot_phit_perm       — phit vs log(perm), coloured by zone,
                                   saturation samples marked separately
    4. sensitivity_ntg_curves    — Part C.1 result: NTG vs vsh_cutoff per zone
    5. lorenz_curves             — flow vs storage capacity for each zone

Design choices:
    * Single source of truth for colours (ZONE_COLORS) so every chart is
      consistent across the deliverable.
    * Each function returns both a matplotlib figure (for the report) and
      a Plotly figure (for the dashboard). Saves to disk are explicit.
    * Saturation samples are visually emphasised, not hidden — they are the
      single biggest interpretation caveat in the whole dataset.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from loguru import logger

# Saturated perm flag threshold (mirror of metrics.PERM_SATURATION_THRESHOLD)
from src.analytics.metrics import PERM_SATURATION_THRESHOLD

# Consistent palette across all field views.
# Picked to be colour-blind-friendly (Wong palette ordering).
ZONE_COLORS = {
    "A": "#009E73",  # green   — top reservoir, clean
    "B": "#0072B2",  # blue    — main flow zone (saturation-flagged)
    "C": "#E69F00",  # orange  — secondary reservoir
    "D": "#999999",  # grey    — tight rock / non-reservoir
    "E": "#D55E00",  # red     — deep reservoir
}


# -----------------------------------------------------------------------------
# Chart 1: kh heatmap (well × zone)
# -----------------------------------------------------------------------------

def heatmap_kh_by_well_zone(
    metrics: pd.DataFrame,
) -> tuple[plt.Figure, go.Figure]:
    """Heat-map of kh (mD·m) with well rows × zone columns.

    Saturation count is annotated on each cell so the reader can see which
    high-kh estimates are likely lower bounds (tool-cap artefact).
    """
    pivot_kh = metrics.pivot(index="well", columns="zone", values="kh_mD_m")
    pivot_sat = metrics.pivot(
        index="well", columns="zone", values="n_perm_saturated_in_net"
    )

    # ---- matplotlib ----
    fig_mpl, ax = plt.subplots(figsize=(8, 5))
    # log10 of kh (handle zero/negative gracefully)
    log_kh = np.log10(pivot_kh.replace(0, np.nan))
    im = ax.imshow(log_kh.values, cmap="viridis", aspect="auto")
    ax.set_xticks(range(len(pivot_kh.columns)))
    ax.set_xticklabels(pivot_kh.columns)
    ax.set_yticks(range(len(pivot_kh.index)))
    ax.set_yticklabels([f"well {w}" for w in pivot_kh.index])
    ax.set_xlabel("Zone")
    ax.set_ylabel("Well")
    ax.set_title("Flow capacity (kh) by well and zone\nAnnotation: # samples at tool-cap")

    # Cell annotations: kh value + saturation count
    for i, well in enumerate(pivot_kh.index):
        for j, zone in enumerate(pivot_kh.columns):
            kh_val = pivot_kh.iloc[i, j]
            sat_val = pivot_sat.iloc[i, j]
            if pd.notna(kh_val):
                annotation = f"{kh_val:.0f}"
                if sat_val > 0:
                    annotation += f"\n⚠{int(sat_val)}"
                ax.text(
                    j, i, annotation,
                    ha="center", va="center",
                    color="white" if log_kh.iloc[i, j] > log_kh.mean().mean() else "black",
                    fontsize=8,
                )
    plt.colorbar(im, ax=ax, label="log₁₀(kh) [mD·m]")
    fig_mpl.tight_layout()

    # ---- plotly ----
    # Build 2D text array matching the heatmap z-grid
    text_grid = []
    for i, well in enumerate(pivot_kh.index):
        row_texts = []
        for j, zone in enumerate(pivot_kh.columns):
            kh_val = pivot_kh.iloc[i, j]
            sat_val = pivot_sat.iloc[i, j]
            if pd.notna(kh_val):
                txt = f"{kh_val:.0f}"
                if sat_val > 0:
                    txt += f"<br>⚠{int(sat_val)}"
            else:
                txt = ""
            row_texts.append(txt)
        text_grid.append(row_texts)

    fig_plotly = go.Figure(
        data=go.Heatmap(
            z=log_kh.values,
            x=list(pivot_kh.columns),
            y=[f"well {w}" for w in pivot_kh.index],
            text=text_grid,
            texttemplate="%{text}",
            textfont=dict(size=11, color="white"),
            colorscale="Viridis",
            colorbar=dict(title="log₁₀(kh)<br>[mD·m]"),
            hovertemplate=(
                "Well: %{y}<br>Zone: %{x}<br>"
                "log₁₀(kh): %{z:.2f}<br><extra></extra>"
            ),
        )
    )
    fig_plotly.update_layout(
        title="Flow capacity (kh) by well and zone<br>"
              "<sub>⚠ count = samples at 15000 mD tool cap</sub>",
        xaxis_title="Zone",
        yaxis_title="Well",
        height=450,
    )
    return fig_mpl, fig_plotly


# -----------------------------------------------------------------------------
# Chart 2: stacked bar — kh per well, decomposed by zone
# -----------------------------------------------------------------------------

def stacked_bar_kh_per_well(
    metrics: pd.DataFrame,
) -> tuple[plt.Figure, go.Figure]:
    """Stacked bar: each well's kh is decomposed by zone contribution."""
    pivot = metrics.pivot(index="well", columns="zone", values="kh_mD_m").fillna(0)
    # Order zones consistently
    ordered_zones = [z for z in ZONE_COLORS if z in pivot.columns]
    pivot = pivot[ordered_zones]

    # ---- matplotlib ----
    fig_mpl, ax = plt.subplots(figsize=(9, 5))
    bottom = np.zeros(len(pivot))
    for zone in ordered_zones:
        ax.bar(
            [f"well {w}" for w in pivot.index],
            pivot[zone].values,
            bottom=bottom,
            label=f"Zone {zone}",
            color=ZONE_COLORS[zone],
            edgecolor="white",
            linewidth=0.5,
        )
        bottom += pivot[zone].values
    ax.set_ylabel("kh [mD·m]")
    ax.set_title("Total kh per well, decomposed by zone")
    ax.legend(loc="upper right", framealpha=0.9)
    ax.grid(axis="y", alpha=0.3)
    fig_mpl.tight_layout()

    # ---- plotly ----
    fig_plotly = go.Figure()
    for zone in ordered_zones:
        fig_plotly.add_trace(
            go.Bar(
                name=f"Zone {zone}",
                x=[f"well {w}" for w in pivot.index],
                y=pivot[zone].values,
                marker_color=ZONE_COLORS[zone],
                hovertemplate="%{x}<br>Zone " + zone + ": %{y:.0f} mD·m<extra></extra>",
            )
        )
    fig_plotly.update_layout(
        barmode="stack",
        title="Total kh per well, decomposed by zone",
        yaxis_title="kh [mD·m]",
        height=450,
    )
    return fig_mpl, fig_plotly


# -----------------------------------------------------------------------------
# Chart 3: phit vs log(perm) cross-plot
# -----------------------------------------------------------------------------

def crossplot_phit_perm(
    master: pd.DataFrame,
    sample_frac: float = 0.20,
    random_state: int = 42,
) -> tuple[plt.Figure, go.Figure]:
    """Classic petrophysical cross-plot: porosity vs log10(permeability),
    coloured by zone. Saturation-capped samples drawn as red X markers.

    We subsample for plotting speed (18 K points → ~3.6 K by default).
    """
    df = master.dropna(subset=["zone", "phit", "perm"]).copy()
    if sample_frac < 1.0:
        df = df.sample(frac=sample_frac, random_state=random_state)
    df["log_perm"] = np.log10(df["perm"].clip(lower=1e-3))
    df["is_saturated"] = df["perm"] >= PERM_SATURATION_THRESHOLD

    # ---- matplotlib ----
    fig_mpl, ax = plt.subplots(figsize=(9, 6))
    for zone in [z for z in ZONE_COLORS if z in df["zone"].unique()]:
        zd = df[(df["zone"] == zone) & ~df["is_saturated"]]
        ax.scatter(
            zd["phit"], zd["log_perm"],
            s=8, alpha=0.4, c=ZONE_COLORS[zone],
            label=f"Zone {zone}", edgecolors="none",
        )
    # Saturated samples on top, hatched marker
    sat = df[df["is_saturated"]]
    if len(sat) > 0:
        ax.scatter(
            sat["phit"], sat["log_perm"],
            s=18, marker="x", c="red", linewidths=0.8, alpha=0.6,
            label=f"Tool-capped ({len(sat)})",
        )
    ax.set_xlabel("Porosity (phit) [fraction]")
    ax.set_ylabel("log₁₀(perm) [mD]")
    ax.set_title("Porosity-permeability cross-plot by zone")
    ax.legend(loc="lower right", framealpha=0.9)
    ax.grid(alpha=0.3)
    fig_mpl.tight_layout()

    # ---- plotly ----
    fig_plotly = go.Figure()
    for zone in [z for z in ZONE_COLORS if z in df["zone"].unique()]:
        zd = df[(df["zone"] == zone) & ~df["is_saturated"]]
        fig_plotly.add_trace(
            go.Scatter(
                x=zd["phit"], y=zd["log_perm"],
                mode="markers",
                name=f"Zone {zone}",
                marker=dict(size=4, color=ZONE_COLORS[zone], opacity=0.5),
                hovertemplate="phit: %{x:.3f}<br>log₁₀(perm): %{y:.2f}<extra></extra>",
            )
        )
    if len(sat) > 0:
        fig_plotly.add_trace(
            go.Scatter(
                x=sat["phit"], y=sat["log_perm"],
                mode="markers",
                name=f"Tool-capped ({len(sat)})",
                marker=dict(size=6, color="red", symbol="x", opacity=0.6),
                hovertemplate="phit: %{x:.3f}<br>log₁₀(perm): %{y:.2f}<br>SATURATED<extra></extra>",
            )
        )
    fig_plotly.update_layout(
        title="Porosity-permeability cross-plot by zone",
        xaxis_title="Porosity (phit) [fraction]",
        yaxis_title="log₁₀(perm) [mD]",
        height=500,
    )
    return fig_mpl, fig_plotly


# -----------------------------------------------------------------------------
# Chart 4: sensitivity NTG curves (uses sweep results from Part C.1)
# -----------------------------------------------------------------------------

def sensitivity_ntg_curves(
    sweep_results: pd.DataFrame,
) -> tuple[plt.Figure, go.Figure]:
    """Field-level NTG vs vsh_cutoff curve per zone, with per-well lines as
    thin background context."""
    # ---- matplotlib ----
    fig_mpl, ax = plt.subplots(figsize=(9, 6))

    # Thin lines per (well, zone)
    for (well, zone), group in sweep_results.groupby(["well", "zone"], observed=True):
        g = group.sort_values("vsh_cutoff")
        ax.plot(
            g["vsh_cutoff"], g["ntg"],
            color=ZONE_COLORS.get(zone, "black"),
            alpha=0.25, linewidth=0.8,
        )

    # Bold field-average per zone
    for zone in [z for z in ZONE_COLORS if z in sweep_results["zone"].unique()]:
        zd = (
            sweep_results[sweep_results["zone"] == zone]
            .groupby("vsh_cutoff", as_index=False)["ntg"]
            .mean()
            .sort_values("vsh_cutoff")
        )
        ax.plot(
            zd["vsh_cutoff"], zd["ntg"],
            color=ZONE_COLORS[zone],
            linewidth=2.5, label=f"Zone {zone}", marker="o", markersize=5,
        )

    ax.axvline(0.5, ls="--", color="black", alpha=0.4, label="Default (0.5)")
    ax.set_xlabel("vsh cutoff")
    ax.set_ylabel("Net-to-Gross")
    ax.set_title("NTG sensitivity to vsh cutoff\nthin lines: per-well, bold: zone average")
    ax.legend(loc="lower right", framealpha=0.9)
    ax.grid(alpha=0.3)
    fig_mpl.tight_layout()

    # ---- plotly ----
    fig_plotly = go.Figure()
    for zone in [z for z in ZONE_COLORS if z in sweep_results["zone"].unique()]:
        # per-well thin
        for well in sorted(sweep_results["well"].unique()):
            g = sweep_results[
                (sweep_results["zone"] == zone) & (sweep_results["well"] == well)
            ].sort_values("vsh_cutoff")
            fig_plotly.add_trace(
                go.Scatter(
                    x=g["vsh_cutoff"], y=g["ntg"],
                    mode="lines",
                    line=dict(color=ZONE_COLORS[zone], width=1),
                    opacity=0.25,
                    showlegend=False,
                    hoverinfo="skip",
                )
            )
        # bold zone-average
        zd = (
            sweep_results[sweep_results["zone"] == zone]
            .groupby("vsh_cutoff", as_index=False)["ntg"]
            .mean()
            .sort_values("vsh_cutoff")
        )
        fig_plotly.add_trace(
            go.Scatter(
                x=zd["vsh_cutoff"], y=zd["ntg"],
                mode="lines+markers",
                name=f"Zone {zone}",
                line=dict(color=ZONE_COLORS[zone], width=3),
            )
        )
    fig_plotly.add_vline(
        x=0.5, line=dict(color="black", dash="dash"),
        annotation_text="default 0.5", annotation_position="top right",
    )
    fig_plotly.update_layout(
        title="NTG sensitivity to vsh cutoff",
        xaxis_title="vsh cutoff",
        yaxis_title="Net-to-Gross",
        height=500,
    )
    return fig_mpl, fig_plotly


# -----------------------------------------------------------------------------
# Chart 5: Lorenz curves per zone
# -----------------------------------------------------------------------------

def lorenz_curves(
    master: pd.DataFrame,
    vsh_max: float = 0.5,
    phit_min: float = 0.08,
) -> tuple[plt.Figure, go.Figure]:
    """Field-level Lorenz curves per zone: cumulative flow capacity (sorted
    by perm descending) vs cumulative storage capacity. The 45° diagonal is
    perfectly homogeneous; the more the curve bows up-left, the more
    heterogeneous the zone.
    """
    df = master.dropna(subset=["zone", "vsh", "phit"]).copy()
    df = df[(df["vsh"] <= vsh_max) & (df["phit"] >= phit_min)]

    curves = {}
    for zone in [z for z in ZONE_COLORS if z in df["zone"].unique()]:
        zd = df[df["zone"] == zone].sort_values("perm", ascending=False)
        flow = zd["perm"] * zd["dz"]
        store = zd["phit"] * zd["dz"]
        sum_flow, sum_store = flow.sum(), store.sum()
        if sum_flow > 0 and sum_store > 0:
            F = np.concatenate([[0], (flow.cumsum() / sum_flow).values])
            C = np.concatenate([[0], (store.cumsum() / sum_store).values])
            # Lorenz coef (matches metrics._lorenz_coefficient definition)
            L = 2.0 * (np.trapezoid(F, C) - 0.5)
            curves[zone] = (C, F, max(0.0, min(1.0, L)))

    # ---- matplotlib ----
    fig_mpl, ax = plt.subplots(figsize=(7, 7))
    ax.plot([0, 1], [0, 1], ls="--", color="black", alpha=0.5, label="Homogeneous (L=0)")
    for zone, (C, F, L) in curves.items():
        ax.plot(C, F, color=ZONE_COLORS[zone], linewidth=2, label=f"Zone {zone}  L={L:.2f}")
    ax.set_xlabel("Cumulative storage capacity")
    ax.set_ylabel("Cumulative flow capacity")
    ax.set_title("Lorenz curves — flow heterogeneity by zone\n(L closer to 1 = more heterogeneous)")
    ax.set_xlim(0, 1); ax.set_ylim(0, 1)
    ax.set_aspect("equal")
    ax.legend(loc="lower right", framealpha=0.9)
    ax.grid(alpha=0.3)
    fig_mpl.tight_layout()

    # ---- plotly ----
    fig_plotly = go.Figure()
    fig_plotly.add_trace(
        go.Scatter(
            x=[0, 1], y=[0, 1], mode="lines",
            line=dict(color="black", dash="dash"),
            name="Homogeneous (L=0)",
        )
    )
    for zone, (C, F, L) in curves.items():
        fig_plotly.add_trace(
            go.Scatter(
                x=C, y=F, mode="lines",
                line=dict(color=ZONE_COLORS[zone], width=3),
                name=f"Zone {zone}  L={L:.2f}",
            )
        )
    fig_plotly.update_layout(
        title="Lorenz curves — flow heterogeneity by zone",
        xaxis_title="Cumulative storage capacity",
        yaxis_title="Cumulative flow capacity",
        xaxis=dict(range=[0, 1]), yaxis=dict(range=[0, 1], scaleanchor="x", scaleratio=1),
        height=600, width=600,
    )
    return fig_mpl, fig_plotly


# -----------------------------------------------------------------------------
# Save helpers
# -----------------------------------------------------------------------------

def save_chart(
    fig_mpl: plt.Figure,
    fig_plotly: go.Figure,
    name: str,
    figures_dir: Path,
    dpi: int = 150,
) -> None:
    """Save one chart in PNG (matplotlib) + HTML (plotly) form."""
    figures_dir.mkdir(parents=True, exist_ok=True)
    png_path = figures_dir / f"{name}.png"
    html_path = figures_dir / f"{name}.html"
    fig_mpl.savefig(png_path, dpi=dpi, bbox_inches="tight")
    plt.close(fig_mpl)
    fig_plotly.write_html(html_path, include_plotlyjs="cdn")
    logger.info(f"Saved {png_path}")
    logger.info(f"Saved {html_path}")