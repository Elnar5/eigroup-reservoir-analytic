"""
Smoke test: run the Part A pipeline end-to-end on whatever is in data/raw.

This is NOT the final CLI — just a sanity check that loader + quality + joiner
all wire together.
"""

from pathlib import Path

from loguru import logger

from src.data.loader import load_all_wells, load_zones, validate_well_zone_consistency
from src.data.quality import build_quality_report, render_report_to_markdown
from src.data.joiner import build_master_table


def main() -> None:
    raw_dir = Path("data/raw")
    reports_dir = Path("outputs/reports")

    valid_ranges = {
        "vsh":  {"min": 0.0,   "max": 1.0},
        "phit": {"min": 0.0,   "max": 0.5},
        "sw":   {"min": 0.0,   "max": 1.0},
        "perm": {"min": 0.001, "max": 15000.0},
    }

    logger.info("=" * 70)
    logger.info("Part A pipeline smoke test")
    logger.info("=" * 70)

    # 1. Load
    logs = load_all_wells(raw_dir)
    zones = load_zones(raw_dir)

    # 2. Validate
    issues = validate_well_zone_consistency(logs, zones)
    logger.info(f"Cross-validation issues: {issues}")

    # 3. Quality report
    report = build_quality_report(logs, zones, valid_ranges)
    md_path = render_report_to_markdown(report, reports_dir / "data_quality.md")
    logger.info(f"Wrote {md_path}")

    # 4. Build master table (zones + dz)
    master = build_master_table(logs, zones)
    logger.info(f"\nMaster table shape: {master.shape}")
    logger.info(f"Columns: {list(master.columns)}")
    logger.info(f"\nFirst 3 rows:\n{master.head(3)}")
    logger.info(f"\nZone distribution (samples per zone, summed across wells):")
    logger.info(master.zone.value_counts(dropna=False).sort_index())

    # 5. Save the master table for next steps
    out = Path("data/processed/master_table.parquet")
    out.parent.mkdir(parents=True, exist_ok=True)
    master.to_parquet(out, index=False)
    logger.info(f"\nSaved master table to {out}")
    logger.info("\nPart A pipeline: OK")


if __name__ == "__main__":
    main()
