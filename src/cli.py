"""
Command-line interface for the reservoir analytics pipeline.

Each sub-command corresponds to one stage of the assignment. Configuration
is loaded from configs/config.yaml via Hydra-compatible OmegaConf; CLI flags
can override anything.

Usage:
    python -m src.cli quality       # Part A
    python -m src.cli metrics       # Part B
    python -m src.cli sweep         # Part C.1
    python -m src.cli field         # Part C.2
    python -m src.cli subzones      # Part D
    python -m src.cli run-all       # everything in order
"""

from __future__ import annotations

import sys
from pathlib import Path

import typer
from loguru import logger
from omegaconf import OmegaConf

app = typer.Typer(
    name="reservoir-cli",
    help="eiGroup reservoir analytics pipeline.",
    no_args_is_help=True,
)


# -----------------------------------------------------------------------------
# Shared helpers
# -----------------------------------------------------------------------------

DEFAULT_CONFIG = "configs/config.yaml"


def _load_config(config_path: str) -> OmegaConf:
    """
    Load the main config file, then resolve the `defaults:` group references
    by hand (we want to keep dependencies minimal — no Hydra runtime).
    """
    base = OmegaConf.load(config_path)

    # Resolve `defaults:` block — load each referenced sub-config
    base_dir = Path(config_path).parent
    if "defaults" in base:
        for entry in base.defaults:
            if entry == "_self_":
                continue
            # entry like {"cutoffs": "default"} -> load configs/cutoffs/default.yaml
            if isinstance(entry, dict) or hasattr(entry, "items"):
                for group, name in entry.items():
                    sub_path = base_dir / group / f"{name}.yaml"
                    if sub_path.exists():
                        sub = OmegaConf.load(sub_path)
                        # Merge under the group key
                        base[group] = OmegaConf.merge(base.get(group, {}), sub)
        # Drop the defaults marker now that we've resolved it
        del base["defaults"]

    return base


def _setup_logging(level: str = "INFO") -> None:
    logger.remove()
    logger.add(sys.stderr, level=level, format="<g>{time:HH:mm:ss}</g> | <lvl>{level: <7}</lvl> | <c>{name}</c> | {message}")


# -----------------------------------------------------------------------------
# Sub-commands
# -----------------------------------------------------------------------------


@app.command("quality")
def quality_cmd(
    config: str = typer.Option(DEFAULT_CONFIG, "--config", "-c", help="Path to config YAML"),
) -> None:
    """Part A — generate the data quality report and master table."""
    from src.data.joiner import build_master_table
    from src.data.loader import load_all_wells, load_zones, validate_well_zone_consistency
    from src.data.quality import build_quality_report, render_report_to_markdown

    cfg = _load_config(config)
    _setup_logging(cfg.runtime.log_level)

    raw_dir = Path(cfg.data.raw_dir)
    reports_dir = Path(cfg.output.reports_dir)
    processed_dir = Path(cfg.data.processed_dir)

    well_ids = OmegaConf.to_object(cfg.data.wells) if cfg.data.wells is not None else None
    logs = load_all_wells(raw_dir, well_ids=well_ids)
    zones = load_zones(raw_dir, cfg.data.zones_file)

    issues = validate_well_zone_consistency(logs, zones)
    # Only flag at WARNING level for real (un-fixed) issues. The
    # `first_zone_below_log_top` category is auto-fixed by the joiner.
    real_issues = {
        k: v for k, v in issues.items()
        if v and k != "first_zone_below_log_top"
    }
    if real_issues:
        logger.warning(f"Cross-validation issues detected: {list(real_issues.keys())}")

    valid_ranges = OmegaConf.to_object(cfg.validity)
    report = build_quality_report(logs, zones, valid_ranges)
    render_report_to_markdown(report, reports_dir / "data_quality.md")

    master = build_master_table(logs, zones)
    if cfg.runtime.save_intermediates:
        processed_dir.mkdir(parents=True, exist_ok=True)
        out = processed_dir / "master_table.parquet"
        master.to_parquet(out, index=False)
        logger.info(f"Saved master table: {out} ({len(master):,} rows)")


