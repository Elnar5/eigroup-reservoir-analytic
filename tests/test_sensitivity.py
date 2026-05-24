"""
Tests for src.analytics.sensitivity (Part C.1).

We test:
    1. Sweep monotonicity: looser vsh cutoff -> net_thickness never decreases.
    2. Sweep frame structure: row count = n_cutoffs * n_(well,zone) groups.
    3. Bootstrap CI structure: low <= mean <= high; lengths match.
    4. Knee detection: identifies the cutoff with largest NTG jump.
    5. Field summary roll-up: sums match per-zone totals.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.analytics.sensitivity import (
    bootstrap_kh_ci,
    detect_knee_points,
    field_sweep_summary,
    run_vsh_sweep,
)


# -----------------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------------

@pytest.fixture
def master_two_wells_two_zones() -> pd.DataFrame:
    """Reproducible synthetic master table: 2 wells × 2 zones × 30 samples each.
    Zone A has low vsh (clean reservoir), Zone B has high vsh (shaly).
    """
    rng = np.random.default_rng(42)
    rows = []
    for well in [1, 2]:
        for zone, vsh_range in [("A", (0.1, 0.4)), ("B", (0.4, 0.75))]:
            for i in range(30):
                rows.append(
                    {
                        "well": well,
                        "zone": zone,
                        "depth": 2000.0 + i * 0.2,
                        "vsh": rng.uniform(*vsh_range),
                        "phit": rng.uniform(0.12, 0.25),
                        "sw": 0.5,
                        "perm": rng.uniform(50, 500),
                        "dz": 0.2,
                    }
                )
    return pd.DataFrame(rows)


# -----------------------------------------------------------------------------
# Sweep behaviour
# -----------------------------------------------------------------------------

class TestSweep:
    def test_row_count_equals_cutoffs_times_groups(self, master_two_wells_two_zones):
        sweep = run_vsh_sweep(
            master_two_wells_two_zones, vsh_min=0.3, vsh_max=0.7, vsh_step=0.05
        )
        # 9 cutoffs × 4 (well, zone) groups = 36
        assert len(sweep) == 36

    def test_cutoffs_endpoints_inclusive(self, master_two_wells_two_zones):
        sweep = run_vsh_sweep(
            master_two_wells_two_zones, vsh_min=0.3, vsh_max=0.7, vsh_step=0.05
        )
        cutoffs = sorted(sweep["vsh_cutoff"].unique())
        assert cutoffs[0] == pytest.approx(0.30)
        assert cutoffs[-1] == pytest.approx(0.70)
        # Step uniformity
        diffs = np.diff(cutoffs)
        assert np.allclose(diffs, 0.05)

    def test_net_thickness_monotone_per_group(self, master_two_wells_two_zones):
        """Looser vsh_max can only add (or keep) samples to net, never remove."""
        sweep = run_vsh_sweep(
            master_two_wells_two_zones, vsh_min=0.3, vsh_max=0.7, vsh_step=0.05
        )
        for (well, zone), group in sweep.groupby(["well", "zone"]):
            g = group.sort_values("vsh_cutoff")
            assert g["net_thickness_m"].is_monotonic_increasing, (
                f"(well={well}, zone={zone}) net_thickness not monotone"
            )

    def test_ntg_monotone_per_group(self, master_two_wells_two_zones):
        sweep = run_vsh_sweep(
            master_two_wells_two_zones, vsh_min=0.3, vsh_max=0.7, vsh_step=0.05
        )
        for (well, zone), group in sweep.groupby(["well", "zone"]):
            g = group.sort_values("vsh_cutoff")
            assert g["ntg"].is_monotonic_increasing

    def test_kh_monotone_per_group(self, master_two_wells_two_zones):
        sweep = run_vsh_sweep(
            master_two_wells_two_zones, vsh_min=0.3, vsh_max=0.7, vsh_step=0.05
        )
        for (well, zone), group in sweep.groupby(["well", "zone"]):
            g = group.sort_values("vsh_cutoff")
            assert g["kh_mD_m"].is_monotonic_increasing

    def test_gross_thickness_constant_across_cutoffs(self, master_two_wells_two_zones):
        """Gross thickness is the zone thickness — independent of net cutoff."""
        sweep = run_vsh_sweep(
            master_two_wells_two_zones, vsh_min=0.3, vsh_max=0.7, vsh_step=0.05
        )
        for (well, zone), group in sweep.groupby(["well", "zone"]):
            assert group["gross_thickness_m"].nunique() == 1, (
                f"(well={well}, zone={zone}) gross_thickness should be invariant"
            )

    def test_invalid_range_raises(self, master_two_wells_two_zones):
        with pytest.raises(ValueError, match="must be <"):
            run_vsh_sweep(master_two_wells_two_zones, vsh_min=0.7, vsh_max=0.3)

    def test_invalid_step_raises(self, master_two_wells_two_zones):
        with pytest.raises(ValueError, match="step must be positive"):
            run_vsh_sweep(master_two_wells_two_zones, vsh_step=0)


# -----------------------------------------------------------------------------
# Bootstrap CI
# -----------------------------------------------------------------------------

class TestBootstrap:
    def test_ci_low_le_mean_le_high(self, master_two_wells_two_zones):
        ci = bootstrap_kh_ci(
            master_two_wells_two_zones, vsh_cutoffs=[0.5], n_bootstrap=100
        )
        assert (ci["kh_p_low"] <= ci["kh_mean"]).all()
        assert (ci["kh_mean"] <= ci["kh_p_high"]).all()

    def test_ci_one_row_per_group_per_cutoff(self, master_two_wells_two_zones):
        cutoffs = [0.3, 0.5, 0.7]
        ci = bootstrap_kh_ci(
            master_two_wells_two_zones, vsh_cutoffs=cutoffs, n_bootstrap=50
        )
        # 4 (well, zone) groups × 3 cutoffs = 12 rows
        assert len(ci) == 12

    def test_ci_kh_std_non_negative(self, master_two_wells_two_zones):
        ci = bootstrap_kh_ci(
            master_two_wells_two_zones, vsh_cutoffs=[0.5], n_bootstrap=100
        )
        assert (ci["kh_std"] >= 0).all()

    def test_ci_reproducible_with_seed(self, master_two_wells_two_zones):
        ci1 = bootstrap_kh_ci(
            master_two_wells_two_zones, vsh_cutoffs=[0.5], n_bootstrap=50,
            random_state=123,
        )
        ci2 = bootstrap_kh_ci(
            master_two_wells_two_zones, vsh_cutoffs=[0.5], n_bootstrap=50,
            random_state=123,
        )
        # Same seed -> identical means
        pd.testing.assert_series_equal(
            ci1["kh_mean"].reset_index(drop=True),
            ci2["kh_mean"].reset_index(drop=True),
        )

    def test_ci_different_seeds_differ(self, master_two_wells_two_zones):
        ci1 = bootstrap_kh_ci(
            master_two_wells_two_zones, vsh_cutoffs=[0.5], n_bootstrap=50,
            random_state=1,
        )
        ci2 = bootstrap_kh_ci(
            master_two_wells_two_zones, vsh_cutoffs=[0.5], n_bootstrap=50,
            random_state=2,
        )
        # Different seeds -> at least some difference
        assert not np.allclose(ci1["kh_mean"], ci2["kh_mean"])


# -----------------------------------------------------------------------------
# Knee detection
# -----------------------------------------------------------------------------

class TestKneeDetection:
    def test_returns_one_row_per_group(self, master_two_wells_two_zones):
        sweep = run_vsh_sweep(
            master_two_wells_two_zones, vsh_min=0.3, vsh_max=0.7, vsh_step=0.05
        )
        knees = detect_knee_points(sweep, metric="ntg")
        assert len(knees) == 4  # 2 wells × 2 zones

    def test_knee_cutoff_within_sweep_range(self, master_two_wells_two_zones):
        sweep = run_vsh_sweep(
            master_two_wells_two_zones, vsh_min=0.3, vsh_max=0.7, vsh_step=0.05
        )
        knees = detect_knee_points(sweep, metric="ntg")
        assert (knees["knee_cutoff"] >= 0.3).all()
        assert (knees["knee_cutoff"] <= 0.7).all()

    def test_invalid_metric_raises(self, master_two_wells_two_zones):
        sweep = run_vsh_sweep(
            master_two_wells_two_zones, vsh_min=0.3, vsh_max=0.7, vsh_step=0.05
        )
        with pytest.raises(ValueError, match="not in sweep_results"):
            detect_knee_points(sweep, metric="nonexistent_column")

    def test_zone_b_knee_higher_than_zone_a(self, master_two_wells_two_zones):
        """Zone B has higher vsh distribution -> its knee occurs at a higher cutoff."""
        sweep = run_vsh_sweep(
            master_two_wells_two_zones, vsh_min=0.3, vsh_max=0.7, vsh_step=0.05
        )
        knees = detect_knee_points(sweep, metric="ntg")
        zone_a_knees = knees[knees["zone"] == "A"]["knee_cutoff"].mean()
        zone_b_knees = knees[knees["zone"] == "B"]["knee_cutoff"].mean()
        assert zone_b_knees > zone_a_knees


# -----------------------------------------------------------------------------
# Field roll-up
# -----------------------------------------------------------------------------

class TestFieldSweepSummary:
    def test_row_count_zones_times_cutoffs(self, master_two_wells_two_zones):
        sweep = run_vsh_sweep(
            master_two_wells_two_zones, vsh_min=0.3, vsh_max=0.7, vsh_step=0.05
        )
        summary = field_sweep_summary(sweep)
        # 2 zones × 9 cutoffs = 18
        assert len(summary) == 18

    def test_net_total_equals_per_zone_sum(self, master_two_wells_two_zones):
        sweep = run_vsh_sweep(
            master_two_wells_two_zones, vsh_min=0.3, vsh_max=0.7, vsh_step=0.05
        )
        summary = field_sweep_summary(sweep)
        for _, row in summary.iterrows():
            expected = sweep[
                (sweep["zone"] == row["zone"])
                & (sweep["vsh_cutoff"] == row["vsh_cutoff"])
            ]["net_thickness_m"].sum()
            assert row["net_thickness_total"] == pytest.approx(expected)

    def test_ntg_field_in_unit_interval(self, master_two_wells_two_zones):
        sweep = run_vsh_sweep(
            master_two_wells_two_zones, vsh_min=0.3, vsh_max=0.7, vsh_step=0.05
        )
        summary = field_sweep_summary(sweep)
        assert ((summary["ntg_field"] >= 0) & (summary["ntg_field"] <= 1)).all()
