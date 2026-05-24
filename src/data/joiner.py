"""
Zone joiner.

The zones.csv file records only zone TOPS (the depth at which a named zone
begins). Within a well, a zone extends from its listed top depth down to
the top of the next zone in that same well, or to the bottom of the log
for the last zone.

This module performs the spatial join: for every depth sample in the
combined log frame, assign the zone name it belongs to.

Strategy
--------
We use `pd.merge_asof` with direction="backward" on (well, depth). For each
log sample, we find the most-recent zone-top at-or-above that depth within
the same well. This is O((n + m) log m) per well and far faster than the
naive nested-loop approach.

Edge cases handled:
  - Samples shallower than the first zone top of their well → zone == NaN.
    These are reported in the data quality validation step.
  - Wells in logs but absent from zones.csv → all zone = NaN.
  - Zone names treated as strings (no implicit ordering).
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from loguru import logger


def assign_zones(logs: pd.DataFrame, zones: pd.DataFrame) -> pd.DataFrame:
    """
    Add a `zone` column to the combined log frame using zone-top records.

    Parameters
    ----------
    logs : pd.DataFrame
        Long-form log frame with columns (well, depth, vsh, phit, sw, perm).
    zones : pd.DataFrame
        Zone tops with columns (well, depth, name).

    Returns
    -------
    pd.DataFrame
        Same as `logs` plus a `zone` column (string, NaN where unassigned).

    Spec compliance
    ---------------
    data_dictionary.md states: "Every depth sample in the well log belongs
    to exactly one zone." In raw zones.csv, each well's first zone top is
    typically a few centimetres BELOW the log start (e.g. log starts at
    1850.00 m, zone A top is at 1850.07 m). That would leave the first
    sample of each well unassigned. We snap each well's earliest zone top
    down to that well's first log depth so the spec holds: zero NaN zones.
    """
    # ---- Snap each well's first zone top to the log's first depth ----
    log_first_depth = (
        logs.groupby("well", as_index=False)["depth"].min()
        .rename(columns={"depth": "log_first_depth"})
    )
    zones_with_first = zones.merge(log_first_depth, on="well", how="left")

    # For each well, find the index of its earliest zone top
    earliest_idx = zones_with_first.groupby("well")["depth"].idxmin()

    # Replace the earliest zone top's depth with the log's first depth, but
    # only if the log starts AT or ABOVE the original zone top (defensive:
    # if the log somehow starts deeper, we leave the zone top alone).
    zones_snapped = zones_with_first.copy()
    for well, idx in earliest_idx.items():
        log_start = zones_snapped.at[idx, "log_first_depth"]
        zone_top = zones_snapped.at[idx, "depth"]
        if log_start <= zone_top:
            zones_snapped.at[idx, "depth"] = log_start

    zones_snapped = zones_snapped.drop(columns=["log_first_depth"])

    # ---- Standard merge_asof zone assignment ----
    # merge_asof requires the `on` key to be globally sorted (per-group sort
    # is not enough in newer pandas). We sort by depth alone; the `by="well"`
    # parameter then constrains matches to the same well.
    logs_sorted = logs.sort_values("depth", kind="stable").reset_index(drop=True)
    zones_sorted = (
        zones_snapped[["well", "depth", "name"]]
        .rename(columns={"name": "zone"})
        .sort_values("depth", kind="stable")
        .reset_index(drop=True)
    )

    # direction="backward" picks the largest zone-top depth that is <= the
    # sample depth, within the same well.
    merged = pd.merge_asof(
        left=logs_sorted,
        right=zones_sorted,
        on="depth",
        by="well",
        direction="backward",
    )

    # Restore tidy (well, depth) ordering for downstream consumers
    merged = merged.sort_values(["well", "depth"]).reset_index(drop=True)

    # Diagnostics
    n_unassigned = int(merged.zone.isna().sum())
    if n_unassigned:
        unassigned_by_well = (
            merged[merged.zone.isna()]
            .groupby("well")
            .size()
            .to_dict()
        )
        logger.warning(
            f"{n_unassigned:,} samples have no zone assignment "
            f"(shallower than first zone top in well). Breakdown: {unassigned_by_well}"
        )
    else:
        logger.info("Zone assignment: 100% of samples assigned to a zone")

    return merged


def compute_dz(logs_with_zone: pd.DataFrame) -> pd.DataFrame:
    """
    Add a `dz` column: the thickness represented by each depth sample.

    Per data_dictionary.md:
      dz[i] = depth[i+1] - depth[i]  for all rows except the last
      dz[last] = dz[last-1]          (repeat the prior step)

    This is computed PER WELL because sampling steps may differ between wells.
    """
    out_frames = []
    for well_id, g in logs_with_zone.groupby("well", sort=True):
        g = g.sort_values("depth").reset_index(drop=True).copy()
        depths = g.depth.values
        if len(depths) < 2:
            g["dz"] = 0.0
        else:
            dz = np.diff(depths)
            dz = np.concatenate([dz, [dz[-1]]])  # repeat last step
            g["dz"] = dz
        out_frames.append(g)
    result = pd.concat(out_frames, ignore_index=True)
    logger.debug(
        f"Computed dz across {result.well.nunique()} wells. "
        f"Mean dz = {result.dz.mean():.4f} m"
    )
    return result


def build_master_table(logs: pd.DataFrame, zones: pd.DataFrame) -> pd.DataFrame:
    """
    One-shot helper: assign zones + compute dz. Returns the analytical-ready
    master table with columns:
        well, depth, vsh, phit, sw, perm, zone, dz
    """
    with_zones = assign_zones(logs, zones)
    master = compute_dz(with_zones)
    return master