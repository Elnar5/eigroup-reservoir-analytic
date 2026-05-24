"""
Part B: Per-(well, zone) reservoir metrics.

Required (from assignment):
    - gross_thickness     : total interval thickness, m
    - net_thickness       : thickness where vsh <= cutoff AND phit >= cutoff
    - avg_phit            : mean porosity in net interval
    - avg_perm            : arithmetic mean permeability in net interval
    - kh                  : sum(perm * dz) in net interval, mD*m

Bonus (signal real-data sophistication):
    - ntg                 : net_thickness / gross_thickness  (net-to-gross)
    - avg_perm_kh_weighted: kh / net_thickness (flow-relevant average)
    - lorenz_coefficient  : flow heterogeneity within the net interval
    - n_samples_net       : net-interval sample count (sanity check)
    - n_perm_saturated_in_net : how many net samples hit the 15000 mD cap
    - n_phit_nan          : how many samples were excluded due to NaN porosity

Design choices:
    * Net cutoffs come from config (default vsh_max=0.5, phit_min=0.08)
      so Part C.1 sensitivity sweep reuses the same function.
    * NaN porosity samples are EXCLUDED from net (well_3 has 78 such samples).
      Their count is reported separately so it never silently inflates net.
    * Permeability-saturated samples (perm >= 14999 mD) ARE counted in kh.
      Censoring them would systematically under-estimate flow capacity.
      The flag is surfaced so the consumer can decide.
    * dz is computed per well in joiner.compute_dz (well_5 has 0.5 m step,
      others 0.2 m), so kh and net_thickness handle mixed sampling correctly.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from loguru import logger

PERM_SATURATION_THRESHOLD = 14999.0  # samples >= this are tool-capped


# -----------------------------------------------------------------------------
# Core single-group metrics
# -----------------------------------------------------------------------------

def compute_zone_metrics(
    group: pd.DataFrame,
    vsh_max: float = 0.5,
    phit_min: float = 0.08,
) -> pd.Series:
    """Compute metrics for one (well, zone) group.

    Parameters
    ----------
    group : DataFrame with columns [vsh, phit, sw, perm, dz]
        All rows belong to the same (well, zone).
    vsh_max : float
        Maximum shale volume to qualify as net reservoir.
    phit_min : float
        Minimum porosity to qualify as net reservoir.

    Returns
    -------
    Series indexed by metric name.
    """
    # ---- gross interval ----
    gross_thickness = float(group["dz"].sum())
    n_samples = len(group)

    # ---- net mask ----
    # NaN in vsh or phit -> sample CANNOT be classified as net (False, not NaN).
    # This is the conservative, defensible choice: missing data ≠ reservoir.
    net_mask = (
        (group["vsh"] <= vsh_max)
        & (group["phit"] >= phit_min)
        & group["vsh"].notna()
        & group["phit"].notna()
    )
    net = group.loc[net_mask]

    n_phit_nan = int(group["phit"].isna().sum())
    n_samples_net = int(net_mask.sum())
    net_thickness = float(net["dz"].sum())

    # ---- averages in net ----
    if n_samples_net > 0:
        avg_phit = float(net["phit"].mean())
        avg_perm = float(net["perm"].mean())
        # kh-weighted avg perm: more meaningful for flow than arithmetic mean.
        # k_h_weighted = sum(k*dz) / sum(dz) = kh / net_thickness
        kh = float((net["perm"] * net["dz"]).sum())
        avg_perm_kh_weighted = kh / net_thickness if net_thickness > 0 else np.nan
    else:
        avg_phit = np.nan
        avg_perm = np.nan
        kh = 0.0
        avg_perm_kh_weighted = np.nan

    # ---- derived ratios ----
    ntg = net_thickness / gross_thickness if gross_thickness > 0 else np.nan

    # ---- diagnostics ----
    n_perm_saturated_in_net = int(
        (net["perm"] >= PERM_SATURATION_THRESHOLD).sum()
    ) if n_samples_net > 0 else 0

    # ---- Lorenz coefficient (flow heterogeneity) ----
    lorenz = _lorenz_coefficient(net) if n_samples_net >= 2 else np.nan

    return pd.Series(
        {
            "gross_thickness_m": gross_thickness,
            "net_thickness_m": net_thickness,
            "ntg": ntg,
            "avg_phit": avg_phit,
            "avg_perm_mD": avg_perm,
            "avg_perm_kh_weighted_mD": avg_perm_kh_weighted,
            "kh_mD_m": kh,
            "lorenz_coefficient": lorenz,
            "n_samples": n_samples,
            "n_samples_net": n_samples_net,
            "n_phit_nan": n_phit_nan,
            "n_perm_saturated_in_net": n_perm_saturated_in_net,
        }
    )


# -----------------------------------------------------------------------------
# Lorenz coefficient (flow heterogeneity within net)
# -----------------------------------------------------------------------------

def _lorenz_coefficient(net: pd.DataFrame) -> float:
    """Lorenz coefficient L in [0, 1]: 0 = perfectly homogeneous, 1 = all flow
    from one cell.

    Construction (Stiles / Schmalz-Rahme method, standard reservoir engineering):
      1. Sort samples by perm descending.
      2. Cumulative flow capacity F = cumsum(k*dz) / sum(k*dz).
      3. Cumulative storage capacity C = cumsum(phi*dz) / sum(phi*dz).
      4. Plot F vs C: deviation from 45-degree line = heterogeneity.
      5. L = 2 * (area between curve and diagonal).

    Net interval only — we are measuring heterogeneity within the reservoir,
    not across the cutoff boundary.
    """
    if len(net) < 2:
        return np.nan

    df = net[["perm", "phit", "dz"]].copy()
    df = df.sort_values("perm", ascending=False).reset_index(drop=True)

    flow_cap = df["perm"] * df["dz"]
    store_cap = df["phit"] * df["dz"]

    sum_flow = flow_cap.sum()
    sum_store = store_cap.sum()
    if sum_flow <= 0 or sum_store <= 0:
        return np.nan

    F = (flow_cap.cumsum() / sum_flow).to_numpy()
    C = (store_cap.cumsum() / sum_store).to_numpy()

    # Prepend (0, 0) so the integral starts at the origin.
    F = np.concatenate([[0.0], F])
    C = np.concatenate([[0.0], C])

    # Area under F vs C curve via trapezoid.
    area_under_curve = np.trapezoid(F, C)
    # Diagonal area is 0.5 (unit square).
    lorenz = 2.0 * (area_under_curve - 0.5)

    # Numerical floor: clip tiny negatives from floating-point noise.
    return float(max(0.0, min(1.0, lorenz)))


# -----------------------------------------------------------------------------
# Driver: master table -> per-(well, zone) metrics frame
# -----------------------------------------------------------------------------

def compute_all_zone_metrics(
    master: pd.DataFrame,
    vsh_max: float = 0.5,
    phit_min: float = 0.08,
    drop_unassigned: bool = True,
) -> pd.DataFrame:
    """Apply compute_zone_metrics across every (well, zone) group.

    Parameters
    ----------
    master : DataFrame from joiner.build_master_table
        Must contain columns [well, zone, depth, vsh, phit, sw, perm, dz].
    vsh_max, phit_min : net cutoffs.
    drop_unassigned : if True, drop rows where zone is NaN (above first zone
        top in well). These are the 7 sentinel rows flagged by the joiner.

    Returns
    -------
    DataFrame indexed by (well, zone) with one row per group.
    """
    required = {"well", "zone", "depth", "vsh", "phit", "sw", "perm", "dz"}
    missing = required - set(master.columns)
    if missing:
        raise ValueError(f"master table missing required columns: {missing}")

    df = master.copy()
    if drop_unassigned:
        n_before = len(df)
        df = df.dropna(subset=["zone"])
        n_dropped = n_before - len(df)
        if n_dropped > 0:
            logger.debug(
                f"compute_all_zone_metrics: dropped {n_dropped} rows with NaN zone "
                f"(samples above first zone top in their well)"
            )

    result = (
        df.groupby(["well", "zone"], sort=True, observed=True)
        .apply(
            compute_zone_metrics,
            vsh_max=vsh_max,
            phit_min=phit_min,
            include_groups=False,
        )
        .reset_index()
    )

    logger.info(
        f"Computed metrics for {len(result)} (well, zone) groups "
        f"using vsh_max={vsh_max}, phit_min={phit_min}"
    )
    return result


# -----------------------------------------------------------------------------
# Field-level rollups (used by Part C.2 charts + presentation)
# -----------------------------------------------------------------------------

def field_summary_by_zone(metrics: pd.DataFrame) -> pd.DataFrame:
    """Aggregate per-(well, zone) metrics up to zone-level (field view).

    Useful for: 'Which zone delivers the most kh field-wide?' charts.
    """
    summary = (
        metrics.groupby("zone", observed=True)
        .agg(
            n_wells=("well", "nunique"),
            gross_thickness_m_total=("gross_thickness_m", "sum"),
            net_thickness_m_total=("net_thickness_m", "sum"),
            kh_mD_m_total=("kh_mD_m", "sum"),
            avg_phit_mean=("avg_phit", "mean"),
            avg_perm_kh_weighted_mD_mean=("avg_perm_kh_weighted_mD", "mean"),
            ntg_mean=("ntg", "mean"),
        )
        .reset_index()
    )
    summary["ntg_field"] = (
        summary["net_thickness_m_total"] / summary["gross_thickness_m_total"]
    )
    return summary


def field_summary_by_well(metrics: pd.DataFrame) -> pd.DataFrame:
    """Aggregate per-(well, zone) metrics up to well-level.

    Useful for: 'Which well has the most kh?' ranking.
    """
    summary = (
        metrics.groupby("well", observed=True)
        .agg(
            n_zones=("zone", "nunique"),
            gross_thickness_m_total=("gross_thickness_m", "sum"),
            net_thickness_m_total=("net_thickness_m", "sum"),
            kh_mD_m_total=("kh_mD_m", "sum"),
            n_perm_saturated_total=("n_perm_saturated_in_net", "sum"),
        )
        .reset_index()
    )
    summary["ntg_well"] = (
        summary["net_thickness_m_total"] / summary["gross_thickness_m_total"]
    )
    return summary
