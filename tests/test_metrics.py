"""
Tests for src.analytics.metrics

We test invariants the math must satisfy regardless of input, and the three
real-data behaviours we baked into the design:
    1. NaN porosity samples are excluded from net (well_3 motivation).
    2. Permeability-saturated samples ARE counted in kh but flagged.
    3. Mixed dz (well_5 = 0.5 m, others = 0.2 m) is respected per group.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.analytics.metrics import (
    PERM_SATURATION_THRESHOLD,
    _lorenz_coefficient,
    compute_all_zone_metrics,
    compute_zone_metrics,
    field_summary_by_well,
    field_summary_by_zone,
)


# -----------------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------------

@pytest.fixture
def tiny_group() -> pd.DataFrame:
    """5 samples, all net, dz=0.2, known answers we can verify by hand."""
    return pd.DataFrame(
        {
            "vsh": [0.2, 0.3, 0.25, 0.4, 0.35],
            "phit": [0.20, 0.18, 0.22, 0.15, 0.19],
            "sw": [0.5, 0.5, 0.5, 0.5, 0.5],
            "perm": [100.0, 200.0, 150.0, 80.0, 120.0],
            "dz": [0.2, 0.2, 0.2, 0.2, 0.2],
        }
    )


@pytest.fixture
def master_synthetic() -> pd.DataFrame:
    """Two wells, two zones each. Mixed dz to mimic well_5's 0.5 m step."""
    rng = np.random.default_rng(42)
    rows = []

    # well 1: dz=0.2, 20 rows per zone
    for zone in ("A", "B"):
        for i in range(20):
            rows.append(
                {
                    "well": 1,
                    "zone": zone,
                    "depth": 2000.0 + i * 0.2,
                    "vsh": rng.uniform(0.1, 0.4),
                    "phit": rng.uniform(0.15, 0.25),
                    "sw": rng.uniform(0.3, 0.6),
                    "perm": rng.uniform(100, 500),
                    "dz": 0.2,
                }
            )

    # well 2: dz=0.5 (well_5-style), 8 rows per zone
    for zone in ("A", "B"):
        for i in range(8):
            rows.append(
                {
                    "well": 2,
                    "zone": zone,
                    "depth": 2050.0 + i * 0.5,
                    "vsh": rng.uniform(0.1, 0.4),
                    "phit": rng.uniform(0.15, 0.25),
                    "sw": rng.uniform(0.3, 0.6),
                    "perm": rng.uniform(100, 500),
                    "dz": 0.5,
                }
            )

    return pd.DataFrame(rows)


# -----------------------------------------------------------------------------
# Core arithmetic invariants
# -----------------------------------------------------------------------------

class TestArithmeticInvariants:
    def test_gross_thickness_equals_dz_sum(self, tiny_group):
        out = compute_zone_metrics(tiny_group)
        assert out["gross_thickness_m"] == pytest.approx(1.0)  # 5 * 0.2

    def test_net_equals_gross_when_all_qualify(self, tiny_group):
        out = compute_zone_metrics(tiny_group)
        # All 5 samples have vsh <= 0.5 and phit >= 0.08
        assert out["net_thickness_m"] == pytest.approx(out["gross_thickness_m"])
        assert out["ntg"] == pytest.approx(1.0)

    def test_kh_equals_sum_perm_times_dz(self, tiny_group):
        out = compute_zone_metrics(tiny_group)
        expected = (tiny_group["perm"] * tiny_group["dz"]).sum()
        assert out["kh_mD_m"] == pytest.approx(expected)

    def test_kh_weighted_perm_equals_kh_over_net(self, tiny_group):
        out = compute_zone_metrics(tiny_group)
        assert out["avg_perm_kh_weighted_mD"] == pytest.approx(
            out["kh_mD_m"] / out["net_thickness_m"]
        )

    def test_avg_perm_arithmetic_vs_kh_weighted_can_differ(self, tiny_group):
        """For non-uniform dz, kh-weighted and arithmetic should differ.
        For uniform dz they should match. tiny_group is uniform, so equal."""
        out = compute_zone_metrics(tiny_group)
        assert out["avg_perm_mD"] == pytest.approx(out["avg_perm_kh_weighted_mD"])


class TestRangeInvariants:
    def test_ntg_in_unit_interval(self, master_synthetic):
        metrics = compute_all_zone_metrics(master_synthetic)
        assert ((metrics["ntg"] >= 0) & (metrics["ntg"] <= 1)).all()

    def test_lorenz_in_unit_interval(self, master_synthetic):
        metrics = compute_all_zone_metrics(master_synthetic)
        valid = metrics["lorenz_coefficient"].dropna()
        assert ((valid >= 0) & (valid <= 1)).all()

    def test_net_never_exceeds_gross(self, master_synthetic):
        metrics = compute_all_zone_metrics(master_synthetic)
        assert (metrics["net_thickness_m"] <= metrics["gross_thickness_m"] + 1e-9).all()

    def test_n_samples_net_le_n_samples(self, master_synthetic):
        metrics = compute_all_zone_metrics(master_synthetic)
        assert (metrics["n_samples_net"] <= metrics["n_samples"]).all()


