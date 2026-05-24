"""
Smoke tests for src.visualization.clustering.

Verify that each chart function returns both a matplotlib Figure and a
plotly Figure, with the expected number of traces, and that save_chart
writes both PNG and HTML.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import pytest
from sklearn.preprocessing import StandardScaler

from src.clustering.subzone import (
    build_feature_frame,
    fit_clustering,
    search_optimal_k,
    smooth_labels,
)
from src.visualization.clustering import (
    SUBZONE_COLORS,
    cross_well_centroids,
    depth_profile_per_well,
    optimal_k_plot,
    save_chart,
)


# -----------------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------------

@pytest.fixture
def master_3_subzones() -> pd.DataFrame:
    rng = np.random.default_rng(42)
    rows = []
    for well in [1, 2, 3]:
        depth = 2100.0
        for sub_type, n, vsh_r, phit_r, perm_r in [
            ("tight", 60, (0.30, 0.45), (0.08, 0.13), (1, 50)),
            ("mid", 80, (0.15, 0.30), (0.15, 0.22), (100, 1000)),
            ("high", 60, (0.10, 0.20), (0.20, 0.28), (3000, 15000)),
        ]:
            for i in range(n):
                rows.append({
                    "well": well, "zone": "B", "depth": depth, "dz": 0.2,
                    "vsh": rng.uniform(*vsh_r), "phit": rng.uniform(*phit_r),
                    "sw": rng.uniform(0.3, 0.6), "perm": rng.uniform(*perm_r),
                })
                depth += 0.2
    return pd.DataFrame(rows)


@pytest.fixture
def clustering_artefacts(master_3_subzones):
    features = ["vsh", "phit", "log_perm", "sw", "effective_porosity", "hc_porosity"]
    fdf = build_feature_frame(master_3_subzones[master_3_subzones.zone == "B"], features)
    X = StandardScaler().fit_transform(fdf.values)
    opt = search_optimal_k(X, k_min=2, k_max=5)
    result = fit_clustering(master_3_subzones, "B", features, method="kmeans", n_clusters=3)
    labels = pd.Series(result.labels, index=result.feature_df.index)
    smoothed = smooth_labels(master_3_subzones, "B", labels)
    return {
        "master": master_3_subzones,
        "features": features,
        "optimal_k": opt,
        "result": result,
        "smoothed": smoothed,
    }


# -----------------------------------------------------------------------------
# Charts
# -----------------------------------------------------------------------------

class TestDepthProfile:
    def test_returns_both_figures(self, clustering_artefacts):
        fig_m, fig_p = depth_profile_per_well(
            clustering_artefacts["master"], "B", clustering_artefacts["smoothed"]
        )
        assert isinstance(fig_m, plt.Figure)
        assert isinstance(fig_p, go.Figure)
        plt.close(fig_m)

    def test_plotly_has_one_trace_per_cluster(self, clustering_artefacts):
        _, fig_p = depth_profile_per_well(
            clustering_artefacts["master"], "B", clustering_artefacts["smoothed"]
        )
        n_clusters = clustering_artefacts["smoothed"].nunique()
        assert len(fig_p.data) == n_clusters


class TestOptimalKPlot:
    def test_three_panels(self, clustering_artefacts):
        fig_m, _ = optimal_k_plot(clustering_artefacts["optimal_k"])
        assert len(fig_m.axes) == 3
        plt.close(fig_m)

    def test_plotly_has_four_traces(self, clustering_artefacts):
        """elbow (1) + KMeans silhouette + GMM silhouette + GMM BIC = 4"""
        _, fig_p = optimal_k_plot(clustering_artefacts["optimal_k"])
        assert len(fig_p.data) == 4


class TestCrossWellCentroids:
    def test_returns_both_figures(self, clustering_artefacts):
        fig_m, fig_p = cross_well_centroids(
            clustering_artefacts["master"], "B",
            clustering_artefacts["smoothed"], clustering_artefacts["features"]
        )
        assert isinstance(fig_m, plt.Figure)
        assert isinstance(fig_p, go.Figure)
        plt.close(fig_m)

    def test_plotly_has_traces_per_cluster_plus_pooled(self, clustering_artefacts):
        """Per cluster: samples scatter + per-well crosses + pooled star
        = 3 traces per cluster × 3 clusters = 9"""
        _, fig_p = cross_well_centroids(
            clustering_artefacts["master"], "B",
            clustering_artefacts["smoothed"], clustering_artefacts["features"]
        )
        n_clusters = clustering_artefacts["smoothed"].nunique()
        assert len(fig_p.data) == 3 * n_clusters


# -----------------------------------------------------------------------------
# Save round-trip
# -----------------------------------------------------------------------------

class TestSaveChart:
    def test_writes_png_and_html(self, clustering_artefacts, tmp_path: Path):
        fig_m, fig_p = depth_profile_per_well(
            clustering_artefacts["master"], "B", clustering_artefacts["smoothed"]
        )
        save_chart(fig_m, fig_p, "test_subzone", tmp_path)
        assert (tmp_path / "test_subzone.png").exists()
        assert (tmp_path / "test_subzone.html").exists()


# -----------------------------------------------------------------------------
# Palette consistency
# -----------------------------------------------------------------------------

class TestPalette:
    def test_subzone_colors_are_distinct(self):
        values = list(SUBZONE_COLORS.values())
        assert len(values) == len(set(values))
