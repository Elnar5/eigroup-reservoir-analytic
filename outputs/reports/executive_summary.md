# Executive Summary

**Project:** Reservoir-volume characterization and sub-zone clustering across 7 wells in a single field.
**Submitted by:** Kamil Muradli, Associate Data Scientist candidate.
**Date:** 2026-05-27.

---

## TL;DR — five decisions this analysis supports

1. **Zone B is the dominant flow interval (kh ≈ 10.7 M mD·m, NTG 93%), but its
   permeability is right-censored** — 88% of net samples sit at the 15,000 mD
   tool cap. All Zone B kh-based numbers are **conservative lower bounds**, not
   best estimates.

2. **Zone D should be bypassed.** Net-to-gross never exceeds 32% even at the
   loosest cutoff (vsh ≤ 0.7). The failure is on porosity, not shale content
   — it's tight rock.

3. **Volume estimates differ in robustness across zones.** Zone B's NTG is
   stable to ±13% across the entire 0.30–0.70 vsh cutoff sweep; Zone A's
   varies by ±80%. Field strategy should commit to a calibrated cutoff and
   document the choice — especially for Zones A and C.

4. **Within Zone C, three sub-zones reproduce across all 7 wells** (LOWO ARI
   0.97). Sub-zone 2 (perm ≈ 1,100 mD) holds **48% of Zone C flow capacity in
   29% of its thickness** — a natural drilling target.

5. **Well-to-well kh ranking is partly an instrument artefact.** Well 7 leads
   on kh (2.59 M mD·m) but 30% of its samples are tool-capped. A
   saturation-weighted ranking would change the top three.

---

## Method audit

### What we did

- **Part A** — Joined 18,167 well-log samples from 7 wells to 35 zone
  intervals via depth-asof merge. Per-well dz handled mixed sampling (well_5
  is 0.5 m; others 0.2 m).

- **Part B** — Computed 12 metrics per (well, zone): gross/net thickness,
  NTG, avg phit, arithmetic and kh-weighted avg perm, kh, Lorenz coefficient,
  plus diagnostic counts (NaN porosity, saturated permeability).

- **Part C.1** — Swept vsh cutoff from 0.30 to 0.70 (step 0.05) → 315 metric
  rows. Bootstrap CI on kh (200 resamples). Knee detection per (well, zone).

- **Part C.2** — Five field-view charts: kh heatmap, stacked bar per well,
  porosity-permeability cross-plot, NTG sensitivity curves, Lorenz curves.

- **Part D** — Pooled K-Means + GMM clustering on Zone B (failed, instructive)
  and Zone C (succeeded). Leave-one-well-out validation via Adjusted Rand
  Index. Sample-level smoothing (rolling mode, min run = 5).

### Three real-data issues caught in QC and flagged downstream

1. **Permeability tool saturation at 15,000 mD** — 14–30% of every well's
   samples. The fraction is highest in wells 1 and 7 (25–30%). We retain
   saturated samples in kh calculations (excluding them would systematically
   underestimate flow capacity) and surface the count alongside every
   downstream metric.

2. **NaN porosity in well_3** — 78 samples (4%) lack phit. These are excluded
   from net interval calculations but counted separately (`n_phit_nan`) so
   they never silently inflate net.

3. **Heterogeneous sampling step** — well_5 is logged at 0.5 m versus 0.2 m
   for the other six wells. dz is computed per well, so kh and net thickness
   handle mixed sampling correctly.

### Engineering reliability

- 105 unit + invariant tests, all green.
- Module test coverage: metrics 99%, sensitivity 96%, subzone 97%, field 100%,
  clustering 100%, joiner 97%, loader 92%.
- All pipeline steps reproducible via single-line CLI commands. Outputs
  versioned in `data/processed/` (parquet) and `outputs/reports/` (CSV).

---

## Risk-flagged volume estimates

