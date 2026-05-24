"""Tests for src.data.joiner — zone assignment and dz computation."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.data.joiner import assign_zones, build_master_table, compute_dz


@pytest.fixture
def simple_logs() -> pd.DataFrame:
    """Two wells, 5 samples each at 0.2 m step."""
    return pd.DataFrame({
        "well":  [1, 1, 1, 1, 1, 2, 2, 2, 2, 2],
        "depth": [1000.0, 1000.2, 1000.4, 1000.6, 1000.8,
                  2000.0, 2000.2, 2000.4, 2000.6, 2000.8],
        "vsh":   [0.1] * 10,
        "phit":  [0.2] * 10,
        "sw":    [0.5] * 10,
        "perm":  [100.0] * 10,
    })


@pytest.fixture
def simple_zones() -> pd.DataFrame:
    return pd.DataFrame({
        "well":  [1, 1, 2, 2],
        "depth": [1000.0, 1000.4, 2000.0, 2000.6],
        "name":  ["A", "B", "X", "Y"],
    })


def test_assign_zones_basic(simple_logs: pd.DataFrame, simple_zones: pd.DataFrame) -> None:
    out = assign_zones(simple_logs, simple_zones)
    out_well_1 = out[out.well == 1].sort_values("depth").reset_index(drop=True)
    # Samples at 1000.0 and 1000.2 should be in zone A; 1000.4 onwards in B
    assert out_well_1.loc[0, "zone"] == "A"
    assert out_well_1.loc[1, "zone"] == "A"
    assert out_well_1.loc[2, "zone"] == "B"
    assert out_well_1.loc[3, "zone"] == "B"
    assert out_well_1.loc[4, "zone"] == "B"


def test_assign_zones_well_isolation(simple_logs: pd.DataFrame, simple_zones: pd.DataFrame) -> None:
    """A zone defined in well 1 must not leak into well 2."""
    out = assign_zones(simple_logs, simple_zones)
    well_1_zones = set(out[out.well == 1].zone.dropna().unique())
    well_2_zones = set(out[out.well == 2].zone.dropna().unique())
    assert well_1_zones == {"A", "B"}
    assert well_2_zones == {"X", "Y"}


def test_assign_zones_above_first_top_is_nan() -> None:
    logs = pd.DataFrame({
        "well": [1, 1, 1],
        "depth": [900.0, 1000.0, 1010.0],  # 900 is shallower than first zone top 1000
        "vsh": [0.1, 0.1, 0.1], "phit": [0.2, 0.2, 0.2],
        "sw": [0.5, 0.5, 0.5], "perm": [100.0, 100.0, 100.0],
    })
    zones = pd.DataFrame({"well": [1], "depth": [1000.0], "name": ["A"]})
    out = assign_zones(logs, zones)
    assert pd.isna(out.iloc[0]["zone"])
    assert out.iloc[1]["zone"] == "A"


def test_compute_dz_per_well(simple_logs: pd.DataFrame) -> None:
    out = compute_dz(simple_logs)
    assert "dz" in out.columns
    # All dz should be 0.2 since sampling is uniform
    assert np.allclose(out.dz.values, 0.2)


def test_compute_dz_last_row_repeats_prior() -> None:
    logs = pd.DataFrame({
        "well": [1, 1, 1],
        "depth": [1000.0, 1000.5, 1000.7],   # steps: 0.5, 0.2
        "vsh": [0.1, 0.1, 0.1], "phit": [0.2, 0.2, 0.2],
        "sw": [0.5, 0.5, 0.5], "perm": [100.0, 100.0, 100.0],
    })
    out = compute_dz(logs)
    # dz: [0.5, 0.2, 0.2]  — the last value repeats the prior step
    assert np.isclose(out.dz.iloc[0], 0.5)
    assert np.isclose(out.dz.iloc[1], 0.2)
    assert np.isclose(out.dz.iloc[2], 0.2)


def test_build_master_table_pipeline(simple_logs: pd.DataFrame, simple_zones: pd.DataFrame) -> None:
    master = build_master_table(simple_logs, simple_zones)
    expected_cols = {"well", "depth", "vsh", "phit", "sw", "perm", "zone", "dz"}
    assert expected_cols.issubset(set(master.columns))
    assert len(master) == len(simple_logs)