@app.command("metrics")
def metrics_cmd(
    config: str = typer.Option(DEFAULT_CONFIG, "--config", "-c"),
    vsh_max: float = typer.Option(None, "--vsh-max", help="Override cutoffs.vsh_max"),
    phit_min: float = typer.Option(None, "--phit-min", help="Override cutoffs.phit_min"),
) -> None:
    """Part B — compute the per-(well, zone) analytical table and field rollups."""
    from src.analytics.metrics import (
        compute_all_zone_metrics,
        field_summary_by_well,
        field_summary_by_zone,
    )
    from src.data.joiner import build_master_table
    from src.data.loader import load_all_wells, load_zones

    cfg = _load_config(config)
    _setup_logging(cfg.runtime.log_level)

    raw_dir = Path(cfg.data.raw_dir)
    processed_dir = Path(cfg.data.processed_dir)
    reports_dir = Path(cfg.output.reports_dir)

    # Resolve cutoffs: CLI flag > config > default
    vsh_cut = vsh_max if vsh_max is not None else cfg.cutoffs.vsh_max
    phit_cut = phit_min if phit_min is not None else cfg.cutoffs.phit_min
    logger.info(f"Net cutoffs: vsh_max={vsh_cut}, phit_min={phit_cut}")

    # Reuse the master table if it was already saved by `quality`; otherwise rebuild.
    master_path = processed_dir / "master_table.parquet"
    if master_path.exists():
        import pandas as pd
        master = pd.read_parquet(master_path)
        logger.info(f"Loaded cached master table: {master_path} ({len(master):,} rows)")
    else:
        well_ids = OmegaConf.to_object(cfg.data.wells) if cfg.data.wells is not None else None
        logs = load_all_wells(raw_dir, well_ids=well_ids)
        zones = load_zones(raw_dir, cfg.data.zones_file)
        master = build_master_table(logs, zones)
        logger.info(f"Built master table on the fly: {len(master):,} rows")

    # Per-(well, zone) metrics
    metrics = compute_all_zone_metrics(master, vsh_max=vsh_cut, phit_min=phit_cut)
    by_zone = field_summary_by_zone(metrics)
    by_well = field_summary_by_well(metrics)

    # Save artefacts: CSV (human-readable) + parquet (machine-friendly)
    processed_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    metrics_csv = reports_dir / "metrics_per_zone.csv"
    by_zone_csv = reports_dir / "field_summary_by_zone.csv"
    by_well_csv = reports_dir / "field_summary_by_well.csv"
    metrics_parq = processed_dir / "metrics_per_zone.parquet"

    metrics.to_csv(metrics_csv, index=False, float_format="%.6f")
    by_zone.to_csv(by_zone_csv, index=False, float_format="%.6f")
    by_well.to_csv(by_well_csv, index=False, float_format="%.6f")
    if cfg.runtime.save_intermediates:
        metrics.to_parquet(metrics_parq, index=False)

    logger.info(f"Wrote {metrics_csv} ({len(metrics)} rows)")
    logger.info(f"Wrote {by_zone_csv}")
    logger.info(f"Wrote {by_well_csv}")
    if cfg.runtime.save_intermediates:
        logger.info(f"Wrote {metrics_parq}")


