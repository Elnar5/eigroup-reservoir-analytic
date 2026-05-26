"""
Tests for src.data.quality.

Covers all six public functions:
  - per_well_inventory
  - missing_value_table
  - range_validity_table
  - perm_saturation_check
  - build_quality_report
  - render_report_to_markdown

We synthesize tiny DataFrames in-test so no external data dependency.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.data.quality import (
    LOG_COLUMNS,
    build_quality_report,
    missing_value_table,
    per_well_inventory,
    perm_saturation_check,
    range_validity_table,
    render_report_to_markdown,
)


# -----------------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------------

@pytest.fixture
def clean_logs() -> pd.DataFrame:
    """Two wells, uniform 0.2 m step, clean data."""
    depths_w1 = np.arange(1000.0, 1010.0, 0.2)   # 50 samples
    depths_w2 = np.arange(2000.0, 2005.0, 0.2)   # 25 samples
    n1, n2 = len(depths_w1), len(depths_w2)

    return pd.DataFrame({
        "well":  [1] * n1 + [2] * n2,
        "depth": np.concatenate([depths_w1, depths_w2]),
        "vsh":   np.concatenate([np.linspace(0.1, 0.5, n1), np.linspace(0.2, 0.6, n2)]),
        "phit":  np.concatenate([np.linspace(0.10, 0.25, n1), np.linspace(0.08, 0.22, n2)]),
        "sw":    np.concatenate([np.linspace(0.3, 0.8, n1), np.linspace(0.4, 0.7, n2)]),
        "perm":  np.concatenate([np.linspace(50, 500, n1), np.linspace(100, 1000, n2)]),
    })


@pytest.fixture
def logs_with_nan() -> pd.DataFrame:
    """Logs with intentional NaN values for testing missing_value_table."""
    return pd.DataFrame({
        "well":  [1, 1, 1, 1, 2, 2, 2, 2],
        "depth": [1000.0, 1000.2, 1000.4, 1000.6, 2000.0, 2000.2, 2000.4, 2000.6],
        "vsh":   [0.2, np.nan, 0.3, 0.4, 0.5, 0.4, np.nan, np.nan],
        "phit":  [0.15, 0.18, 0.20, np.nan, 0.10, 0.12, 0.15, 0.20],
        "sw":    [0.5, 0.6, 0.5, 0.4, 0.7, 0.8, 0.6, 0.5],
        "perm":  [100, 200, 150, 300, 500, 400, 250, 100],
    })


@pytest.fixture
def logs_with_saturation() -> pd.DataFrame:
    """Logs containing perm values at and above 14999 mD."""
    return pd.DataFrame({
        "well":  [1, 1, 1, 1, 1, 2, 2, 2, 2, 2],
        "depth": [1000.0, 1000.2, 1000.4, 1000.6, 1000.8,
                  2000.0, 2000.2, 2000.4, 2000.6, 2000.8],
        "vsh":   [0.2] * 10,
        "phit":  [0.2] * 10,
        "sw":    [0.5] * 10,
        # well 1: 2 saturated (15000), 3 normal
        # well 2: 0 saturated, 5 normal
        "perm":  [15000, 14999, 200, 300, 400, 100, 200, 300, 400, 500],
    })


@pytest.fixture
def logs_with_step_anomaly() -> pd.DataFrame:
    """Two wells: well_1 uniform 0.2m, well_5 uniform 0.5m (mirrors real data)."""
    depths_w1 = np.arange(1000.0, 1004.0, 0.2)   # 0.2 step
    depths_w5 = np.arange(2000.0, 2010.0, 0.5)   # 0.5 step
    n1, n5 = len(depths_w1), len(depths_w5)

    return pd.DataFrame({
        "well":  [1] * n1 + [5] * n5,
        "depth": np.concatenate([depths_w1, depths_w5]),
        "vsh":   [0.3] * (n1 + n5),
        "phit":  [0.2] * (n1 + n5),
        "sw":    [0.5] * (n1 + n5),
        "perm":  [100] * (n1 + n5),
    })


@pytest.fixture
def zones_df() -> pd.DataFrame:
    """Simple zones table for build_quality_report tests."""
    return pd.DataFrame({
        "well":  [1, 1, 2, 2],
        "depth": [1000.0, 1005.0, 2000.0, 2003.0],
        "name":  ["A", "B", "A", "B"],
    })


@pytest.fixture
def valid_ranges() -> dict:
    """Default valid ranges from data_dictionary.md."""
    return {
        "vsh":  {"min": 0.0,   "max": 1.0},
        "phit": {"min": 0.0,   "max": 0.5},
        "sw":   {"min": 0.0,   "max": 1.0},
        "perm": {"min": 0.001, "max": 15000.0},
    }


# -----------------------------------------------------------------------------
# Tests — per_well_inventory (3 tests)
# -----------------------------------------------------------------------------

class TestPerWellInventory:

    def test_inventory_one_row_per_well(self, clean_logs):
        """Inventory yields exactly one row per unique well."""
        inv = per_well_inventory(clean_logs)
        assert len(inv) == clean_logs.well.nunique()
        assert set(inv["well"].tolist()) == {1, 2}

    def test_inventory_step_mode_correct_uniform(self, clean_logs):
        """For uniform 0.2 m sampling, step_mode equals 0.2 and irregular=0."""
        inv = per_well_inventory(clean_logs)
        for _, row in inv.iterrows():
            assert row["step_mode"] == pytest.approx(0.2, abs=1e-6)
            assert row["irregular_steps"] == 0

    def test_inventory_detects_mixed_step(self, logs_with_step_anomaly):
        """When well_5 uses 0.5 m and well_1 uses 0.2 m, each step_mode reflects its own."""
        inv = per_well_inventory(logs_with_step_anomaly)
        w1 = inv[inv["well"] == 1].iloc[0]
        w5 = inv[inv["well"] == 5].iloc[0]
        assert w1["step_mode"] == pytest.approx(0.2, abs=1e-6)
        assert w5["step_mode"] == pytest.approx(0.5, abs=1e-6)


# -----------------------------------------------------------------------------
# Tests — missing_value_table (3 tests)
# -----------------------------------------------------------------------------

class TestMissingValueTable:

    def test_missing_counts_match_actual_nans(self, logs_with_nan):
        """Hand-checked: well 1 vsh=1 NaN, well 1 phit=1 NaN, well 2 vsh=2 NaN."""
        mv = missing_value_table(logs_with_nan)
        w1_vsh = mv[(mv["well"] == 1) & (mv["column"] == "vsh")].iloc[0]
        w1_phit = mv[(mv["well"] == 1) & (mv["column"] == "phit")].iloc[0]
        w2_vsh = mv[(mv["well"] == 2) & (mv["column"] == "vsh")].iloc[0]
        assert w1_vsh["n_missing"] == 1
        assert w1_phit["n_missing"] == 1
        assert w2_vsh["n_missing"] == 2

    def test_missing_returns_long_form_with_expected_columns(self, clean_logs):
        """Output is long-form: well × column rows, 4 columns."""
        mv = missing_value_table(clean_logs)
        # 2 wells × 4 columns = 8 rows
        assert len(mv) == 2 * len(LOG_COLUMNS)
        expected_cols = {"well", "column", "n_missing", "fraction_missing"}
        assert expected_cols.issubset(set(mv.columns))

    def test_missing_fraction_in_unit_interval(self, logs_with_nan):
        """Fraction is always between 0 and 1."""
        mv = missing_value_table(logs_with_nan)
        assert (mv["fraction_missing"] >= 0).all()
        assert (mv["fraction_missing"] <= 1).all()


# -----------------------------------------------------------------------------
# Tests — range_validity_table (3 tests)
# -----------------------------------------------------------------------------

class TestRangeValidityTable:

    def test_range_no_violations_for_clean_data(self, clean_logs, valid_ranges):
        """Clean fixture data is fully within valid ranges → zero violations."""
        rv = range_validity_table(clean_logs, valid_ranges)
        assert (rv["below_min"] == 0).all()
        assert (rv["above_max"] == 0).all()
        assert (rv["total_out_of_range"] == 0).all()

    def test_range_detects_below_min(self, valid_ranges):
        """Inject a negative vsh sample → below_min counts it."""
        bad_logs = pd.DataFrame({
            "well":  [1, 1, 1],
            "depth": [1000.0, 1000.2, 1000.4],
            "vsh":   [-0.5, 0.3, 0.4],   # one below 0
            "phit":  [0.2, 0.2, 0.2],
            "sw":    [0.5, 0.5, 0.5],
            "perm":  [100, 200, 300],
        })
        rv = range_validity_table(bad_logs, valid_ranges)
        vsh_row = rv[rv["column"] == "vsh"].iloc[0]
        assert vsh_row["below_min"] == 1
        assert vsh_row["above_max"] == 0

    def test_range_detects_above_max(self, valid_ranges):
        """Inject perm above 15000 → above_max counts it."""
        bad_logs = pd.DataFrame({
            "well":  [1, 1, 1],
            "depth": [1000.0, 1000.2, 1000.4],
            "vsh":   [0.3, 0.3, 0.3],
            "phit":  [0.2, 0.2, 0.2],
            "sw":    [0.5, 0.5, 0.5],
            "perm":  [16000.0, 200, 300],   # one above 15000
        })
        rv = range_validity_table(bad_logs, valid_ranges)
        perm_row = rv[rv["column"] == "perm"].iloc[0]
        assert perm_row["above_max"] == 1
        assert perm_row["below_min"] == 0


# -----------------------------------------------------------------------------
# Tests — perm_saturation_check (2 tests)
# -----------------------------------------------------------------------------

class TestPermSaturationCheck:

    def test_saturation_count_correct(self, logs_with_saturation):
        """well 1 has 2 saturated (15000, 14999), well 2 has 0."""
        sat = perm_saturation_check(logs_with_saturation)
        w1 = sat[sat["well"] == 1].iloc[0]
        w2 = sat[sat["well"] == 2].iloc[0]
        assert w1["n_perm_saturated"] == 2     # 15000 and 14999 both >= 14999
        assert w2["n_perm_saturated"] == 0

    def test_saturation_threshold_boundary(self, logs_with_saturation):
        """Default threshold is 14999.0 — exactly 14999 IS counted as saturated."""
        sat = perm_saturation_check(logs_with_saturation, sat_threshold=14999.0)
        w1 = sat[sat["well"] == 1].iloc[0]
        # well 1 perm = [15000, 14999, 200, 300, 400] → 2 at-or-above 14999
        assert w1["n_perm_saturated"] == 2
        # Now bump threshold above any sample
        sat_strict = perm_saturation_check(logs_with_saturation, sat_threshold=15001.0)
        assert (sat_strict["n_perm_saturated"] == 0).all()


# -----------------------------------------------------------------------------
# Tests — build_quality_report (2 tests)
# -----------------------------------------------------------------------------

class TestBuildQualityReport:

    def test_report_dict_has_all_keys(self, clean_logs, zones_df, valid_ranges):
        """Report dict must contain summary + four DataFrame sections."""
        report = build_quality_report(clean_logs, zones_df, valid_ranges)
        expected_keys = {"summary", "inventory", "missing_values",
                         "range_validity", "perm_saturation"}
        assert expected_keys.issubset(set(report.keys()))

    def test_report_summary_matches_inputs(self, clean_logs, zones_df, valid_ranges):
        """Summary reflects the input counts."""
        report = build_quality_report(clean_logs, zones_df, valid_ranges)
        s = report["summary"]
        assert s["n_wells"] == clean_logs.well.nunique()
        assert s["n_samples_total"] == len(clean_logs)
        assert s["n_zones_defined"] == len(zones_df)
        assert set(s["unique_zone_names"]) == set(zones_df["name"].unique())


# -----------------------------------------------------------------------------
# Tests — render_report_to_markdown (2 tests)
# -----------------------------------------------------------------------------

class TestRenderReportToMarkdown:

    def test_markdown_file_created(self, clean_logs, zones_df, valid_ranges, tmp_path):
        """render writes a markdown file at the requested path."""
        report = build_quality_report(clean_logs, zones_df, valid_ranges)
        out = tmp_path / "report.md"
        result_path = render_report_to_markdown(report, out)
        assert result_path.exists()
        assert result_path.is_file()
        assert result_path.suffix == ".md"

    def test_markdown_contains_all_sections(
        self, clean_logs, zones_df, valid_ranges, tmp_path
    ):
        """Rendered markdown contains every required section header — including Join Strategy."""
        report = build_quality_report(clean_logs, zones_df, valid_ranges)
        out = tmp_path / "report.md"
        render_report_to_markdown(report, out)
        text = out.read_text()
        # Standard QC sections
        assert "# Data Quality Report (Part A)" in text
        assert "## Summary" in text
        assert "## Per-Well Inventory" in text
        assert "## Missing Values" in text
        assert "## Range Validity" in text
        assert "## Permeability Saturation Check" in text
        # New Join Strategy section
        assert "## Join Strategy" in text
        assert "merge_asof" in text
        assert "snap" in text.lower()
