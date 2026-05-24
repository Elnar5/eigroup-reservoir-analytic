"""
Tests for src.data.loader.

We don't ship fixtures — instead we synthesize tiny CSVs in tmp_path so the
test suite has no external data dependency.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.data.loader import (
    discover_wells,
    load_all_wells,
    load_well,
    load_zones,
    validate_well_zone_consistency,
)


def _make_well_csv(path: Path, depths: list[float]) -> None:
    n = len(depths)
    df = pd.DataFrame({
        "depth": depths,
        "vsh":   np.linspace(0.1, 0.6, n),
        "phit":  np.linspace(0.05, 0.30, n),
        "sw":    np.linspace(0.3, 0.9, n),
        "perm":  np.logspace(0, 3, n),
    })
    df.to_csv(path, index=False)


def _make_zones_csv(path: Path) -> None:
    pd.DataFrame({
        "well": [1, 1, 2, 2],
        "depth": [1000.0, 1010.0, 2000.0, 2010.0],
        "name": ["A", "B", "A", "B"],
    }).to_csv(path, index=False)


@pytest.fixture
def raw_dir(tmp_path: Path) -> Path:
    d = tmp_path / "raw"
    d.mkdir()
    _make_well_csv(d / "well_1.csv", np.arange(1000.0, 1020.2, 0.2).tolist())
    _make_well_csv(d / "well_2.csv", np.arange(2000.0, 2020.2, 0.2).tolist())
    _make_zones_csv(d / "zones.csv")
    return d


def test_discover_wells_finds_all(raw_dir: Path) -> None:
    ids = discover_wells(raw_dir)
    assert ids == [1, 2]


def test_discover_wells_raises_on_empty_dir(tmp_path: Path) -> None:
    empty = tmp_path / "empty"
    empty.mkdir()
    with pytest.raises(FileNotFoundError):
        discover_wells(empty)


def test_load_well_returns_sorted(raw_dir: Path) -> None:
    df = load_well(1, raw_dir)
    assert list(df.columns)[0] == "well"
    assert df["well"].unique().tolist() == [1]
    assert df["depth"].is_monotonic_increasing


def test_load_well_dtype_coercion(tmp_path: Path) -> None:
    # CSV with a stray non-numeric — should coerce to NaN, not crash
    p = tmp_path / "well_99.csv"
    p.write_text("depth,vsh,phit,sw,perm\n1000.0,0.2,0.15,0.5,100.0\n1000.2,oops,0.16,0.5,120.0\n")
    df = load_well(99, tmp_path)
    assert df.loc[1, "vsh"] != df.loc[1, "vsh"]  # NaN check (NaN != NaN)


def test_load_well_missing_file(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_well(42, tmp_path)


def test_load_all_wells_concatenates(raw_dir: Path) -> None:
    df = load_all_wells(raw_dir)
    assert set(df.well.unique()) == {1, 2}
    # Each well had ~101 samples (1000-1020 step 0.2)
    assert len(df) > 200


def test_load_zones_schema(raw_dir: Path) -> None:
    z = load_zones(raw_dir)
    assert list(z.columns) == ["well", "depth", "name"]
    assert z.well.dtype.kind == "i"
    assert sorted(z.name.unique()) == ["A", "B"]


def test_validate_consistency_clean(raw_dir: Path) -> None:
    logs = load_all_wells(raw_dir)
    zones = load_zones(raw_dir)
    issues = validate_well_zone_consistency(logs, zones)
    assert issues["zone_without_log"] == []
    assert issues["log_without_zone"] == []


def test_validate_detects_zone_without_log(raw_dir: Path) -> None:
    logs = load_all_wells(raw_dir)
    # Add a phantom well 99 to zones only
    zones = load_zones(raw_dir)
    phantom = pd.DataFrame({"well": [99], "depth": [500.0], "name": ["A"]})
    zones = pd.concat([zones, phantom], ignore_index=True)
    issues = validate_well_zone_consistency(logs, zones)
    assert 99 in issues["zone_without_log"]
