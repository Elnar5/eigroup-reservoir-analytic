"""
Part C.1: vsh cutoff sensitivity sweep.

The question this module answers:
    How robust are our reservoir-volume estimates to the choice of vsh cutoff?

Why this matters:
    The 0.5 cutoff in the data_dictionary is a literature default, not a
    calibrated value. A field decision should never hinge on a single cutoff —
    we want to see how net_thickness, NTG, and kh behave as the cutoff slides
    across a plausible range. A "knee" in the curve flags zones where the
    answer is brittle; a flat curve flags zones where the cutoff doesn't matter.

What this module produces:
    1. `run_vsh_sweep`  → long-form frame: (well, zone, vsh_cutoff, all metrics)
    2. `bootstrap_kh_ci` → 90% confidence intervals on kh per (well, zone, cutoff)
    3. `detect_knee_points` → for each (well, zone), the cutoff where NTG falls
       most sharply (the "regime change" point)

Reuses src.analytics.metrics.compute_all_zone_metrics under the hood. Each
sweep step is a fresh metrics computation with vsh_max overridden.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from loguru import logger

from src.analytics.metrics import compute_all_zone_metrics


# -----------------------------------------------------------------------------
# Main sweep
# -----------------------------------------------------------------------------

def run_vsh_sweep(
    master: pd.DataFrame,
    vsh_min: float = 0.30,
    vsh_max: float = 0.70,
    vsh_step: float = 0.05,
    phit_fixed: float = 0.08,
) -> pd.DataFrame:
    """Sweep vsh cutoff across a range, recomputing all metrics each time.

    Parameters
    ----------
    master : DataFrame from joiner.build_master_table
    vsh_min, vsh_max, vsh_step : sweep grid
    phit_fixed : phit_min held constant across the sweep

    Returns
    -------
    Long-form DataFrame with one row per (well, zone, vsh_cutoff). All
    metrics columns from compute_all_zone_metrics are preserved.

    Notes
    -----
    Endpoint inclusion: we use np.arange + rounding to dodge floating-point
    drift (np.arange(0.3, 0.7, 0.05) would otherwise stop at 0.65 or include
    0.7000000001). Cutoffs are rounded to 2 decimals for clean output.
    """
    if vsh_min >= vsh_max:
        raise ValueError(f"vsh_min ({vsh_min}) must be < vsh_max ({vsh_max})")
    if vsh_step <= 0:
        raise ValueError(f"vsh_step must be positive, got {vsh_step}")

    # Build cutoff grid inclusive of both endpoints
    n_steps = int(round((vsh_max - vsh_min) / vsh_step)) + 1
    cutoffs = np.round(np.linspace(vsh_min, vsh_max, n_steps), 2)

    logger.info(
        f"Sweeping vsh_max across {len(cutoffs)} cutoffs: "
        f"{cutoffs.min():.2f} → {cutoffs.max():.2f} step {vsh_step:.2f}, "
        f"phit_min held at {phit_fixed}"
    )

    frames = []
    for cutoff in cutoffs:
        metrics = compute_all_zone_metrics(
            master, vsh_max=float(cutoff), phit_min=phit_fixed
        )
        metrics.insert(0, "vsh_cutoff", float(cutoff))
        frames.append(metrics)

    result = pd.concat(frames, ignore_index=True)
    logger.info(
        f"Sweep complete: {len(result)} rows "
        f"({len(cutoffs)} cutoffs × {len(result) // len(cutoffs)} (well, zone) groups)"
    )
    return result


# -----------------------------------------------------------------------------
# Bootstrap confidence intervals on kh
# -----------------------------------------------------------------------------

def bootstrap_kh_ci(
    master: pd.DataFrame,
    vsh_cutoffs: list[float] | None = None,
    phit_min: float = 0.08,
    n_bootstrap: int = 200,
    confidence: float = 0.90,
    random_state: int = 42,
) -> pd.DataFrame:
    """Bootstrap confidence intervals on kh per (well, zone, vsh_cutoff).

    The bootstrap is over **samples within each (well, zone) group** —
    we resample sample rows with replacement and recompute kh. This captures
    sampling-level uncertainty given the existing log measurements.

    It does NOT capture:
        - Tool-cap (saturation) uncertainty (perm >= 14999 is a censoring
          issue, not a sampling issue — would need a separate treatment).
        - Zone-top picking uncertainty.
        - Inter-well geological variability.

    Parameters
    ----------
    master : master table (well, zone, dz, vsh, phit, sw, perm)
    vsh_cutoffs : list of cutoffs to bootstrap over (default: just 0.5)
    phit_min : phit cutoff held constant
    n_bootstrap : number of resamples per group per cutoff
    confidence : confidence level (0.90 → percentile 5/95)
    random_state : reproducibility seed

    Returns
    -------
    DataFrame with columns:
        well, zone, vsh_cutoff, kh_mean, kh_p_low, kh_p_high, n_bootstrap
    """
    if vsh_cutoffs is None:
        vsh_cutoffs = [0.5]

    alpha = (1.0 - confidence) / 2.0
    p_low, p_high = 100 * alpha, 100 * (1 - alpha)

    rng = np.random.default_rng(random_state)
    df = master.dropna(subset=["zone"]).copy()

    rows = []
    grouped = df.groupby(["well", "zone"], observed=True)
    n_groups = len(grouped)
    logger.info(
        f"Bootstrapping kh CI: {n_groups} groups × {len(vsh_cutoffs)} cutoffs "
        f"× {n_bootstrap} resamples (confidence={confidence})"
    )

    for (well, zone), group in grouped:
        group_arr_perm = group["perm"].to_numpy()
        group_arr_dz = group["dz"].to_numpy()
        group_arr_vsh = group["vsh"].to_numpy()
        group_arr_phit = group["phit"].to_numpy()
        n = len(group)

        for cutoff in vsh_cutoffs:
            # Build the once-per-cutoff net mask, then bootstrap indices
            base_net_mask = (
                (group_arr_vsh <= cutoff)
                & (group_arr_phit >= 0.08 if phit_min == 0.08 else group_arr_phit >= phit_min)
                & ~np.isnan(group_arr_vsh)
                & ~np.isnan(group_arr_phit)
            )

            kh_samples = np.empty(n_bootstrap)
            for b in range(n_bootstrap):
                idx = rng.integers(0, n, size=n)
                net_mask_b = base_net_mask[idx]
                kh_samples[b] = float(
                    (group_arr_perm[idx][net_mask_b] * group_arr_dz[idx][net_mask_b]).sum()
                )

            rows.append(
                {
                    "well": int(well),
                    "zone": str(zone),
                    "vsh_cutoff": float(cutoff),
                    "kh_mean": float(kh_samples.mean()),
                    "kh_p_low": float(np.percentile(kh_samples, p_low)),
                    "kh_p_high": float(np.percentile(kh_samples, p_high)),
                    "kh_std": float(kh_samples.std(ddof=1)),
                    "n_bootstrap": n_bootstrap,
                }
            )

    result = pd.DataFrame(rows)
    logger.info(f"Bootstrap complete: {len(result)} CI rows")
    return result


# -----------------------------------------------------------------------------
# Knee detection
# -----------------------------------------------------------------------------

def detect_knee_points(
    sweep_results: pd.DataFrame,
    metric: str = "ntg",
) -> pd.DataFrame:
    """For each (well, zone), find the vsh cutoff at which `metric` falls
    most sharply — the "knee" of the curve.

    Algorithm: discrete first difference along the cutoff axis. The cutoff
    BEFORE the largest negative jump is the knee. Geological interpretation:
    a sharp knee means the zone has a bimodal vsh distribution and the cutoff
    sits right on the boundary; a flat curve means the zone is uniformly
    above or below the cutoff threshold.

    Parameters
    ----------
    sweep_results : output of run_vsh_sweep
    metric : column to track (default 'ntg'; try 'net_thickness_m' too)

    Returns
    -------
    DataFrame indexed by (well, zone) with knee_cutoff, knee_drop columns.
    """
    if metric not in sweep_results.columns:
        raise ValueError(f"metric '{metric}' not in sweep_results columns")

    rows = []
    for (well, zone), group in sweep_results.groupby(["well", "zone"], observed=True):
        g = group.sort_values("vsh_cutoff").reset_index(drop=True)
        # We sweep vsh_max from low to high, so metric (e.g. NTG) is non-decreasing.
        # The "knee" is where the metric RISES the most — the cutoff that adds
        # the most net to the picture. We flip sign convention vs. classical
        # elbow: largest positive diff = knee.
        diffs = g[metric].diff()
        if diffs.notna().any():
            idx = diffs.idxmax()
            knee_cutoff = float(g.loc[idx, "vsh_cutoff"])
            knee_jump = float(diffs.loc[idx])
        else:
            knee_cutoff = np.nan
            knee_jump = np.nan

        rows.append(
            {
                "well": int(well),
                "zone": str(zone),
                "knee_cutoff": knee_cutoff,
                "knee_jump": knee_jump,
                f"{metric}_at_min_cutoff": float(g[metric].iloc[0]),
                f"{metric}_at_max_cutoff": float(g[metric].iloc[-1]),
                f"{metric}_range": float(g[metric].iloc[-1] - g[metric].iloc[0]),
            }
        )

    return pd.DataFrame(rows)


# -----------------------------------------------------------------------------
# Convenience: field-level rollup of sweep
# -----------------------------------------------------------------------------

def field_sweep_summary(sweep_results: pd.DataFrame) -> pd.DataFrame:
    """Aggregate the per-(well, zone, cutoff) sweep up to (zone, cutoff).

    Useful for the per-zone sensitivity chart in Part C.2.
    """
    summary = (
        sweep_results.groupby(["zone", "vsh_cutoff"], observed=True)
        .agg(
            n_wells=("well", "nunique"),
            net_thickness_total=("net_thickness_m", "sum"),
            gross_thickness_total=("gross_thickness_m", "sum"),
            kh_total=("kh_mD_m", "sum"),
            ntg_mean=("ntg", "mean"),
            avg_perm_kh_weighted_mean=("avg_perm_kh_weighted_mD", "mean"),
        )
        .reset_index()
    )
    summary["ntg_field"] = (
        summary["net_thickness_total"] / summary["gross_thickness_total"]
    )
    return summary
