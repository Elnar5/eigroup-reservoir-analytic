# Executive Summary

**Reservoir Analytics — Beyond the Headline Numbers**

A petrophysical investigation of 18,167 depth samples across 7 wells
and 5 zones. Submitted in fulfilment of the eiGroup Associate Data
Scientist technical assessment.

**Author:** Elnar Babayev  ·  **Date:** 27 May 2026

---

## TL;DR — five findings, each backed by data

1. **A measurement anomaly shapes everything downstream.** 3,514 of
   18,167 samples (19.34%) report permeability of exactly 15,000 mD —
   the upper end of the documented valid range. Three pieces of
   statistical evidence point to this being a tool ceiling, not a
   physical maximum (log-normal distribution doesn't produce point
   masses; the spike sits exactly at the round upper limit; the
   saturated samples concentrate in Zone B). Under this interpretation,
   **every Zone B kh number is a conservative lower bound, not a point
   estimate.**

2. **Zone D is non-reservoir, robustly.** NTG never exceeds 29% across
   the entire 0.30–0.70 vsh cutoff sweep. The binding constraint is
   porosity (sub-1 mD perm), not shaliness. **Cutting vsh further
   would not change this conclusion.** Zone D should be bypassed.

3. **Zone C splits into three reproducible sub-zones.** Pooled
   K-Means clustering on 3,571 net samples produces three
   monotonically ordered quality tiers (poor / moderate / best).
   Leave-one-well-out ARI averaged across 7 folds: **0.991** — the
   structure is essentially invariant to which well is withheld.
   **Sub-zone 2 (best tier) holds 48% of Zone C's kh in just 29% of
   its thickness** — a natural drilling target.

4. **Zone E is the largest defensible kh in the field at 1.2 M mD·m.**
   Zone B's 10.7 M headline is larger, but its lower-bound nature
   makes Zone E the safer basis for downstream flow calculations.
   Only 1.4% of Zone E samples are saturated.

5. **Cross-well kh rankings are partly an instrument artefact.**
   Well 7 leads on visible kh (2.59 M mD·m) but is 30% saturated.
   Under the tool-ceiling interpretation, the true gap to the rest
   of the field is larger than the table shows.

---

## Method audit

### What we built

| Part | Deliverable | Output |
|------|-------------|--------|
| **A** | Data loading, joining, quality assessment | 18,167-row master table; 3 quality issues discovered |
| **B** | Per-(well, zone) metrics | 35 rows × 12 metrics (5 required + 7 bonus) |
| **C.1** | Cutoff sensitivity sweep | 315 results across 9 vsh cutoffs + bootstrap CI |
| **C.2** | Field-level views | 6 charts — heatmap, stacked bar, crossplot, sensitivity, Lorenz, box plot |
| **D** | Sub-zone definition | Zone C clustered into 3 reproducible sub-zones; Zone B failed informatively |

### Engineering reliability

- **133 pytest tests**, all passing
- **79% overall coverage**, 96-100% on hot paths (metrics, sensitivity,
  clustering, visualization)
- Single-command reproducibility per part via the `src.cli` interface
- All intermediates cached to parquet; all deliverables versioned in
  `outputs/reports/`

---

## Three quality issues found in Part A — all by design

| Issue | Scope | How we handled it |
|-------|------:|-------------------|
| Tool saturation at 15,000 mD | 3,514 samples (19.34%) | Kept, flagged with boolean column, surfaced count alongside every downstream kh number |
| Well 3 NaN porosity | 78 samples (0.43%) | Excluded from net mask; counted separately in `n_phit_nan` |
| Well 5 sampling step (0.5 m vs 0.2 m elsewhere) | All well-5 samples | Per-well dz computation; every metric is depth-weighted |

---

## Volume estimates with confidence flags

| Zone | NTG | Total kh (mD·m) | Saturation | Reading |
|------|----:|----------------:|----------:|---------|
| **A** | 0.63 | 267 K | 0% | Clean baseline. NTG range across cutoffs: 0.15–0.94 — cutoff-sensitive |
| **B** | 0.93 | **10.7 M** | **99.85%** | Headline number; most likely a lower bound under saturation interpretation |
| **C** | 0.84 | 680 K | 0.4% | Heterogeneous (Lorenz 0.65); 3 sub-zones identified in Part D |
| **D** | 0.10 | 42 | 0% | Tight rock. NTG ≤ 29% at any cutoff — robust failure |
| **E** | 0.70 | 1.2 M | 1.4% | **Most defensible high-perm zone in the field** |

---

## Robust findings vs cutoff-driven findings

Five findings hold across every cutoff tested (0.30–0.70):

- Zone B dominates field flow capacity
- Zone D is non-reservoir
- Well 7 leads on visible kh
- Zone E is the most defensible high-perm zone
- The saturation pattern is invariant to cutoff (it's a tool feature,
  not a methodology artefact)

Three findings depend on the cutoff and should be reported as ranges:

- Zone A's NTG (range 0.15–0.94)
- Zone C's NTG (range 0.38–0.94)
- Zone E's NTG (range 0.32–0.89)

---

## Method awareness — Zone B clustering failed informatively

I attempted the same K-Means clustering on Zone B as a controlled
comparison. The result fails in a specific, predictable way:
sub-zones 1 and 2 have log_perm centroids of **4.175938** and
**4.176091** — a difference of 0.00015. In raw permeability units,
that's the difference between 14,985 mD and 14,995 mD, well inside
tool quantization noise.

The clustering "succeeded" statistically (LOWO ARI 0.991) but
produced two sub-zones that are indistinguishable in their key flow
property. Under the saturation interpretation, this is exactly the
predicted failure mode — the tool can't see heterogeneity above the
ceiling. Under the alternative interpretation, Zone B is genuinely
homogeneous in perm. The clustering output alone cannot distinguish
between these two readings.

**The lesson:** internal-consistency metrics like silhouette and ARI
can be misleadingly high on features that have been censored. A
production workflow should always inspect centroid separation in
domain units, not only the algorithm's quality score.

---

## What better validation would require

The internal validation here (silhouette, LOWO ARI, multi-algorithm
cross-check, monotone-feature ordering) is the best possible without
external data. Three external sources would lift the conclusions from
internal-consistency to true external validation:

1. **Core descriptions and core permeability** — gold standard.
   Resolves the saturation-vs-physical-max question directly and
   tests whether sub-zone boundaries correspond to observable
   lithology changes.

2. **Production logs (PLT / spinner)** — operational validation.
   Tests whether the predicted "best" sub-zone actually produces
   more per metre.

3. **Pressure transient data** — calibrates magnitude, not just
   ranking. Provides an analytic check on cluster-summed kh.

---

## Reading order for the full submission

For a reviewer with limited time:

1. **`outputs/dashboard.html`** — all 9 chart sections on one page (5 min)
2. **`outputs/reports/part_c_walkthrough.md`** — sensitivity + 6 field views (15 min)
3. **`outputs/reports/part_d_walkthrough.md`** — clustering + all case answers (15 min)
4. **`outputs/reports/part_a_walkthrough.md`** — data + saturation discovery (10 min)
5. **`outputs/reports/part_b_walkthrough.md`** — 5 zone signatures (10 min)
6. **`presentation/eigroup_reservoir_analytics.pptx`** — 26-slide deck

Technical reference documents remain in `outputs/reports/` for any
detailed cross-checking.

---

*All numbers in this summary are computed from real data and
reproducible via the pipeline in `src/`. Raw inputs in `data/raw/`,
processed outputs in `outputs/`.*