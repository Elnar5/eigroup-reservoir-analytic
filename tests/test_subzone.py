"""
Tests for src.clustering.subzone (Part D).

We test:
    1. Feature engineering computes derived features correctly.
    2. Optimal-K search returns expected array shapes and ranges.
    3. Clustering produces labels in [0, n_clusters-1], ascending by log_perm.
    4. Smoothing reduces single-sample label flips.
    5. LOWO validation produces ARI > 0.7 on geologically separated data.
    6. Sub-zone metrics roll-up matches per-group sums.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from sklearn.preprocessing import StandardScaler

from src.clustering.subzone import (
    DERIVED_FEATURE_FORMULAE,
    _absorb_short_runs,
    _rolling_mode,
    build_feature_frame,
    fit_clustering,
    leave_one_well_out_validation,
    search_optimal_k,
    smooth_labels,
    subzone_metrics,
)


# -----------------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------------

@pytest.fixture
def master_3_subzones() -> pd.DataFrame:
    """3 wells × Zone B with 3 stacked geological sub-units: tight, mid,
    high-perm. The clusters should be obvious from features alone."""
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
                    "vsh": rng.uniform(*vsh_r),
                    "phit": rng.uniform(*phit_r),
                    "sw": rng.uniform(0.3, 0.6),
                    "perm": rng.uniform(*perm_r),
                })
                depth += 0.2
    return pd.DataFrame(rows)


@pytest.fixture
def features_default():
    return ["vsh", "phit", "log_perm", "sw", "effective_porosity", "hc_porosity"]


# -----------------------------------------------------------------------------
# Feature engineering
# -----------------------------------------------------------------------------

class TestFeatureEngineering:
    def test_log_perm_clips_zero(self):
        df = pd.DataFrame({"perm": [0.0, 0.0001, 100.0, 15000.0]})
        result = DERIVED_FEATURE_FORMULAE["log_perm"](df)
        assert np.isfinite(result).all()
        # Both perm=0 and perm=0.0001 get clipped to the same floor (1e-3),
        # so they share log_perm = -3. From there it must be monotone up.
        assert result.iloc[0] == result.iloc[1] == pytest.approx(-3.0)
        assert result.iloc[1] < result.iloc[2] < result.iloc[3]

    def test_effective_porosity_formula(self):
        df = pd.DataFrame({"phit": [0.20, 0.10], "vsh": [0.30, 0.50]})
        result = DERIVED_FEATURE_FORMULAE["effective_porosity"](df)
        assert result.iloc[0] == pytest.approx(0.14)  # 0.20 * 0.70
        assert result.iloc[1] == pytest.approx(0.05)  # 0.10 * 0.50

    def test_hc_porosity_formula(self):
        df = pd.DataFrame({"phit": [0.20], "sw": [0.40]})
        result = DERIVED_FEATURE_FORMULAE["hc_porosity"](df)
        assert result.iloc[0] == pytest.approx(0.12)  # 0.20 * 0.60

    def test_build_feature_frame_drops_nan(self, master_3_subzones):
        df = master_3_subzones.copy()
        df.loc[5, "phit"] = np.nan
        features = ["vsh", "phit", "log_perm"]
        out = build_feature_frame(df, features)
        assert out.isna().sum().sum() == 0
        assert len(out) == len(df) - 1

    def test_build_feature_frame_missing_raw_feature_raises(self):
        df = pd.DataFrame({"vsh": [0.2]})
        with pytest.raises(ValueError, match="Cannot compute"):
            build_feature_frame(df, ["nonexistent"])


# -----------------------------------------------------------------------------
# Optimal-K search
# -----------------------------------------------------------------------------

class TestOptimalK:
    def test_returns_arrays_of_correct_length(self, master_3_subzones, features_default):
        zone_b = master_3_subzones[master_3_subzones["zone"] == "B"]
        fdf = build_feature_frame(zone_b, features_default)
        X = StandardScaler().fit_transform(fdf.values)
        opt = search_optimal_k(X, k_min=2, k_max=5)
        assert opt.k_range == [2, 3, 4, 5]
        assert len(opt.kmeans_inertia) == 4
        assert len(opt.kmeans_silhouette) == 4
        assert len(opt.gmm_bic) == 4

    def test_inertia_monotonically_decreasing(self, master_3_subzones, features_default):
        """K-Means inertia should ALWAYS decrease as k grows (more centroids
        = less unexplained variance)."""
        zone_b = master_3_subzones[master_3_subzones["zone"] == "B"]
        fdf = build_feature_frame(zone_b, features_default)
        X = StandardScaler().fit_transform(fdf.values)
        opt = search_optimal_k(X, k_min=2, k_max=6)
        diffs = np.diff(opt.kmeans_inertia)
        assert (diffs <= 1e-6).all()  # allow tiny numerical noise

    def test_silhouettes_in_valid_range(self, master_3_subzones, features_default):
        zone_b = master_3_subzones[master_3_subzones["zone"] == "B"]
        fdf = build_feature_frame(zone_b, features_default)
        X = StandardScaler().fit_transform(fdf.values)
        opt = search_optimal_k(X, k_min=2, k_max=5)
        for s in opt.kmeans_silhouette + opt.gmm_silhouette:
            assert -1.0 <= s <= 1.0


# -----------------------------------------------------------------------------
# Clustering
# -----------------------------------------------------------------------------

class TestClustering:
    def test_kmeans_returns_valid_labels(self, master_3_subzones, features_default):
        result = fit_clustering(master_3_subzones, "B", features_default,
                                method="kmeans", n_clusters=3)
        assert result.method == "kmeans"
        assert result.n_clusters == 3
        assert set(result.labels) <= {0, 1, 2}
        assert len(result.labels) == len(result.feature_df)

    def test_gmm_returns_valid_labels(self, master_3_subzones, features_default):
        result = fit_clustering(master_3_subzones, "B", features_default,
                                method="gmm", n_clusters=3)
        assert set(result.labels) <= {0, 1, 2}

    def test_labels_ordered_by_log_perm(self, master_3_subzones, features_default):
        """After _reorder_labels_by_log_perm, cluster 0 should have lowest
        mean log_perm and k-1 highest."""
        result = fit_clustering(master_3_subzones, "B", features_default,
                                method="kmeans", n_clusters=3)
        centroids = result.centroids_original_scale.xs("mean", level=1, axis=1)
        log_perm_means = centroids["log_perm"].values
        assert all(log_perm_means[i] < log_perm_means[i + 1]
                   for i in range(len(log_perm_means) - 1))

    def test_silhouette_above_threshold(self, master_3_subzones, features_default):
        """For well-separated synthetic data, silhouette should be > 0.3."""
        result = fit_clustering(master_3_subzones, "B", features_default,
                                method="kmeans", n_clusters=3)
        assert result.silhouette > 0.3

    def test_invalid_method_raises(self, master_3_subzones, features_default):
        with pytest.raises(ValueError, match="method must be"):
            fit_clustering(master_3_subzones, "B", features_default,
                           method="dbscan", n_clusters=3)

    def test_empty_zone_raises(self, master_3_subzones, features_default):
        with pytest.raises(ValueError, match="No samples found"):
            fit_clustering(master_3_subzones, "Z", features_default,
                           method="kmeans", n_clusters=3)


# -----------------------------------------------------------------------------
# Smoothing
# -----------------------------------------------------------------------------

class TestSmoothing:
    def test_rolling_mode_basic(self):
        arr = np.array([0, 0, 1, 0, 0])
        # window=3 mode at each position: 0,0,0,0,0 (the lone 1 gets absorbed)
        out = _rolling_mode(arr, window=3)
        assert out.tolist() == [0, 0, 0, 0, 0]

    def test_rolling_mode_preserves_runs(self):
        arr = np.array([0, 0, 0, 1, 1, 1, 1])
        out = _rolling_mode(arr, window=3)
        # Run boundary moves at most one sample
        assert out.tolist() == [0, 0, 0, 0, 1, 1, 1] or out.tolist() == [0, 0, 0, 1, 1, 1, 1]

    def test_absorb_short_runs_drops_singletons(self):
        # Run lengths: 3, 1, 4
        arr = np.array([0, 0, 0, 1, 2, 2, 2, 2])
        out = _absorb_short_runs(arr, min_run_length=2)
        # The lone '1' should be absorbed by its longer neighbour (cluster 2, len 4)
        assert 1 not in out

    def test_absorb_keeps_long_enough_runs(self):
        arr = np.array([0, 0, 0, 1, 1, 1, 1, 2, 2, 2])
        out = _absorb_short_runs(arr, min_run_length=3)
        # All three runs are >= 3, nothing should change
        np.testing.assert_array_equal(out, arr)

    def test_smooth_labels_returns_same_index(self, master_3_subzones, features_default):
        result = fit_clustering(master_3_subzones, "B", features_default,
                                method="kmeans", n_clusters=3)
        labels = pd.Series(result.labels, index=result.feature_df.index)
        smoothed = smooth_labels(master_3_subzones, "B", labels)
        assert smoothed.index.equals(labels.index)

    def test_smooth_labels_window_must_be_odd(self, master_3_subzones, features_default):
        result = fit_clustering(master_3_subzones, "B", features_default,
                                method="kmeans", n_clusters=3)
        labels = pd.Series(result.labels, index=result.feature_df.index)
        with pytest.raises(ValueError, match="must be odd"):
            smooth_labels(master_3_subzones, "B", labels, window_size=10)


# -----------------------------------------------------------------------------
# Cross-well validation
# -----------------------------------------------------------------------------

class TestLOWO:
    def test_returns_one_row_per_well(self, master_3_subzones, features_default):
        result = fit_clustering(master_3_subzones, "B", features_default,
                                method="kmeans", n_clusters=3)
        lowo = leave_one_well_out_validation(
            master_3_subzones, "B", features_default, result,
            method="kmeans", n_clusters=3,
        )
        assert len(lowo) == 3  # 3 wells

    def test_ari_high_on_separable_data(self, master_3_subzones, features_default):
        """On geologically separable synthetic data, ARI should be > 0.4 for
        every fold and > 0.7 on average. (Small synthetic well samples can
        give one weak fold; the average is the more meaningful signal.)"""
        result = fit_clustering(master_3_subzones, "B", features_default,
                                method="kmeans", n_clusters=3)
        lowo = leave_one_well_out_validation(
            master_3_subzones, "B", features_default, result,
            method="kmeans", n_clusters=3,
        )
        assert (lowo["ari_vs_pooled"] > 0.4).all(), \
            f"Per-fold ARI too low: {lowo['ari_vs_pooled'].tolist()}"
        assert lowo["ari_vs_pooled"].mean() > 0.7, \
            f"Mean ARI too low: {lowo['ari_vs_pooled'].mean():.3f}"


# -----------------------------------------------------------------------------
# Sub-zone metrics
# -----------------------------------------------------------------------------

class TestSubzoneMetrics:
    def test_one_row_per_well_subzone_pair(self, master_3_subzones, features_default):
        result = fit_clustering(master_3_subzones, "B", features_default,
                                method="kmeans", n_clusters=3)
        labels = pd.Series(result.labels, index=result.feature_df.index)
        metrics = subzone_metrics(master_3_subzones, "B", labels)
        # 3 wells × 3 sub-zones = 9
        assert len(metrics) == 9

    def test_thickness_equals_dz_sum(self, master_3_subzones, features_default):
        result = fit_clustering(master_3_subzones, "B", features_default,
                                method="kmeans", n_clusters=3)
        labels = pd.Series(result.labels, index=result.feature_df.index)
        metrics = subzone_metrics(master_3_subzones, "B", labels)
        # Total thickness summed across sub-zones per well should equal Zone B
        # thickness for that well
        for well in metrics["well"].unique():
            sub_total = metrics[metrics["well"] == well]["thickness_m"].sum()
            zone_total = (
                master_3_subzones[
                    (master_3_subzones["well"] == well)
                    & (master_3_subzones["zone"] == "B")
                ]["dz"].sum()
            )
            assert sub_total == pytest.approx(zone_total)

    def test_kh_sums_to_zone_kh(self, master_3_subzones, features_default):
        """Sum of sub-zone kh per well should equal total Zone B kh per well."""
        result = fit_clustering(master_3_subzones, "B", features_default,
                                method="kmeans", n_clusters=3)
        labels = pd.Series(result.labels, index=result.feature_df.index)
        metrics = subzone_metrics(master_3_subzones, "B", labels)
        for well in metrics["well"].unique():
            sub_kh = metrics[metrics["well"] == well]["kh_mD_m"].sum()
            zone_b = master_3_subzones[
                (master_3_subzones["well"] == well)
                & (master_3_subzones["zone"] == "B")
            ]
            zone_kh = float((zone_b["perm"] * zone_b["dz"]).sum())
            assert sub_kh == pytest.approx(zone_kh)
