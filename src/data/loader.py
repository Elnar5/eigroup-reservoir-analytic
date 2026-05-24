"""
Data loading layer.

Responsibilities
----------------
- Discover well CSV files in the raw directory (or use an explicit list)
- Load each well into a tidy DataFrame, sorted by depth, with a `well` column
- Load zones.csv and validate that every referenced well has a log file
- Return both as pandas DataFrames for downstream processing

Design notes
------------
We do NOT silently coerce or fill missing values here. Quality issues are
the job of `src/data/quality.py` — loading should be transparent. The only
exception is dtype enforcement: depth is always float, vsh/phit/sw/perm
are floats, the well id is int.
"""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd
from loguru import logger

# Schema the loader expects from every well CSV
EXPECTED_LOG_COLUMNS: tuple[str, ...] = ("depth", "vsh", "phit", "sw", "perm")
EXPECTED_ZONE_COLUMNS: tuple[str, ...] = ("well", "depth", "name")

# Filename pattern: well_<id>.csv  where <id> is an integer
_WELL_FILE_RE = re.compile(r"^well_(\d+)\.csv$")


def discover_wells(raw_dir: Path, pattern: str = "well_*.csv") -> list[int]:
    """
    Find all well CSV files in `raw_dir` matching `pattern` and return their ids.

    Parameters
    ----------
    raw_dir : Path
        Directory containing well_<id>.csv files.
    pattern : str
        Glob pattern for well files.

    Returns
    -------
    list[int]
        Sorted list of well ids (e.g. [1, 2, 3, 4, 5, 6, 7]).

    Raises
    ------
    FileNotFoundError
        If raw_dir does not exist or contains no matching files.
    """
    raw_dir = Path(raw_dir)
    if not raw_dir.exists():
        raise FileNotFoundError(f"Raw data directory not found: {raw_dir}")

    files = sorted(raw_dir.glob(pattern))
    well_ids: list[int] = []
    for f in files:
        m = _WELL_FILE_RE.match(f.name)
        if m:
            well_ids.append(int(m.group(1)))
        else:
            logger.warning(f"File {f.name} matches pattern but not well_<id>.csv naming")

    if not well_ids:
        raise FileNotFoundError(
            f"No well files found in {raw_dir} matching pattern {pattern!r}"
        )

    logger.info(f"Discovered {len(well_ids)} wells: {well_ids}")
    return sorted(well_ids)


def load_well(
    well_id: int,
    raw_dir: Path,
    validate_schema: bool = True,
) -> pd.DataFrame:
    """
    Load a single well CSV and return a tidy DataFrame.

    The returned frame has columns:
        well (int), depth (float), vsh (float), phit (float), sw (float), perm (float)
    Sorted ascending by depth. Missing values preserved (no fill/imputation here).

    Parameters
    ----------
    well_id : int
        Numeric well identifier (matches well_<id>.csv).
    raw_dir : Path
        Directory containing the well file.
    validate_schema : bool
        If True, raise on missing expected columns. Default True.

    Returns
    -------
    pd.DataFrame
    """
    raw_dir = Path(raw_dir)
    path = raw_dir / f"well_{well_id}.csv"
    if not path.exists():
        raise FileNotFoundError(f"Well file not found: {path}")

    df = pd.read_csv(path)

    if validate_schema:
        missing = set(EXPECTED_LOG_COLUMNS) - set(df.columns)
        if missing:
            raise ValueError(
                f"Well {well_id}: missing expected columns {sorted(missing)}. "
                f"Found: {list(df.columns)}"
            )

    # Force dtypes — pandas usually does this right but be explicit
    for col in EXPECTED_LOG_COLUMNS:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df.insert(0, "well", well_id)
    df = df.sort_values("depth").reset_index(drop=True)
    logger.debug(f"Loaded well {well_id}: {len(df)} rows, depth {df.depth.min():.2f}-{df.depth.max():.2f} m")
    return df


def load_all_wells(
    raw_dir: Path,
    well_ids: list[int] | None = None,
) -> pd.DataFrame:
    """
    Load every well in `well_ids` (or all discovered wells) and concatenate.

    Returns a single long DataFrame with one row per (well, depth) sample.
    Wells are loaded in numeric order and stacked vertically.

    Parameters
    ----------
    raw_dir : Path
        Directory containing well_<id>.csv files.
    well_ids : list[int] | None
        Explicit list of wells to load. If None, auto-discover.

    Returns
    -------
    pd.DataFrame
    """
    raw_dir = Path(raw_dir)
    if well_ids is None:
        well_ids = discover_wells(raw_dir)

    frames = [load_well(wid, raw_dir) for wid in well_ids]
    combined = pd.concat(frames, ignore_index=True)
    logger.info(
        f"Loaded {len(well_ids)} wells, {len(combined):,} total samples "
        f"({combined.well.nunique()} unique wells in frame)"
    )
    return combined


def load_zones(raw_dir: Path, filename: str = "zones.csv") -> pd.DataFrame:
    """
    Load zones.csv. Each row marks the TOP of a named zone within a well;
    the zone extends to the top of the next zone (or to bottom of log).

    Returns
    -------
    pd.DataFrame with columns (well, depth, name), sorted by (well, depth).
    """
    raw_dir = Path(raw_dir)
    path = raw_dir / filename
    if not path.exists():
        raise FileNotFoundError(f"Zones file not found: {path}")

    zones = pd.read_csv(path)
    missing = set(EXPECTED_ZONE_COLUMNS) - set(zones.columns)
    if missing:
        raise ValueError(
            f"zones.csv missing columns {sorted(missing)}. Found: {list(zones.columns)}"
        )

    zones["well"] = pd.to_numeric(zones["well"], errors="raise").astype(int)
    zones["depth"] = pd.to_numeric(zones["depth"], errors="raise")
    zones["name"] = zones["name"].astype(str).str.strip()
    zones = zones.sort_values(["well", "depth"]).reset_index(drop=True)

    logger.info(
        f"Loaded zones.csv: {len(zones)} zone tops across {zones.well.nunique()} wells, "
        f"unique zone names: {sorted(zones.name.unique())}"
    )
    return zones


def validate_well_zone_consistency(
    logs: pd.DataFrame,
    zones: pd.DataFrame,
) -> dict[str, list]:
    """
    Cross-check that:
      - every well in zones.csv also has log data
      - every well in logs has at least one zone defined
      - the first zone top of each well is at-or-above the shallowest log depth
        (otherwise the topmost log samples have no zone assignment)

    Returns a dict of issue category -> list of well ids. Empty lists mean clean.
    """
    log_wells = set(logs.well.unique())
    zone_wells = set(zones.well.unique())

    issues: dict[str, list] = {
        "zone_without_log": sorted(zone_wells - log_wells),
        "log_without_zone": sorted(log_wells - zone_wells),
        "first_zone_below_log_top": [],
    }

    for w in sorted(log_wells & zone_wells):
        log_top = logs.loc[logs.well == w, "depth"].min()
        first_zone_top = zones.loc[zones.well == w, "depth"].min()
        if first_zone_top > log_top:
            issues["first_zone_below_log_top"].append(
                {"well": w, "log_top": log_top, "first_zone_top": first_zone_top}
            )

    for cat, items in issues.items():
        if items:
            logger.warning(f"Validation issue [{cat}]: {items}")
    return issues