@app.command("sweep")
def sweep_cmd(
    config: str = typer.Option(DEFAULT_CONFIG, "--config", "-c"),
    bootstrap: bool = typer.Option(False, "--bootstrap", help="Also compute bootstrap CI on kh (slow)"),
) -> None:
    """Part C.1 — vsh cutoff sensitivity sweep."""
    from src.analytics.sensitivity import (
        bootstrap_kh_ci,
        detect_knee_points,
        field_sweep_summary,
        run_vsh_sweep,
    )
    from src.data.joiner import build_master_table
    from src.data.loader import load_all_wells, load_zones

    cfg = _load_config(config)
    _setup_logging(cfg.runtime.log_level)

    raw_dir = Path(cfg.data.raw_dir)
    processed_dir = Path(cfg.data.processed_dir)
    reports_dir = Path(cfg.output.reports_dir)

    # Reuse cached master table if available
    master_path = processed_dir / "master_table.parquet"
    if master_path.exists():
        import pandas as pd
        master = pd.read_parquet(master_path)
        logger.info(f"Loaded cached master table: {master_path} ({len(master):,} rows)")
    else:
        well_ids = OmegaConf.to_object(cfg.data.wells) if cfg.data.wells is not None else None
        logs = load_all_wells(raw_dir, well_ids=well_ids)
        zones = load_zones(raw_dir, cfg.data.zones_file)
        master = build_master_table(logs, zones)

    # ---- Sweep ----
    sweep = run_vsh_sweep(
        master,
        vsh_min=cfg.sensitivity.vsh_min,
        vsh_max=cfg.sensitivity.vsh_max,
        vsh_step=cfg.sensitivity.vsh_step,
        phit_fixed=cfg.sensitivity.phit_fixed,
    )

    # ---- Knee detection ----
    knees_ntg = detect_knee_points(sweep, metric="ntg")
    knees_kh = detect_knee_points(sweep, metric="kh_mD_m")

    # ---- Field summary ----
    summary = field_sweep_summary(sweep)

    # ---- Save ----
    reports_dir.mkdir(parents=True, exist_ok=True)
    processed_dir.mkdir(parents=True, exist_ok=True)

    sweep.to_csv(reports_dir / "sweep_results.csv", index=False, float_format="%.6f")
    knees_ntg.to_csv(reports_dir / "knee_points_ntg.csv", index=False, float_format="%.6f")
    knees_kh.to_csv(reports_dir / "knee_points_kh.csv", index=False, float_format="%.6f")
    summary.to_csv(reports_dir / "sweep_field_summary.csv", index=False, float_format="%.6f")
    if cfg.runtime.save_intermediates:
        sweep.to_parquet(processed_dir / "sweep_results.parquet", index=False)

    logger.info(f"Wrote sweep_results.csv ({len(sweep)} rows)")
    logger.info(f"Wrote knee_points_ntg.csv, knee_points_kh.csv")
    logger.info(f"Wrote sweep_field_summary.csv")

    # ---- Optional bootstrap ----
    if bootstrap:
        # Bootstrap at every cutoff is expensive. Default: just the 3 most
        # interesting cutoffs (low, default, high).
        cutoffs_for_ci = [
            float(cfg.sensitivity.vsh_min),
            float(cfg.cutoffs.vsh_max),
            float(cfg.sensitivity.vsh_max),
        ]
        ci = bootstrap_kh_ci(
            master,
            vsh_cutoffs=cutoffs_for_ci,
            phit_min=cfg.sensitivity.phit_fixed,
            n_bootstrap=cfg.sensitivity.bootstrap_samples,
            confidence=cfg.sensitivity.confidence_level,
            random_state=cfg.runtime.random_seed,
        )
        ci.to_csv(reports_dir / "kh_bootstrap_ci.csv", index=False, float_format="%.6f")
        logger.info(f"Wrote kh_bootstrap_ci.csv ({len(ci)} rows)")


