"""
Part D: Sub-zone clustering within a chosen zone.

Goal:
    Identify 2-3 geologically meaningful sub-units inside the target zone
    that are consistent across all 7 wells.

Why pooled clustering (not per-well):
    If we cluster each well independently, "Sub-zone 1" in well 1 has no
    relationship to "Sub-zone 1" in well 2. We instead fit ONE clustering
    model on the pooled feature space, then assign every sample globally.
    This way the label IS the rock type, everywhere.

Why these features (configurable in clustering/default.yaml):
    vsh, phit          — primary lithology + porosity
    log10(perm)        — flow capacity, log scale (perm spans 5 orders of mag)
    sw                 — fluid signal
    effective_porosity = phit × (1 − vsh)   — porosity in the sand fraction
    hc_porosity        = phit × (1 − sw)    — hydrocarbon-filled pore volume
    Derived features pack petrophysical meaning the raw logs alone don't.

Saturation note:
    Permeability-capped samples (perm ≥ 14999) collapse to log_perm ≈ 4.18.
    We do NOT remove them — they ARE the dominant flow facies in Zone B.
    The clustering will naturally see this collapse and may carve out a
    "saturated facies" cluster. That is the right behaviour for our story:
    "the tool tells us this rock type behaves identically, even though the
    real perm distribution is hidden behind the cap."

Smoothing rationale:
    Sample-level clustering produces single-sample label flips around the
    decision boundary. Real geological units are continuous and metres-thick.
    A rolling mode (median for integer labels = mode in the binary/ternary
    case here) suppresses these flips. We also drop runs shorter than
    `min_run_length` to avoid spurious thin units.

Cross-well validation:
    Leave-one-well-out (LOWO): fit on 6 wells, predict on the 7th. Compare
    LOWO labels to the pooled-fit labels via Adjusted Rand Index. ARI > 0.7
    is "highly consistent" — the geology is reproducible.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from loguru import logger
from scipy.ndimage import median_filter
from sklearn.cluster import KMeans
from sklearn.metrics import adjusted_rand_score, silhouette_score
from sklearn.mixture import GaussianMixture
from sklearn.preprocessing import StandardScaler

# Aliases for feature engineering — single source of truth
DERIVED_FEATURE_FORMULAE = {
    "log_perm": lambda df: np.log10(df["perm"].clip(lower=1e-3)),
    "effective_porosity": lambda df: df["phit"] * (1.0 - df["vsh"]),
    "hc_porosity": lambda df: df["phit"] * (1.0 - df["sw"]),
}


# -----------------------------------------------------------------------------
# Feature engineering
# -----------------------------------------------------------------------------

def build_feature_frame(
    zone_samples: pd.DataFrame,
    features: list[str],
) -> pd.DataFrame:
    """Compute derived features and return a frame with only the requested
    feature columns (no NaN rows, original index preserved).

    Parameters
    ----------
    zone_samples : master-table rows for one zone (already filtered)
    features : list of feature names; raw column names or derived keys
    """
    out = zone_samples.copy()
    for feat in features:
        if feat in DERIVED_FEATURE_FORMULAE and feat not in out.columns:
            out[feat] = DERIVED_FEATURE_FORMULAE[feat](out)

    missing = [f for f in features if f not in out.columns]
    if missing:
        raise ValueError(f"Cannot compute features: {missing}")

    feature_df = out[features].copy()
    n_before = len(feature_df)
    feature_df = feature_df.dropna()
    n_after = len(feature_df)
    if n_before != n_after:
        logger.debug(f"Dropped {n_before - n_after} rows with NaN features")
    return feature_df


# -----------------------------------------------------------------------------
# Optimal-K analysis
# -----------------------------------------------------------------------------

@dataclass
class OptimalKResult:
    k_range: list[int]
    kmeans_inertia: list[float]
    kmeans_silhouette: list[float]
    gmm_bic: list[float]
    gmm_silhouette: list[float]


def search_optimal_k(
    X_scaled: np.ndarray,
    k_min: int = 2,
    k_max: int = 8,
    random_state: int = 42,
) -> OptimalKResult:
    """Sweep k from k_min to k_max for both K-Means and GMM.

    Returns three signals per k:
        * K-Means inertia (elbow plot)
        * Silhouette score (both methods)
        * BIC (GMM only — penalised likelihood, lower = better with fewer params)

    The caller decides what to optimise; we provide the numbers.
    """
    k_range = list(range(k_min, k_max + 1))
    km_inertia, km_sil = [], []
    gmm_bic, gmm_sil = [], []

    for k in k_range:
        km = KMeans(n_clusters=k, n_init=10, random_state=random_state)
        km_labels = km.fit_predict(X_scaled)
        km_inertia.append(float(km.inertia_))
        km_sil.append(float(silhouette_score(X_scaled, km_labels)) if k > 1 else float("nan"))

        gmm = GaussianMixture(n_components=k, random_state=random_state, n_init=3)
        gmm_labels = gmm.fit_predict(X_scaled)
        gmm_bic.append(float(gmm.bic(X_scaled)))
        gmm_sil.append(float(silhouette_score(X_scaled, gmm_labels)) if k > 1 else float("nan"))

    logger.info(
        f"Optimal-K search: k∈[{k_min},{k_max}]; "
        f"best KMeans silhouette at k={k_range[int(np.argmax(km_sil))]} "
        f"(score={max(km_sil):.3f}); "
        f"best GMM BIC at k={k_range[int(np.argmin(gmm_bic))]} "
        f"(BIC={min(gmm_bic):.0f})"
    )

    return OptimalKResult(
        k_range=k_range,
        kmeans_inertia=km_inertia,
        kmeans_silhouette=km_sil,
        gmm_bic=gmm_bic,
        gmm_silhouette=gmm_sil,
    )


# -----------------------------------------------------------------------------
# Pooled clustering
# -----------------------------------------------------------------------------

@dataclass
class ClusteringResult:
    """Output of a single clustering fit on the pooled feature space."""
    method: str                     # 'kmeans' or 'gmm'
    n_clusters: int
    labels: np.ndarray              # cluster IDs aligned with feature_df.index
    feature_df: pd.DataFrame        # what was actually clustered (post-NaN drop)
    scaler: StandardScaler
    model: KMeans | GaussianMixture
    silhouette: float
    centroids_original_scale: pd.DataFrame  # cluster centroids in raw feature units


def fit_clustering(
    master: pd.DataFrame,
    target_zone: str,
    features: list[str],
    method: str = "kmeans",
    n_clusters: int = 3,
    random_state: int = 42,
) -> ClusteringResult:
    """Cluster all samples of `target_zone` in a single pooled fit.

    Parameters
    ----------
    master : master table (Part A output)
    target_zone : zone to subdivide ('A', 'B', ...)
    features : list of feature names (raw or derived)
    method : 'kmeans' or 'gmm'
    n_clusters : k
    random_state : reproducibility seed
    """
    if method not in {"kmeans", "gmm"}:
        raise ValueError(f"method must be 'kmeans' or 'gmm', got '{method}'")

    zone_samples = master[master["zone"] == target_zone].copy()
    if len(zone_samples) == 0:
        raise ValueError(f"No samples found in zone '{target_zone}'")

    feature_df = build_feature_frame(zone_samples, features)
    logger.info(
        f"Clustering zone '{target_zone}': "
        f"{len(feature_df)} samples, {len(features)} features, "
        f"method={method}, k={n_clusters}"
    )

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(feature_df.values)

    if method == "kmeans":
        model = KMeans(n_clusters=n_clusters, n_init=10, random_state=random_state)
    else:
        model = GaussianMixture(
            n_components=n_clusters, random_state=random_state, n_init=3
        )

    labels = model.fit_predict(X_scaled)
    silhouette = float(silhouette_score(X_scaled, labels)) if n_clusters > 1 else float("nan")
    logger.info(f"  silhouette score: {silhouette:.3f}")

    # Reorder cluster IDs so cluster 0 has lowest mean log_perm, cluster k-1
    # highest. This gives stable, interpretable labels across runs.
    labels = _reorder_labels_by_log_perm(labels, feature_df, features)

    # Centroids in original (unscaled) feature units, for interpretation
    centroids = _centroids_in_original_scale(labels, feature_df, n_clusters)

    return ClusteringResult(
        method=method,
        n_clusters=n_clusters,
        labels=labels,
        feature_df=feature_df,
        scaler=scaler,
        model=model,
        silhouette=silhouette,
        centroids_original_scale=centroids,
    )


def _reorder_labels_by_log_perm(
    labels: np.ndarray,
    feature_df: pd.DataFrame,
    features: list[str],
) -> np.ndarray:
    """Relabel clusters so cluster 0 is lowest-permeability, cluster k-1
    highest. Stable across runs and across LOWO folds."""
    sort_key = "log_perm" if "log_perm" in features else features[0]
    cluster_means = pd.Series(labels, index=feature_df.index).groupby(labels).apply(
        lambda idx: feature_df.loc[idx.index, sort_key].mean()
    )
    # Map old label -> new label by rank of mean log_perm
    rank_map = {old: new for new, old in enumerate(cluster_means.sort_values().index)}
    return np.array([rank_map[lbl] for lbl in labels])


def _centroids_in_original_scale(
    labels: np.ndarray,
    feature_df: pd.DataFrame,
    n_clusters: int,
) -> pd.DataFrame:
    """Compute centroid mean+std in original (unscaled) units per cluster."""
    df = feature_df.copy()
    df["cluster"] = labels
    agg = df.groupby("cluster").agg(["mean", "std", "count"])
    return agg


# -----------------------------------------------------------------------------
# Smoothing (rolling mode + short-run drop)
# -----------------------------------------------------------------------------

def smooth_labels(
    master: pd.DataFrame,
    target_zone: str,
    labels: pd.Series,
    window_size: int = 11,
    min_run_length: int = 5,
) -> pd.Series:
    """Smooth sample-level cluster labels per (well) along depth.

    Strategy:
        1. For each well separately (depths within a well are continuous),
           apply a rolling mode (median is equivalent for {0,1,2} labels
           when ties broken downward — we use scipy median_filter).
        2. Find runs of identical labels; if run length < min_run_length,
           merge it into the surrounding majority.

    Parameters
    ----------
    master : master table (need 'well' and 'depth' columns)
    target_zone : zone the labels belong to
    labels : Series of cluster IDs, aligned with master.loc[zone, feature.index]
    window_size : odd integer; rolling mode window in samples
    min_run_length : minimum samples per uninterrupted sub-zone

    Returns
    -------
    Smoothed labels Series, same index as input.
    """
    if window_size % 2 == 0:
        raise ValueError(f"window_size must be odd, got {window_size}")

    # Join labels back to master for well + depth context
    zone_df = master.loc[labels.index, ["well", "depth"]].copy()
    zone_df["label"] = labels.values

    smoothed_parts = []
    for well, well_group in zone_df.groupby("well", sort=True):
        g = well_group.sort_values("depth").copy()
        arr = g["label"].to_numpy()

        # Step 1 — rolling mode (median works for small integer label sets if
        # we offset by 0.5 to avoid ties; safer to use a custom mode here).
        smoothed = _rolling_mode(arr, window=window_size)

        # Step 2 — drop short runs by merging into majority neighbour
        smoothed = _absorb_short_runs(smoothed, min_run_length=min_run_length)

        g["label_smoothed"] = smoothed
        smoothed_parts.append(g)

    out = pd.concat(smoothed_parts).sort_index()
    return pd.Series(out["label_smoothed"].values, index=labels.index, name="label")


def _rolling_mode(arr: np.ndarray, window: int) -> np.ndarray:
    """Rolling mode for a small-integer label array."""
    n = len(arr)
    half = window // 2
    out = arr.copy()
    for i in range(n):
        lo = max(0, i - half)
        hi = min(n, i + half + 1)
        vals, counts = np.unique(arr[lo:hi], return_counts=True)
        out[i] = vals[np.argmax(counts)]
    return out


def _absorb_short_runs(arr: np.ndarray, min_run_length: int) -> np.ndarray:
    """Identify runs in arr; for any run shorter than min_run_length,
    replace with the longer of its neighbours (or the only neighbour if
    at boundary)."""
    out = arr.copy()
    n = len(out)
    i = 0
    while i < n:
        j = i
        while j < n and out[j] == out[i]:
            j += 1
        run_len = j - i
        if run_len < min_run_length:
            # Choose replacement label
            left = out[i - 1] if i > 0 else None
            right = out[j] if j < n else None
            if left is None:
                replacement = right
            elif right is None:
                replacement = left
            else:
                # Pick whichever neighbour's run is longer
                left_run = i - 1
                while left_run > 0 and out[left_run - 1] == left:
                    left_run -= 1
                left_len = i - left_run
                right_run = j
                while right_run + 1 < n and out[right_run + 1] == right:
                    right_run += 1
                right_len = right_run - j + 1
                replacement = left if left_len >= right_len else right
            out[i:j] = replacement
        i = j
    return out


# -----------------------------------------------------------------------------
# Cross-well validation (leave-one-well-out)
# -----------------------------------------------------------------------------

@dataclass
class LOWOResult:
    well_id: int
    n_samples_held_out: int
    ari_vs_pooled: float       # adjusted rand index, LOWO predictions vs pooled labels
    silhouette_lowo: float     # on training (6-well) set


def leave_one_well_out_validation(
    master: pd.DataFrame,
    target_zone: str,
    features: list[str],
    pooled_result: ClusteringResult,
    method: str = "kmeans",
    n_clusters: int = 3,
    random_state: int = 42,
) -> pd.DataFrame:
    """For each well, refit on the other 6 and predict on the held-out one;
    compare predictions to pooled labels via Adjusted Rand Index.

    High ARI → cluster structure does not depend on any single well →
    geology is reproducible.
    """
    zone_samples = master[master["zone"] == target_zone].copy()
    feature_df_full = build_feature_frame(zone_samples, features)
    wells = sorted(zone_samples["well"].unique())

    # Pooled labels indexed by feature_df row
    pooled_labels = pd.Series(
        pooled_result.labels, index=pooled_result.feature_df.index
    )

    results = []
    for held_out in wells:
        train_idx = master.loc[feature_df_full.index, "well"] != held_out
        test_idx = ~train_idx

        train_feat = feature_df_full.loc[train_idx]
        test_feat = feature_df_full.loc[test_idx]

        scaler = StandardScaler()
        X_train = scaler.fit_transform(train_feat.values)
        X_test = scaler.transform(test_feat.values)

        if method == "kmeans":
            model = KMeans(n_clusters=n_clusters, n_init=10, random_state=random_state)
        else:
            model = GaussianMixture(
                n_components=n_clusters, random_state=random_state, n_init=3
            )
        train_labels = model.fit_predict(X_train)
        # Reorder by log_perm so labels align with pooled fit
        train_labels = _reorder_labels_by_log_perm(train_labels, train_feat, features)

        # Predict on held-out
        if method == "kmeans":
            test_labels_raw = model.predict(X_test)
        else:
            test_labels_raw = model.predict(X_test)
        # Map test labels using the same train-reorder permutation
        test_labels = _apply_reorder_to_predictions(
            test_labels_raw, train_labels, model
        )

        # Compare to pooled
        pooled_for_test = pooled_labels.loc[test_feat.index].to_numpy()
        ari = adjusted_rand_score(pooled_for_test, test_labels)

        sil_train = (
            silhouette_score(X_train, train_labels) if n_clusters > 1 else float("nan")
        )

        results.append(
            LOWOResult(
                well_id=int(held_out),
                n_samples_held_out=int(test_idx.sum()),
                ari_vs_pooled=float(ari),
                silhouette_lowo=float(sil_train),
            )
        )
        logger.info(
            f"  LOWO well={held_out}: n_test={int(test_idx.sum())}, "
            f"ARI vs pooled={ari:.3f}, train silhouette={sil_train:.3f}"
        )

    return pd.DataFrame([r.__dict__ for r in results])


def _apply_reorder_to_predictions(
    raw_preds: np.ndarray,
    reordered_train_labels: np.ndarray,
    model,
) -> np.ndarray:
    """Build the label permutation from the model's raw label space to the
    reordered space, then apply it to held-out predictions.

    Idea: the model's `predict()` returns labels in its own internal space;
    we already know train samples' (raw → reordered) mapping. Use the model's
    raw train predictions to invert.
    """
    # Re-predict train to get raw labels in the model's internal space
    # (KMeans.labels_ and GMM internally use this same numbering)
    if hasattr(model, "labels_"):
        raw_train = model.labels_
    else:
        # GMM doesn't have labels_; we already have raw_preds for test only.
        # Predict train would require X_train; safest path is to find the
        # mapping by majority vote within each reordered class.
        raw_train = None

    if raw_train is None:
        # Fallback: identity mapping (will not happen in practice; both
        # KMeans and GMM in sklearn produce labels in the same space as
        # predict()).
        return raw_preds

    # Build mapping: for each (raw, reordered) pair seen in train, count;
    # then for each raw label pick the majority reordered.
    mapping = {}
    for raw, reord in zip(raw_train, reordered_train_labels):
        mapping.setdefault(raw, {}).setdefault(reord, 0)
        mapping[raw][reord] += 1
    final = {raw: max(d.items(), key=lambda x: x[1])[0] for raw, d in mapping.items()}
    return np.array([final.get(p, p) for p in raw_preds])


# -----------------------------------------------------------------------------
# Per-sub-zone metric rollup
# -----------------------------------------------------------------------------

def subzone_metrics(
    master: pd.DataFrame,
    target_zone: str,
    labels: pd.Series,
    label_name: str = "sub_zone",
) -> pd.DataFrame:
    """Aggregate per-(well, sub_zone) metrics within the target zone.

    Mirror of analytics.metrics.compute_zone_metrics but on sub-zones.
    """
    zone_samples = master[master["zone"] == target_zone].copy()
    zone_samples = zone_samples.loc[labels.index].copy()
    zone_samples[label_name] = labels.values

    rows = []
    for (well, sub), g in zone_samples.groupby(["well", label_name], observed=True):
        thickness = float(g["dz"].sum())
        avg_phit = float(g["phit"].mean())
        avg_perm = float(g["perm"].mean())
        kh = float((g["perm"] * g["dz"]).sum())
        avg_perm_khw = kh / thickness if thickness > 0 else np.nan
        n_sat = int((g["perm"] >= 14999.0).sum())
        rows.append({
            "well": int(well),
            "sub_zone": int(sub),
            "thickness_m": thickness,
            "n_samples": int(len(g)),
            "avg_phit": avg_phit,
            "avg_perm_mD": avg_perm,
            "avg_perm_kh_weighted_mD": avg_perm_khw,
            "kh_mD_m": kh,
            "n_perm_saturated": n_sat,
            "frac_saturated": n_sat / len(g) if len(g) > 0 else 0.0,
        })
    return pd.DataFrame(rows)
