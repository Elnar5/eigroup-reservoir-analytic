"""
Data quality reporting (Part A).

Produces a structured report covering:
  - Inventory: per-well row counts, depth ranges, sampling step
  - Missing values: count and fraction, per column per well
  - Range validity: samples outside data_dictionary.md valid ranges
  - Sampling regularity: deviations from the expected uniform step

The report is returned as a dict (machine-readable) and can be rendered to
markdown for the deliverable.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from loguru import logger

LOG_COLUMNS = ("vsh", "phit", "sw", "perm")


def per_well_inventory(logs: pd.DataFrame) -> pd.DataFrame:
    """
    One-row-per-well summary: n_rows, depth_min, depth_max, gross_thickness,
    sampling_step_mode, sampling_step_min, sampling_step_max.

    The "sampling step" is the difference between consecutive depths. We report
    the mode (typical step), min, and max to flag any irregular intervals.
    """
    rows = []
    for well_id, g in logs.groupby("well", sort=True):
        depths = g.depth.values
        if len(depths) < 2:
            rows.append({
                "well": int(well_id),
                "n_rows": int(len(g)),
                "depth_min": float(depths[0]) if len(depths) else np.nan,
                "depth_max": float(depths[-1]) if len(depths) else np.nan,
                "gross_thickness": np.nan,
                "step_mode": np.nan,
                "step_min": np.nan,
                "step_max": np.nan,
                "irregular_steps": 0,
            })
            continue

        steps = np.diff(depths)
        # Mode via rounding (avoid floating-point hash issues)
        steps_rounded = np.round(steps, 4)
        unique, counts = np.unique(steps_rounded, return_counts=True)
        step_mode = float(unique[counts.argmax()])

        # Count steps that deviate from the mode by > 1% (numerically irregular)
        irregular_mask = np.abs(steps - step_mode) > 0.01 * step_mode
        irregular_count = int(irregular_mask.sum())

        rows.append({
            "well": int(well_id),
            "n_rows": int(len(g)),
            "depth_min": float(depths.min()),
            "depth_max": float(depths.max()),
            "gross_thickness": float(depths.max() - depths.min()),
            "step_mode": step_mode,
            "step_min": float(steps.min()),
            "step_max": float(steps.max()),
            "irregular_steps": irregular_count,
        })
    return pd.DataFrame(rows)


def missing_value_table(logs: pd.DataFrame) -> pd.DataFrame:
    """
    Per-well, per-column count and fraction of missing values.
    Returns a long-form frame: (well, column, n_missing, fraction_missing).
    """
    rows = []
    for well_id, g in logs.groupby("well", sort=True):
        n = len(g)
        for col in LOG_COLUMNS:
            n_missing = int(g[col].isna().sum())
            rows.append({
                "well": int(well_id),
                "column": col,
                "n_missing": n_missing,
                "fraction_missing": n_missing / n if n else np.nan,
            })
    return pd.DataFrame(rows)


def range_validity_table(
    logs: pd.DataFrame,
    valid_ranges: Mapping[str, Mapping[str, float]],
) -> pd.DataFrame:
    """
    Count samples falling outside the valid range for each (well, column).

    Parameters
    ----------
    valid_ranges
        e.g. {"vsh": {"min": 0.0, "max": 1.0}, "perm": {"min": 0.001, "max": 15000.0}, ...}
    """
    rows = []
    for well_id, g in logs.groupby("well", sort=True):
        for col in LOG_COLUMNS:
            if col not in valid_ranges:
                continue
            lo = valid_ranges[col]["min"]
            hi = valid_ranges[col]["max"]
            vals = g[col].dropna()
            below = int((vals < lo).sum())
            above = int((vals > hi).sum())
            rows.append({
                "well": int(well_id),
                "column": col,
                "valid_min": lo,
                "valid_max": hi,
                "below_min": below,
                "above_max": above,
                "total_out_of_range": below + above,
            })
    return pd.DataFrame(rows)


def perm_saturation_check(logs: pd.DataFrame, sat_threshold: float = 14999.0) -> pd.DataFrame:
    """
    Flag wells where perm appears saturated at the upper bound (≈15000 mD).

    A high fraction of saturated samples suggests the measurement was capped
    by the tool's dynamic range. Treating these as true 15000 mD inflates kh.
    Worth surfacing in the QC report.
    """
    rows = []
    for well_id, g in logs.groupby("well", sort=True):
        perm = g.perm.dropna()
        n_sat = int((perm >= sat_threshold).sum())
        rows.append({
            "well": int(well_id),
            "n_samples": len(perm),
            "n_perm_saturated": n_sat,
            "fraction_saturated": n_sat / len(perm) if len(perm) else np.nan,
        })
    return pd.DataFrame(rows)


def build_quality_report(
    logs: pd.DataFrame,
    zones: pd.DataFrame,
    valid_ranges: Mapping[str, Mapping[str, float]],
) -> dict[str, Any]:
    """
    Assemble the full Part A quality report.

    Returns a dict with sub-frames; each value is either a DataFrame (for tabular
    sections) or a scalar/dict (for top-level summary).
    """
    inventory = per_well_inventory(logs)
    missing = missing_value_table(logs)
    ranges = range_validity_table(logs, valid_ranges)
    perm_sat = perm_saturation_check(logs)

    summary = {
        "n_wells": int(logs.well.nunique()),
        "n_samples_total": int(len(logs)),
        "n_zones_defined": int(len(zones)),
        "unique_zone_names": sorted(zones.name.unique().tolist()),
        "depth_range_field": (float(logs.depth.min()), float(logs.depth.max())),
    }

    logger.info(f"Quality report summary: {summary}")
    return {
        "summary": summary,
        "inventory": inventory,
        "missing_values": missing,
        "range_validity": ranges,
        "perm_saturation": perm_sat,
    }


def _inv_for_markdown(inv: pd.DataFrame) -> pd.DataFrame:
    """Cast integer-valued columns to strings so to_markdown doesn't pad them with .00"""
    out = inv.copy()
    for col in ("well", "n_rows", "irregular_steps"):
        if col in out.columns:
            out[col] = out[col].astype(int).astype(str)
    return out