@app.command("field")
def field_cmd(
    config: str = typer.Option(DEFAULT_CONFIG, "--config", "-c"),
) -> None:
    """Part C.2 — field-level views (5 charts, PNG + HTML)."""
    import pandas as pd
    from src.data.joiner import build_master_table
    from src.data.loader import load_all_wells, load_zones
    from src.visualization.field import (
        crossplot_phit_perm,
        heatmap_kh_by_well_zone,
        lorenz_curves,
        save_chart,
        sensitivity_ntg_curves,
        stacked_bar_kh_per_well,
    )

    cfg = _load_config(config)
    _setup_logging(cfg.runtime.log_level)

    raw_dir = Path(cfg.data.raw_dir)
    processed_dir = Path(cfg.data.processed_dir)
    figures_dir = Path(cfg.output.figures_dir)

    # Load master + metrics + sweep (build if absent)
    master_path = processed_dir / "master_table.parquet"
    metrics_path = processed_dir / "metrics_per_zone.parquet"
    sweep_path = processed_dir / "sweep_results.parquet"

    if master_path.exists():
        master = pd.read_parquet(master_path)
    else:
        logs = load_all_wells(raw_dir)
        zones = load_zones(raw_dir, cfg.data.zones_file)
        master = build_master_table(logs, zones)

    if metrics_path.exists():
        metrics = pd.read_parquet(metrics_path)
    else:
        from src.analytics.metrics import compute_all_zone_metrics
        metrics = compute_all_zone_metrics(
            master, vsh_max=cfg.cutoffs.vsh_max, phit_min=cfg.cutoffs.phit_min
        )

    sweep = pd.read_parquet(sweep_path) if sweep_path.exists() else None

    # 1. kh heatmap
    fig_m, fig_p = heatmap_kh_by_well_zone(metrics)
    save_chart(fig_m, fig_p, "01_kh_heatmap", figures_dir)

    # 2. stacked bar
    fig_m, fig_p = stacked_bar_kh_per_well(metrics)
    save_chart(fig_m, fig_p, "02_kh_stacked_bar", figures_dir)

    # 3. phi-k cross-plot
    fig_m, fig_p = crossplot_phit_perm(master)
    save_chart(fig_m, fig_p, "03_phit_perm_crossplot", figures_dir)

    # 4. sensitivity (needs sweep results)
    if sweep is not None:
        fig_m, fig_p = sensitivity_ntg_curves(sweep)
        save_chart(fig_m, fig_p, "04_ntg_sensitivity", figures_dir)
    else:
        logger.warning("sweep_results.parquet not found — skipping NTG sensitivity chart. "
                       "Run `python -m src.cli sweep` first.")

    # 5. Lorenz
    fig_m, fig_p = lorenz_curves(master, vsh_max=cfg.cutoffs.vsh_max, phit_min=cfg.cutoffs.phit_min)
    save_chart(fig_m, fig_p, "05_lorenz_curves", figures_dir)

    logger.info(f"All field-view charts saved to {figures_dir}")


