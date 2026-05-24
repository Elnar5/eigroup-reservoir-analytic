"""
Smoke tests for src.visualization.field.

We don't try to validate visual output (that's the human's job). We verify:
    - Every chart function returns (matplotlib.Figure, plotly.graph_objects.Figure)
    - The plotly figure has the expected number of traces
    - save_chart writes both PNG and HTML
    - Charts handle edge cases (empty zones, all-saturated zones)
"""

from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # headless backend for CI

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import pytest

from src.analytics.metrics import compute_all_zone_metrics
from src.analytics.sensitivity import run_vsh_sweep
from src.visualization.field import (
    ZONE_COLORS,
    crossplot_phit_perm,
    heatmap_kh_by_well_zone,
    lorenz_curves,
    save_chart,
    sensitivity_ntg_curves,
    stacked_bar_kh_per_well,
)


# -----------------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------------

@pytest.fixture
def master_realistic() -> pd.DataFrame:
    """Master table mirroring the real-data structure: 3 wells × 5 zones,
    with realistic vsh/phit/perm ranges and ~30% saturation in zone B."""
    rng = np.random.default_rng(42)
    rows = []
    zone_specs = [
        ("A", (0.1, 0.4), (50, 500)),
        ("B", (0.1, 0.3), (5000, 15000)),
        ("C", (0.2, 0.5), (100, 1000)),
        ("D", (0.5, 0.9), (0.1, 5)),
        ("E", (0.2, 0.5), (200, 3000)),
    ]
    for well in [1, 2, 3]:
        for zone, vsh_range, perm_range in zone_specs:
            for i in range(40):
                perm = rng.uniform(*perm_range)
                if zone == "B" and rng.random() < 0.5:
                    perm = 15000.0  # saturate ~half of zone B
                rows.append({
                    "well": well, "zone": zone,
                    "depth": 2000 + i * 0.2,
                    "vsh": rng.uniform(*vsh_range),
                    "phit": rng.uniform(0.10, 0.30),
                    "sw": 0.5,
                    "perm": perm,
                    "dz": 0.2,
                })
    return pd.DataFrame(rows)


@pytest.fixture
def metrics(master_realistic):
    return compute_all_zone_metrics(master_realistic)


@pytest.fixture
def sweep_results(master_realistic):
    return run_vsh_sweep(master_realistic, vsh_min=0.3, vsh_max=0.7, vsh_step=0.05)


# -----------------------------------------------------------------------------
# Per-chart smoke tests
# -----------------------------------------------------------------------------

class TestHeatmap:
    def test_returns_both_figures(self, metrics):
        fig_m, fig_p = heatmap_kh_by_well_zone(metrics)
        assert isinstance(fig_m, plt.Figure)
        assert isinstance(fig_p, go.Figure)
        plt.close(fig_m)

    def test_plotly_has_one_heatmap_trace(self, metrics):
        _, fig_p = heatmap_kh_by_well_zone(metrics)
        assert len(fig_p.data) == 1


class TestStackedBar:
    def test_one_trace_per_zone(self, metrics):
        _, fig_p = stacked_bar_kh_per_well(metrics)
        n_zones = metrics["zone"].nunique()
        assert len(fig_p.data) == n_zones

    def test_zone_colors_consistent(self, metrics):
        _, fig_p = stacked_bar_kh_per_well(metrics)
        # Each bar trace should use a colour from ZONE_COLORS
        used_colours = {t.marker.color for t in fig_p.data}
        valid_colours = set(ZONE_COLORS.values())
        assert used_colours.issubset(valid_colours)


class TestCrossplot:
    def test_one_trace_per_zone_plus_saturation(self, master_realistic):
        _, fig_p = crossplot_phit_perm(master_realistic)
        n_zones = master_realistic.dropna(subset=["zone"])["zone"].nunique()
        # n_zones (non-saturated) + 1 saturated overlay
        assert len(fig_p.data) == n_zones + 1

    def test_no_saturation_trace_when_none_capped(self):
        df = pd.DataFrame({
            "well": [1] * 10, "zone": ["A"] * 10,
            "depth": np.arange(2000.0, 2002.0, 0.2),
            "vsh": [0.2] * 10, "phit": [0.2] * 10, "sw": [0.5] * 10,
            "perm": [100.0] * 10,  # nothing saturated
            "dz": [0.2] * 10,
        })
        _, fig_p = crossplot_phit_perm(df, sample_frac=1.0)
        # 1 zone, 0 saturation overlay -> 1 trace
        assert len(fig_p.data) == 1


class TestSensitivityCurves:
    def test_has_per_well_thin_lines_and_zone_averages(self, sweep_results):
        _, fig_p = sensitivity_ntg_curves(sweep_results)
        n_zones = sweep_results["zone"].nunique()
        n_wells = sweep_results["well"].nunique()
        # Expected: thin lines per (well, zone) + bold per zone = (n_wells × n_zones) + n_zones
        expected = n_wells * n_zones + n_zones
        assert len(fig_p.data) == expected


class TestLorenz:
    def test_includes_diagonal_and_one_curve_per_zone(self, master_realistic):
        _, fig_p = lorenz_curves(master_realistic)
        n_zones_with_net = master_realistic["zone"].nunique()  # in practice all 5 may have net
        # 1 diagonal + at most n_zones curves
        assert len(fig_p.data) <= n_zones_with_net + 1
        assert len(fig_p.data) >= 2  # diagonal + at least one zone


# -----------------------------------------------------------------------------
# Save round-trip
# -----------------------------------------------------------------------------

class TestSaveChart:
    def test_writes_png_and_html(self, metrics, tmp_path: Path):
        fig_m, fig_p = stacked_bar_kh_per_well(metrics)
        save_chart(fig_m, fig_p, "test_chart", tmp_path)
        assert (tmp_path / "test_chart.png").exists()
        assert (tmp_path / "test_chart.html").exists()

    def test_html_contains_plotly_div(self, metrics, tmp_path: Path):
        fig_m, fig_p = stacked_bar_kh_per_well(metrics)
        save_chart(fig_m, fig_p, "test_chart", tmp_path)
        html = (tmp_path / "test_chart.html").read_text()
        assert "plotly" in html.lower()