# -----------------------------------------------------------------------------
# Real-data behaviours
# -----------------------------------------------------------------------------

class TestNaNHandling:
    """well_3 has 78 NaN phit samples — they must be excluded from net,
    counted separately, and never silently inflate any metric."""

    def test_nan_phit_excluded_from_net(self):
        df = pd.DataFrame(
            {
                "vsh": [0.2, 0.2, 0.2, 0.2],
                "phit": [0.20, np.nan, 0.18, np.nan],  # 2 NaN
                "sw": [0.5, 0.5, 0.5, 0.5],
                "perm": [100.0, 100.0, 100.0, 100.0],
                "dz": [0.2, 0.2, 0.2, 0.2],
            }
        )
        out = compute_zone_metrics(df)
        assert out["n_samples"] == 4
        assert out["n_samples_net"] == 2  # only the two non-NaN
        assert out["n_phit_nan"] == 2
        assert out["net_thickness_m"] == pytest.approx(0.4)
        assert out["gross_thickness_m"] == pytest.approx(0.8)  # gross includes NaN rows

    def test_nan_vsh_excluded_from_net(self):
        df = pd.DataFrame(
            {
                "vsh": [0.2, np.nan, 0.2],
                "phit": [0.20, 0.20, 0.20],
                "sw": [0.5, 0.5, 0.5],
                "perm": [100.0, 100.0, 100.0],
                "dz": [0.2, 0.2, 0.2],
            }
        )
        out = compute_zone_metrics(df)
        assert out["n_samples_net"] == 2

    def test_all_nan_gives_nan_averages(self):
        df = pd.DataFrame(
            {
                "vsh": [0.2, 0.2],
                "phit": [np.nan, np.nan],
                "sw": [0.5, 0.5],
                "perm": [100.0, 100.0],
                "dz": [0.2, 0.2],
            }
        )
        out = compute_zone_metrics(df)
        assert out["n_samples_net"] == 0
        assert out["kh_mD_m"] == 0.0
        assert np.isnan(out["avg_phit"])
        assert np.isnan(out["avg_perm_mD"])
        assert np.isnan(out["ntg"]) or out["ntg"] == 0.0


class TestPermSaturation:
    """Zone B has ~88% of net samples at 15000 mD cap. They MUST stay in kh
    (otherwise we under-estimate flow) but be counted so the consumer knows."""

    def test_saturated_samples_counted(self):
        df = pd.DataFrame(
            {
                "vsh": [0.2] * 5,
                "phit": [0.20] * 5,
                "sw": [0.5] * 5,
                "perm": [100.0, 200.0, 15000.0, 15000.0, 15000.0],
                "dz": [0.2] * 5,
            }
        )
        out = compute_zone_metrics(df)
        assert out["n_perm_saturated_in_net"] == 3

    def test_saturated_samples_remain_in_kh(self):
        df = pd.DataFrame(
            {
                "vsh": [0.2, 0.2],
                "phit": [0.20, 0.20],
                "sw": [0.5, 0.5],
                "perm": [100.0, 15000.0],
                "dz": [0.2, 0.2],
            }
        )
        out = compute_zone_metrics(df)
        expected_kh = (100.0 + 15000.0) * 0.2
        assert out["kh_mD_m"] == pytest.approx(expected_kh)

    def test_saturation_threshold_is_inclusive(self):
        """A sample at exactly 14999 mD should count as saturated."""
        df = pd.DataFrame(
            {
                "vsh": [0.2],
                "phit": [0.20],
                "sw": [0.5],
                "perm": [PERM_SATURATION_THRESHOLD],
                "dz": [0.2],
            }
        )
        out = compute_zone_metrics(df)
        assert out["n_perm_saturated_in_net"] == 1


class TestMixedDz:
    """well_5 has dz=0.5 while others have 0.2. kh and net_thickness
    must respect the per-sample dz column, not assume uniform spacing."""

    def test_kh_uses_per_sample_dz(self):
        df = pd.DataFrame(
            {
                "vsh": [0.2, 0.2],
                "phit": [0.20, 0.20],
                "sw": [0.5, 0.5],
                "perm": [100.0, 100.0],
                "dz": [0.2, 0.5],  # mixed
            }
        )
        out = compute_zone_metrics(df)
        # Expected: 100 * 0.2 + 100 * 0.5 = 70
        assert out["kh_mD_m"] == pytest.approx(70.0)
        assert out["net_thickness_m"] == pytest.approx(0.7)

    def test_two_wells_with_different_dz_produce_proportional_thickness(
        self, master_synthetic
    ):
        """well 1 (dz=0.2) and well 2 (dz=0.5) both pass through compute_all.
        Per-well thickness should scale with the dz they actually used."""
        metrics = compute_all_zone_metrics(master_synthetic)
        well1 = metrics[metrics["well"] == 1]
        well2 = metrics[metrics["well"] == 2]
        # well 1: 20 rows * 0.2 = 4.0 per zone gross
        # well 2:  8 rows * 0.5 = 4.0 per zone gross
        # so equal even though sample counts differ -> proves dz is per-sample
        for v in well1["gross_thickness_m"]:
            assert v == pytest.approx(4.0)
        for v in well2["gross_thickness_m"]:
            assert v == pytest.approx(4.0)