| Zone | NTG (default cutoff) | kh field total | Confidence | Risk note |
|------|----------------------|------------------|------------|-----------|
| B    | 0.93                 | 10.7 M           | **High in shape, low in magnitude** | 88% tool-capped — kh is a lower bound. NTG itself is stable (Day 3 knee at 0.35) |
| C    | 0.84                 | 0.68 M           | High      | <1% saturation, real Lorenz=0.65, clean clustering |
| E    | 0.70                 | 1.20 M           | Medium    | ~5% saturation, moderate Lorenz=0.52 |
| A    | 0.63                 | 0.27 M           | Medium    | NTG highly sensitive to cutoff (range 0.74-0.81), needs calibration |
| D    | 0.10                 | 42               | **Bypass — not reservoir** | NTG never exceeds 32% at any cutoff |

**Operational recommendation:** Field volume calculations should report
Zone B's kh with an explicit "**conservative — saturation-limited**" tag,
not as a point estimate. Zone C should be split into the three sub-zones
identified in Part D.

---

## Drilling target — Zone C sub-zone 2

Pooled K-Means clustering on Zone C (vsh, phit, log₁₀perm, sw, derived
porosity features) yields three reproducible sub-zones:

| Sub-zone | Avg perm | Avg phit | Total thickness | Total kh | % of Zone C kh |
|----------|------------|----------|------------------|------------|------------------|
| 0 (worst) | ~200 mD  | 0.140    | 335.5 m          | 68 K       | 10% |
| 1 (mid)   | ~700 mD  | 0.206    | 437.0 m          | 303 K      | 42% |
| **2 (best)** | **~1,100 mD** | **0.230** | **315.6 m** | **350 K** | **48%** |

- Cross-well LOWO ARI: 0.95–0.99 across all 7 folds.
- Sub-zone 2 sits **consistently at the top of Zone C in every well**
  (typically 30–80 m shallower than sub-zone 1 base).
- Sub-zone 1 sits at the base; sub-zone 0 (tight) is sandwiched in the
  middle.

This is a **coarsening-upward (or quality-upward) signature** with a
tight middle, repeated identically across all 7 wells — a strong reproducible
reservoir architecture.

**Drilling target:** Sub-zone 2 (top of Zone C). Completion strategy should
focus perforations on this interval per well.

---

## Method awareness — why Zone B clustering "failed"

We initially attempted sub-zone clustering on Zone B (highest kh, highest
NTG, present in all wells). The clustering produced reproducible but
mathematically meaningless output: two sub-zones with **identical centroids**
(vsh 0.243 vs 0.233, log_perm 4.17 vs 4.16) because 96% of every sub-zone
is at the 15,000 mD tool cap.

**The high Adjusted Rand Index (0.97) was misleading:** the model was
reproducibly clustering noise, not geology.

We re-targeted clustering on Zone C, where saturation is negligible
(<1%), Lorenz heterogeneity is 0.65, and three lithology classes resolve
cleanly. This is the kind of method-aware diagnostic that a production
workflow should always include — high in-sample metrics do not guarantee
geological meaning.

---

## Caveats and out-of-scope items

- **Zone B kh is right-censored**, not point-estimated. The actual perm in
  saturated samples could be 30,000 mD or 100,000 mD — the tool cannot tell
  us. A production workflow would need:
  - Higher-dynamic-range permeability tool, or
  - Lab core measurements at saturated depths, or
  - A censored-regression model relating phit/vsh to uncapped perm.

- **Cutoffs are literature defaults** (vsh ≤ 0.5, phit ≥ 0.08). Production
  cutoffs should be calibrated to core measurements or production data.

- **No production data, no PVT, no seismic.** This analysis is well-log only.
  Cross-well geological correlation could refine the sub-zone interpretation
  if seismic horizon picks were available.

- **The Lorenz coefficient on saturated data is not meaningful.** Zone B's
  L=0.00 is an instrument artefact, not a geological signal — it's still
  worth reporting (visually striking) but should not enter a heterogeneity
  ranking.

---

*Submitted in fulfilment of the eiGroup LLC Associate Data Scientist
technical assessment. Full reproducible pipeline available in source tree;
72 unit tests in `tests/`, executive deliverables in `outputs/`.*
