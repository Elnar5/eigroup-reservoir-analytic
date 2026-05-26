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
        "## Join Strategy",
        "",
        "**Combining the well logs with `zones.csv` to produce the master table.**",
        "",
        "### The problem",
        "",
        "Two independent data sources must be combined:",
        "",
        "- **Well logs** (`well_<id>.csv`): one row per depth sample, "
        "five measurements (vsh, phit, sw, perm) per row. No zone label.",
        "- **Zone tops** (`zones.csv`): 35 rows recording only the depth at which "
        "each zone *begins* in each well, not the interval.",
        "",
        "The data dictionary specifies that each zone extends from its listed "
        "depth down to the top of the next zone in the same well (or to the "
        "bottom of the log for the last zone). Every depth sample must be "
        "assigned the zone it belongs to.",
        "",
        "### Why an equality join does not work",
        "",
        "Log sample depths form a regular grid (1850.00, 1850.20, 1850.40, ...) "
        "while zone-top depths are irregular (1850.07, 1925.00, ...). These "
        "values never coincide, so a standard `INNER JOIN ON depth` would "
        "return zero rows.",
        "",
        "What is needed is an **inequality join**: for each log sample, find "
        "the zone top whose depth is closest *at-or-below* the sample, "
        "within the same well.",
        "",
        "### Chosen approach — `pandas.merge_asof`",
        "",
        "```python",
        "merged = pd.merge_asof(",
        '    left=logs_sorted,',
        '    right=zones_sorted,',
        '    on="depth",',
        '    by="well",',
        '    direction="backward",',
        ")",
        "```",
        "",
        "| Parameter | Value | Why |",
        "|---|---|---|",
        '| `on` | `"depth"` | The inequality key — depth comparison drives the match. |',
        '| `by` | `"well"` | Match scope. Each sample is matched only against zone tops in the **same** well; the search never crosses well boundaries. |',
        '| `direction` | `"backward"` | For each sample, pick the largest zone-top depth ≤ the sample depth — the most recent zone that has already begun. |',
        "",
        "**Why `backward`, not `forward` or `nearest`.** For a sample at depth "
        "1900 m in well_1, where zones A and B begin at 1850 and 1925:",
        "",
        "- `backward` returns Zone A (1850 ≤ 1900) — correct: A is the most recent to have begun.",
        "- `forward` returns Zone B (1925 ≥ 1900) — wrong: B has not begun yet.",
        "- `nearest` returns Zone B (closer in distance) — wrong: proximity is not the geological criterion.",
        "",
        "Only `backward` matches the data dictionary's interval definition.",
        "",
        "**Performance.** On 18,167 samples × 35 zone tops, `merge_asof` "
        "performs roughly 93 K operations versus 636 K for a nested loop — "
        "and runs the inner loop in pandas' C extension. End-to-end join "
        "time is about 50 ms.",
        "",
        "### Spec-compliance fix — the snap step",
        "",
        "A literal `merge_asof` on the raw data leaves 7 samples unassigned. "
        "In every one of the 7 wells, the log starts a few centimetres "
        "**above** the first listed zone top:",
        "",
        "| Well | Log start | First zone top | Gap |",
        "|---|---|---|---|",
        "| 1 | 1850.00 | 1850.07 | 0.07 m |",
        "| 2 | 2010.00 | 2010.03 | 0.03 m |",
        "| 3 | 1920.00 | 1920.01 | 0.01 m |",
        "| 4 | 2100.00 | 2100.06 | 0.06 m |",
        "| 5 | 1970.00 | 1970.01 | 0.01 m |",
        "| 6 | 1800.00 | 1800.07 | 0.07 m |",
        "| 7 | 2050.00 | 2050.04 | 0.04 m |",
        "",
        "Without correction, each well's first sample would receive "
        "`zone = NaN` — a direct spec violation.",
        "",
        "**The fix.** Before merging, each well's earliest zone top is moved "
        "up to that well's first log depth. Maximum snap distance is 7 cm — "
        "well below the 20 cm sampling resolution, so no calculated metric "
        "changes. The raw CSVs are never modified; snapping happens on a "
        "copy of the zones DataFrame inside `assign_zones`.",
        "",
        "Post-snap, zone assignment is **100% complete** — zero NaN zones.",
        "",
        "### Per-sample thickness `dz`",
        "",
        "After zone assignment, each sample needs a thickness `dz` so kh "
        "(= sum of perm·dz) can be computed. The data dictionary defines:",
        "",
        "```",
        "dz[i]    = depth[i+1] - depth[i]   # forward difference",
        "dz[last] = dz[last-1]              # repeat the last step",
        "```",
        "",
        "This is computed **per well**, not globally, because sampling "
        "steps differ. Well_5 uses 0.5 m; the other six wells use 0.2 m. "
        "A global `np.diff` on the concatenated table would produce "
        "nonsense at well boundaries (e.g. well_4 ends at 2750 m, "
        "well_5 starts at 1970 m, giving a boundary 'thickness' of −780 m).",
        "",
        "### Summary",
        "",
        "| Step | Tool | Purpose |",
        "|---|---|---|",
        "| 1. Load 7 well CSVs | `loader.load_all_wells` | One row per depth sample |",
        "| 2. Load zones.csv | `loader.load_zones` | Zone tops, 35 rows |",
        "| 3. Snap earliest zone tops | `joiner.assign_zones` | Spec compliance — 7 cm max correction |",
        "| 4. Sort both frames by depth | (within `assign_zones`) | `merge_asof` precondition |",
        "| 5. `merge_asof` inequality join | `joiner.assign_zones` | Assigns `zone` column |",
        "| 6. Compute per-well `dz` | `joiner.compute_dz` | Per-sample thickness for kh |",
        "| 7. Cache as Parquet | `cli.quality_cmd` | Single source of truth for Parts B/C/D |",
        "",
        "The resulting master table — 18,167 rows with columns "
        "(well, depth, vsh, phit, sw, perm, zone, dz) — is cached as "
        "`data/processed/master_table.parquet` and serves as the single "
        "source of truth for every downstream deliverable.",
        "",
    ]
    output_path.write_text("\n".join(lines), encoding="utf-8")
    logger.info(f"Wrote quality report to {output_path}")
    return output_path