# -----------------------------------------------------------------------------
# Cutoff sensitivity (Part C.1 will rely on this)
# -----------------------------------------------------------------------------

class TestCutoffMonotonicity:
    def test_tighter_vsh_never_increases_net(self, master_synthetic):
        """Lowering vsh_max can only shrink (or keep equal) the net interval."""
        loose = compute_all_zone_metrics(master_synthetic, vsh_max=0.6)
        tight = compute_all_zone_metrics(master_synthetic, vsh_max=0.3)
        merged = loose.merge(
            tight, on=["well", "zone"], suffixes=("_loose", "_tight")
        )
        assert (
            merged["net_thickness_m_tight"]
            <= merged["net_thickness_m_loose"] + 1e-9
        ).all()

    def test_higher_phit_min_never_increases_net(self, master_synthetic):
        loose = compute_all_zone_metrics(master_synthetic, phit_min=0.05)
        tight = compute_all_zone_metrics(master_synthetic, phit_min=0.20)
        merged = loose.merge(
            tight, on=["well", "zone"], suffixes=("_loose", "_tight")
        )
        assert (
            merged["net_thickness_m_tight"]
            <= merged["net_thickness_m_loose"] + 1e-9
        ).all()


# -----------------------------------------------------------------------------
# Lorenz coefficient
# -----------------------------------------------------------------------------

class TestLorenz:
    def test_uniform_perm_gives_zero(self):
        """All samples identical -> perfectly homogeneous -> L=0."""
        df = pd.DataFrame(
            {"perm": [100.0] * 10, "phit": [0.2] * 10, "dz": [0.2] * 10}
        )
        assert _lorenz_coefficient(df) == pytest.approx(0.0, abs=1e-6)

    def test_extreme_heterogeneity_close_to_one(self):
        """One sample dominates -> L close to 1."""
        df = pd.DataFrame(
            {
                "perm": [10000.0] + [0.01] * 99,
                "phit": [0.2] * 100,
                "dz": [0.2] * 100,
            }
        )
        L = _lorenz_coefficient(df)
        assert L > 0.95  # not exactly 1 because storage isn't concentrated too

    def test_empty_returns_nan(self):
        df = pd.DataFrame({"perm": [], "phit": [], "dz": []})
        assert np.isnan(_lorenz_coefficient(df))


# -----------------------------------------------------------------------------
# Field summaries
# -----------------------------------------------------------------------------

class TestFieldSummaries:
    def test_by_zone_kh_total_equals_sum_of_groups(self, master_synthetic):
        metrics = compute_all_zone_metrics(master_synthetic)
        by_zone = field_summary_by_zone(metrics)
        for zone in by_zone["zone"]:
            expected = metrics.loc[metrics["zone"] == zone, "kh_mD_m"].sum()
            actual = by_zone.loc[by_zone["zone"] == zone, "kh_mD_m_total"].iloc[0]
            assert actual == pytest.approx(expected)

    def test_by_well_kh_total_equals_sum_of_groups(self, master_synthetic):
        metrics = compute_all_zone_metrics(master_synthetic)
        by_well = field_summary_by_well(metrics)
        for well in by_well["well"]:
            expected = metrics.loc[metrics["well"] == well, "kh_mD_m"].sum()
            actual = by_well.loc[by_well["well"] == well, "kh_mD_m_total"].iloc[0]
            assert actual == pytest.approx(expected)

    def test_ntg_field_in_unit_interval(self, master_synthetic):
        metrics = compute_all_zone_metrics(master_synthetic)
        by_zone = field_summary_by_zone(metrics)
        assert ((by_zone["ntg_field"] >= 0) & (by_zone["ntg_field"] <= 1)).all()


# -----------------------------------------------------------------------------
# Input validation
# -----------------------------------------------------------------------------

class TestInputValidation:
    def test_missing_required_column_raises(self):
        bad = pd.DataFrame({"well": [1], "zone": ["A"], "depth": [2000.0]})
        with pytest.raises(ValueError, match="missing required columns"):
            compute_all_zone_metrics(bad)

    def test_unassigned_zone_rows_dropped_by_default(self, master_synthetic):
        # Inject a row with NaN zone (simulating the joiner's 7 sentinel rows)
        sentinel = master_synthetic.iloc[:1].copy()
        sentinel["zone"] = np.nan
        with_sentinel = pd.concat([sentinel, master_synthetic], ignore_index=True)
        metrics = compute_all_zone_metrics(with_sentinel)
        # If sentinel had not been dropped, we'd get extra rows
        assert metrics["zone"].notna().all()