@app.command("subzones")
def subzones_cmd(
    config: str = typer.Option(DEFAULT_CONFIG, "--config", "-c"),
    no_validate: bool = typer.Option(False, "--no-validate", help="Skip leave-one-well-out validation"),
    target_zone: str = typer.Option(None, "--target-zone", "-z", help="Override clustering.target_zone (e.g. 'C')"),
    n_clusters: int = typer.Option(None, "--n-clusters", "-k", help="Override clustering.n_clusters"),
) -> None:
    """Part D — sub-zone clustering on the target zone."""
    import pandas as pd
    from sklearn.preprocessing import StandardScaler

    from src.clustering.subzone import (
        build_feature_frame,
        fit_clustering,
        leave_one_well_out_validation,
        search_optimal_k,
        smooth_labels,
        subzone_metrics,
    )
    from src.data.joiner import build_master_table
    from src.data.loader import load_all_wells, load_zones
    from src.visualization.clustering import (
        cross_well_centroids,
        depth_profile_per_well,
        optimal_k_plot,
        save_chart,
    )

    cfg = _load_config(config)
    _setup_logging(cfg.runtime.log_level)

    raw_dir = Path(cfg.data.raw_dir)
    processed_dir = Path(cfg.data.processed_dir)
    reports_dir = Path(cfg.output.reports_dir)
    figures_dir = Path(cfg.output.figures_dir)

    # Load master
    master_path = processed_dir / "master_table.parquet"
    if master_path.exists():
        master = pd.read_parquet(master_path)
        logger.info(f"Loaded cached master table: {master_path} ({len(master):,} rows)")
    else:
        logs = load_all_wells(raw_dir)
        zones = load_zones(raw_dir, cfg.data.zones_file)
        master = build_master_table(logs, zones)

    target_zone = target_zone if target_zone is not None else cfg.clustering.target_zone
    features = list(cfg.clustering.features)
    n_clusters = int(n_clusters if n_clusters is not None else cfg.clustering.n_clusters)
    method = cfg.clustering.method
    logger.info(f"Clustering: target_zone={target_zone}, n_clusters={n_clusters}, method={method}")

    # Optimal-K analysis (runs both KMeans and GMM regardless of method)
    fdf = build_feature_frame(master[master["zone"] == target_zone], features)
    scaler = StandardScaler()
    X = scaler.fit_transform(fdf.values)
    opt = search_optimal_k(
        X,
        k_min=int(cfg.clustering.k_search_min),
        k_max=int(cfg.clustering.k_search_max),
        random_state=int(cfg.runtime.random_seed),
    )

    # Save optimal-K table (postfixed by zone so reruns on different zones don't overwrite)
    z = target_zone.lower()
    opt_df = pd.DataFrame({
        "k": opt.k_range,
        "kmeans_inertia": opt.kmeans_inertia,
        "kmeans_silhouette": opt.kmeans_silhouette,
        "gmm_bic": opt.gmm_bic,
        "gmm_silhouette": opt.gmm_silhouette,
    })
    reports_dir.mkdir(parents=True, exist_ok=True)
    opt_df.to_csv(reports_dir / f"optimal_k_analysis_zone{z}.csv", index=False, float_format="%.6f")

    # Fit method(s) and gather results
    methods_to_run = ["kmeans", "gmm"] if method == "both" else [method]
    chosen_result = None
    for m in methods_to_run:
        result = fit_clustering(
            master, target_zone, features, method=m, n_clusters=n_clusters,
            random_state=int(cfg.runtime.random_seed),
        )
        # Smooth labels
        if cfg.clustering.smoothing.enabled:
            labels_series = pd.Series(result.labels, index=result.feature_df.index)
            smoothed = smooth_labels(
                master, target_zone, labels_series,
                window_size=int(cfg.clustering.smoothing.window_size),
                min_run_length=int(cfg.clustering.smoothing.min_run_length),
            )
        else:
            smoothed = pd.Series(result.labels, index=result.feature_df.index)

        # Per-(well, sub_zone) metrics
        sub_metrics = subzone_metrics(master, target_zone, smoothed)
        sub_metrics.to_csv(
            reports_dir / f"subzone_metrics_zone{z}_{m}.csv",
            index=False, float_format="%.6f"
        )

        # Sample-level assignments
        assignments = master.loc[smoothed.index, ["well", "depth", "zone"]].copy()
        assignments["sub_zone"] = smoothed.values
        assignments.to_csv(
            reports_dir / f"subzone_assignments_zone{z}_{m}.csv",
            index=False, float_format="%.6f"
        )

        # Cross-well validation
        if cfg.clustering.validation.leave_one_well_out and not no_validate:
            lowo = leave_one_well_out_validation(
                master, target_zone, features, result, method=m,
                n_clusters=n_clusters, random_state=int(cfg.runtime.random_seed),
            )
            lowo.to_csv(
                reports_dir / f"lowo_validation_zone{z}_{m}.csv",
                index=False, float_format="%.6f"
            )
            logger.info(f"  {m} LOWO ARI mean: {lowo['ari_vs_pooled'].mean():.3f}")

        # Charts (only for the first/primary method to avoid duplication)
        if chosen_result is None:
            chosen_result = result
            chosen_smoothed = smoothed

            fig_m, fig_p = depth_profile_per_well(master, target_zone, smoothed)
            save_chart(fig_m, fig_p, f"06_zone{z}_clusters_log", figures_dir)

            fig_m, fig_p = optimal_k_plot(opt)
            save_chart(fig_m, fig_p, f"07_zone{z}_silhouette", figures_dir)

            fig_m, fig_p = cross_well_centroids(
                master, target_zone, smoothed, features
            )
            save_chart(fig_m, fig_p, f"08_zone{z}_cross_well_consistency", figures_dir)

        # Save centroid summary
        chosen_result.centroids_original_scale.to_csv(
            reports_dir / f"subzone_centroids_zone{z}_{m}.csv", float_format="%.6f"
        )

    logger.info(
        f"Sub-zone clustering complete: zone='{target_zone}', "
        f"n_clusters={n_clusters}, method={method}"
    )


@app.command("run-all")
def run_all(
    config: str = typer.Option(DEFAULT_CONFIG, "--config", "-c"),
) -> None:
    """Run the full pipeline (Parts A → D)."""
    quality_cmd(config)
    metrics_cmd(config)
    sweep_cmd(config)
    field_cmd(config)
    subzones_cmd(config)


if __name__ == "__main__":
    app()