def _missing_for_markdown(mv: pd.DataFrame) -> pd.DataFrame:
    out = mv.copy()
    for col in ("well", "n_missing"):
        out[col] = out[col].astype(int).astype(str)
    return out


def _ranges_for_markdown(rv: pd.DataFrame) -> pd.DataFrame:
    out = rv.copy()
    for col in ("well", "below_min", "above_max", "total_out_of_range"):
        out[col] = out[col].astype(int).astype(str)
    return out


def _sat_for_markdown(sat: pd.DataFrame) -> pd.DataFrame:
    out = sat.copy()
    for col in ("well", "n_samples", "n_perm_saturated"):
        out[col] = out[col].astype(int).astype(str)
    return out


def render_report_to_markdown(report: dict[str, Any], output_path: Path) -> Path:
    """
    Render the quality report dict to a markdown file. Returns the written path.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    s = report["summary"]
    lines: list[str] = [
        "# Data Quality Report (Part A)",
        "",
        "## Summary",
        "",
        f"- **Total wells:** {s['n_wells']}",
        f"- **Total depth samples:** {s['n_samples_total']:,}",
        f"- **Zone tops defined:** {s['n_zones_defined']}",
        f"- **Unique zone names:** {', '.join(s['unique_zone_names'])}",
        f"- **Field depth range:** {s['depth_range_field'][0]:.2f} – {s['depth_range_field'][1]:.2f} m",
        "",
        "## Per-Well Inventory",
        "",
        _inv_for_markdown(report["inventory"]).to_markdown(index=False, floatfmt=".4f"),
        "",
        "## Missing Values",
        "",
        _missing_for_markdown(report["missing_values"]).to_markdown(index=False, floatfmt=".4f"),
        "",
        "## Range Validity (samples outside data_dictionary ranges)",
        "",
        _ranges_for_markdown(report["range_validity"]).to_markdown(index=False, floatfmt=".4f"),
        "",
        "## Permeability Saturation Check",
        "",
        "Samples where perm ≥ 14999 mD are likely capped at the tool's upper",
        "dynamic-range limit. A high saturation fraction inflates downstream kh",
        "estimates and should be surfaced before any volumetric ranking.",
        "",
        _sat_for_markdown(report["perm_saturation"]).to_markdown(index=False, floatfmt=".4f"),
        "",
    ]
    output_path.write_text("\n".join(lines), encoding="utf-8")
    logger.info(f"Wrote quality report to {output_path}")
    return output_path
