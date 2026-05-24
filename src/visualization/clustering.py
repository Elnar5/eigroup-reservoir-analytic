"""
Part D: Clustering visualisations.

Three charts:
    1. depth_profile_per_well   — for each well, a vertical bar coloured by
       sub-zone vs depth (the "geological column" view).
    2. optimal_k_plot           — silhouette (KMeans) + BIC (GMM) + elbow,
       supporting the n_clusters=3 choice.
    3. cross_well_centroids     — pooled-fit cluster centroids in feature
       space (vsh vs log_perm), with per-well centroid scatter overlaid.

Each function returns (matplotlib.Figure, plotly.Figure) for consistency
with src.visualization.field.

Design notes:
    * Sub-zone palette is distinct from zone palette (different visual axis):
      sub-zone 0 = grey (tight), 1 = orange (mid), 2 = blue (high-perm).
    * The depth profile chart is the single most important interview visual —
      it's what a geologist will look at first to judge whether the clusters
      are geologically real.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from loguru import logger
from plotly.subplots import make_subplots

# Sub-zone palette: low→high permeability
SUBZONE_COLORS = {
    0: "#999999",   # grey  — tight / low perm
    1: "#E69F00",   # orange — mid
    2: "#0072B2",   # blue  — high perm
    3: "#009E73",   # green — extra slot for k=4
    4: "#D55E00",   # red  — extra slot for k=5
}


# -----------------------------------------------------------------------------
# Chart 06: per-well depth column coloured by sub-zone
# -----------------------------------------------------------------------------

def depth_profile_per_well(
    master: pd.DataFrame,
    target_zone: str,
    labels: pd.Series,
    label_name: str = "sub_zone",
) -> tuple[plt.Figure, go.Figure]:
    """One vertical column per well; y-axis = depth, x = well, colour = sub-zone.

    The eye should immediately verify that sub-zones stack in the same
    vertical order across all wells (geological consistency).
    """
    zone_samples = master.loc[labels.index, ["well", "depth"]].copy()
    zone_samples[label_name] = labels.values

    wells = sorted(zone_samples["well"].unique())
    n_wells = len(wells)
    n_clusters = int(zone_samples[label_name].nunique())

    # ---- matplotlib ----
    fig_mpl, ax = plt.subplots(figsize=(max(8, n_wells * 1.2), 7))
    bar_width = 0.7
    for x_pos, well in enumerate(wells):
        wd = zone_samples[zone_samples["well"] == well].sort_values("depth")
        # Plot each sample as a thin horizontal segment
        for sub_id in range(n_clusters):
            mask = wd[label_name] == sub_id
            if mask.any():
                depths = wd.loc[mask, "depth"].to_numpy()
                # Draw as scatter with vertical hlines isn't efficient at 1000+ samples;
                # use scatter with square markers instead
                ax.scatter(
                    [x_pos] * len(depths), depths,
                    s=10, marker="s",
                    color=SUBZONE_COLORS.get(sub_id, "#000000"),
                    edgecolors="none",
                )

    ax.set_xticks(range(n_wells))
    ax.set_xticklabels([f"well {w}" for w in wells])
    ax.set_xlim(-0.5, n_wells - 0.5)
    ax.invert_yaxis()   # depth increases downward
    ax.set_ylabel("Depth [m]")
    ax.set_title(
        f"Zone {target_zone} sub-zone column by well\n"
        f"(grey=low perm, orange=mid, blue=high perm)"
    )

    # Legend
    handles = [
        plt.Line2D([0], [0], marker="s", color="w", markersize=10,
                   markerfacecolor=SUBZONE_COLORS[i], label=f"Sub-zone {i}")
        for i in range(n_clusters)
    ]
    ax.legend(handles=handles, loc="upper right", framealpha=0.9)
    ax.grid(axis="y", alpha=0.3)
    fig_mpl.tight_layout()

    # ---- plotly ----
    fig_plotly = go.Figure()
    for sub_id in range(n_clusters):
        mask = zone_samples[label_name] == sub_id
        if mask.any():
            fig_plotly.add_trace(
                go.Scatter(
                    x=[wells.index(w) for w in zone_samples.loc[mask, "well"]],
                    y=zone_samples.loc[mask, "depth"],
                    mode="markers",
                    marker=dict(
                        symbol="square", size=8,
                        color=SUBZONE_COLORS.get(sub_id, "#000000"),
                    ),
                    name=f"Sub-zone {sub_id}",
                    hovertemplate="Depth: %{y:.1f} m<extra></extra>",
                )
            )
    fig_plotly.update_layout(
        title=f"Zone {target_zone} sub-zone column by well",
        xaxis=dict(
            tickmode="array",
            tickvals=list(range(n_wells)),
            ticktext=[f"well {w}" for w in wells],
        ),
        yaxis=dict(title="Depth [m]", autorange="reversed"),
        height=600,
    )
    return fig_mpl, fig_plotly


# -----------------------------------------------------------------------------
# Chart 07: optimal-K analysis (silhouette + BIC + elbow)
# -----------------------------------------------------------------------------

def optimal_k_plot(optimal_k_result) -> tuple[plt.Figure, go.Figure]:
    """Three-panel chart supporting the n_clusters choice.

    Panel 1: K-Means inertia (elbow)
    Panel 2: Silhouette (both methods, higher = better)
    Panel 3: GMM BIC (lower = better with parsimony)
    """
    k_range = optimal_k_result.k_range

    # ---- matplotlib ----
    fig_mpl, axes = plt.subplots(1, 3, figsize=(15, 4.5))

    ax = axes[0]
    ax.plot(k_range, optimal_k_result.kmeans_inertia, "o-", color="#0072B2", linewidth=2)
    ax.set_xlabel("k")
    ax.set_ylabel("Inertia (lower=better)")
    ax.set_title("K-Means elbow plot")
    ax.grid(alpha=0.3)

    ax = axes[1]
    ax.plot(k_range, optimal_k_result.kmeans_silhouette, "o-", color="#0072B2",
            label="K-Means", linewidth=2)
    ax.plot(k_range, optimal_k_result.gmm_silhouette, "s--", color="#E69F00",
            label="GMM", linewidth=2)
    ax.set_xlabel("k")
    ax.set_ylabel("Silhouette (higher=better)")
    ax.set_title("Cluster separation")
    ax.legend()
    ax.grid(alpha=0.3)

    ax = axes[2]
    ax.plot(k_range, optimal_k_result.gmm_bic, "s-", color="#E69F00", linewidth=2)
    ax.set_xlabel("k")
    ax.set_ylabel("BIC (lower=better)")
    ax.set_title("GMM Bayesian Information Criterion")
    ax.grid(alpha=0.3)

    fig_mpl.suptitle("Optimal K selection — three perspectives", y=1.02)
    fig_mpl.tight_layout()

    # ---- plotly ----
    fig_plotly = make_subplots(
        rows=1, cols=3,
        subplot_titles=("K-Means elbow", "Silhouette", "GMM BIC"),
    )
    fig_plotly.add_trace(
        go.Scatter(x=k_range, y=optimal_k_result.kmeans_inertia, mode="lines+markers",
                   name="Inertia", line=dict(color="#0072B2")),
        row=1, col=1,
    )
    fig_plotly.add_trace(
        go.Scatter(x=k_range, y=optimal_k_result.kmeans_silhouette, mode="lines+markers",
                   name="K-Means sil", line=dict(color="#0072B2")),
        row=1, col=2,
    )
    fig_plotly.add_trace(
        go.Scatter(x=k_range, y=optimal_k_result.gmm_silhouette, mode="lines+markers",
                   name="GMM sil", line=dict(color="#E69F00", dash="dash")),
        row=1, col=2,
    )
    fig_plotly.add_trace(
        go.Scatter(x=k_range, y=optimal_k_result.gmm_bic, mode="lines+markers",
                   name="BIC", line=dict(color="#E69F00")),
        row=1, col=3,
    )
    fig_plotly.update_xaxes(title_text="k", row=1, col=1)
    fig_plotly.update_xaxes(title_text="k", row=1, col=2)
    fig_plotly.update_xaxes(title_text="k", row=1, col=3)
    fig_plotly.update_layout(
        title="Optimal K — three perspectives",
        height=400,
        showlegend=True,
    )
    return fig_mpl, fig_plotly


# -----------------------------------------------------------------------------
# Chart 08: cross-well centroid consistency
# -----------------------------------------------------------------------------

def cross_well_centroids(
    master: pd.DataFrame,
    target_zone: str,
    labels: pd.Series,
    features: list[str],
    label_name: str = "sub_zone",
) -> tuple[plt.Figure, go.Figure]:
    """Show cluster centroids in (vsh, log_perm) space, with per-well
    centroids overlaid as crosses.

    If the per-well crosses cluster tightly around each pooled centroid,
    sub-zones are reproducible across wells.
    """
    from src.clustering.subzone import DERIVED_FEATURE_FORMULAE

    zone_samples = master.loc[labels.index, ["well", "vsh", "phit", "perm"]].copy()
    zone_samples["log_perm"] = DERIVED_FEATURE_FORMULAE["log_perm"](zone_samples)
    zone_samples[label_name] = labels.values

    n_clusters = int(zone_samples[label_name].nunique())

    # Pooled centroids
    pooled = (
        zone_samples.groupby(label_name)[["vsh", "log_perm"]].mean().reset_index()
    )

    # Per-well centroids
    per_well = (
        zone_samples.groupby(["well", label_name])[["vsh", "log_perm"]].mean().reset_index()
    )

    # ---- matplotlib ----
    fig_mpl, ax = plt.subplots(figsize=(9, 6))

    # Background: all samples as faint scatter
    for sub_id in range(n_clusters):
        sd = zone_samples[zone_samples[label_name] == sub_id]
        ax.scatter(
            sd["vsh"], sd["log_perm"],
            s=4, alpha=0.10,
            color=SUBZONE_COLORS.get(sub_id, "#000000"),
        )

    # Per-well centroids: crosses
    for sub_id in range(n_clusters):
        pd_centroids = per_well[per_well[label_name] == sub_id]
        ax.scatter(
            pd_centroids["vsh"], pd_centroids["log_perm"],
            s=80, marker="x", linewidths=1.5,
            color=SUBZONE_COLORS.get(sub_id, "#000000"),
        )

    # Pooled centroids: big stars
    for _, row in pooled.iterrows():
        sub_id = int(row[label_name])
        ax.scatter(
            row["vsh"], row["log_perm"],
            s=400, marker="*", edgecolors="black", linewidths=1.5,
            color=SUBZONE_COLORS.get(sub_id, "#000000"),
            label=f"Sub-zone {sub_id} (pooled)",
            zorder=5,
        )

    ax.set_xlabel("vsh")
    ax.set_ylabel("log₁₀(perm) [mD]")
    ax.set_title(
        f"Zone {target_zone} sub-zone centroids in feature space\n"
        f"⋆ = pooled centroid    ✕ = per-well centroid    · = sample"
    )
    ax.legend(loc="lower left", framealpha=0.9)
    ax.grid(alpha=0.3)
    fig_mpl.tight_layout()

    # ---- plotly ----
    fig_plotly = go.Figure()
    for sub_id in range(n_clusters):
        sd = zone_samples[zone_samples[label_name] == sub_id]
        fig_plotly.add_trace(
            go.Scatter(
                x=sd["vsh"], y=sd["log_perm"],
                mode="markers",
                marker=dict(size=4, opacity=0.15,
                            color=SUBZONE_COLORS.get(sub_id, "#000000")),
                name=f"Sub-zone {sub_id} samples",
                showlegend=False,
                hoverinfo="skip",
            )
        )
        pwd = per_well[per_well[label_name] == sub_id]
        fig_plotly.add_trace(
            go.Scatter(
                x=pwd["vsh"], y=pwd["log_perm"],
                mode="markers",
                marker=dict(symbol="x", size=10, line=dict(width=2),
                            color=SUBZONE_COLORS.get(sub_id, "#000000")),
                name=f"Sub-zone {sub_id} per-well",
                text=[f"well {w}" for w in pwd["well"]],
                hovertemplate="%{text}<br>vsh: %{x:.3f}<br>log_perm: %{y:.2f}<extra></extra>",
            )
        )
    for _, row in pooled.iterrows():
        sub_id = int(row[label_name])
        fig_plotly.add_trace(
            go.Scatter(
                x=[row["vsh"]], y=[row["log_perm"]],
                mode="markers",
                marker=dict(symbol="star", size=18,
                            color=SUBZONE_COLORS.get(sub_id, "#000000"),
                            line=dict(color="black", width=1.5)),
                name=f"Sub-zone {sub_id} pooled",
            )
        )
    fig_plotly.update_layout(
        title=f"Zone {target_zone} sub-zone centroids — pooled vs per-well",
        xaxis_title="vsh",
        yaxis_title="log₁₀(perm) [mD]",
        height=500,
    )
    return fig_mpl, fig_plotly


# -----------------------------------------------------------------------------
# Save helper (mirrors src.visualization.field.save_chart)
# -----------------------------------------------------------------------------

def save_chart(
    fig_mpl: plt.Figure,
    fig_plotly: go.Figure,
    name: str,
    figures_dir: Path,
    dpi: int = 150,
) -> None:
    figures_dir.mkdir(parents=True, exist_ok=True)
    png_path = figures_dir / f"{name}.png"
    html_path = figures_dir / f"{name}.html"
    fig_mpl.savefig(png_path, dpi=dpi, bbox_inches="tight")
    plt.close(fig_mpl)
    fig_plotly.write_html(html_path, include_plotlyjs="cdn")
    logger.info(f"Saved {png_path}")
    logger.info(f"Saved {html_path}")
