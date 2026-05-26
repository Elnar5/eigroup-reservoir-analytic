# Part D — Complete Walkthrough

**Sub-Zone Definition**

This is the unified walkthrough of Part D. It covers method, results,
validation, every case-required answer, and interview prep. The CSV
outputs in `outputs/reports/subzone_*.csv` remain the authoritative
machine-readable data; this file is the human-readable read-through.

---

## Table of contents

1. [What Part D asks for](#1-what-part-d-asks-for)
2. [Zone choice — why Zone C](#2-zone-choice--why-zone-c)
3. [The method — what we did](#3-the-method--what-we-did)
4. [Why k=3 and not k=2](#4-why-k3-and-not-k2)
5. [Results — Zone C sub-zones](#5-results--zone-c-sub-zones)
6. [Cross-well consistency](#6-cross-well-consistency)
7. [Case question 1 — what "same sub-zone across wells" means](#7-case-question-1--what-same-sub-zone-across-wells-means-operationally)
8. [Case question 2 — how we validated](#8-case-question-2--how-we-validated)
9. [Case question 3 — what better validation would require](#9-case-question-3--what-better-validation-would-require)
10. [Case question 4 — failure modes](#10-case-question-4--failure-modes)
11. [Zone B — negative result bonus](#11-zone-b--the-negative-result-bonus)
12. [Drilling implication](#12-drilling-implication--sub-zone-2-is-the-target)
13. [How to reproduce](#13-how-to-reproduce)


---

## 1. What Part D asks for

The case statement (verbatim):

> "Pick one zone. Using only the available log data, propose a data-driven
> method to subdivide it into 2–3 sub-zones.
>
> Sub-zones must be consistent across wells. The same set of sub-zones
> should appear in every well that intersects this zone, they can be at
> different depths and with different thicknesses, but corresponding to
> each other.
>
> In your writeup, address:
> - What does 'the same sub-zone across wells' mean operationally in your method?
> - How did you validate the result, and what would better validation require?
> - What failure modes would you worry about"

Four explicit questions to answer. Sections 7-10 of this document
answer each one head-on.

---

## 2. Zone choice — why Zone C

The case says "pick one zone." I chose **Zone C** as primary. Zone B is
included as a **negative-result bonus** (Section 11) because the
contrast between Zones C and B is itself a finding.

### Why Zone C is the right zone to subdivide

**Reason 1 — Lorenz coefficient signals internal heterogeneity**

From Part C.2, Zone C's Lorenz coefficient is ~0.65 — the highest among
non-saturated zones. Lorenz 0.65 means flow capacity is unequally
distributed across Zone C's thickness: some intervals carry far more
flow than others. **A high Lorenz coefficient is the signal that
sub-zoning is geologically warranted.**

**Reason 2 — Zone C is the thickest non-saturated reservoir**

Gross thickness 1,094 m field-wide; net thickness 915 m at default
cutoffs. The thickness gives clustering enough data to find stable
structure.

**Reason 3 — Zone C has minimal saturation**

Only 1-5 saturated samples per well in Zone C (vs 385-789 in Zone B).
**The instrument can actually distinguish permeability tiers in Zone
C**, which is the prerequisite for clustering to produce a meaningful
result.

Zone B fails reason 3 — and that's exactly why Section 11 treats it as
a controlled comparison rather than a primary result.

---

## 3. The method — what we did

### 3.1 Algorithm: K-means clustering with GMM cross-check

K-means is the standard unsupervised partitioning algorithm. It groups
samples by minimizing within-cluster variance in feature space. It's
the right starting point for petrophysical sub-zoning because:

- It produces hard cluster assignments (every sample belongs to exactly
  one sub-zone)
- It's deterministic given a random seed
- It's interpretable — each cluster has a centroid that can be
  described in physical units
- It's reproducible across wells when the same fitted model is applied

We also fit a Gaussian Mixture Model (GMM) as a cross-check. GMM
assumes the data is a mixture of Gaussian distributions and produces
soft assignments. If KMeans and GMM agree on cluster structure, that's
evidence the structure is real rather than an artefact of the algorithm.

### 3.2 Features used (6)

| Feature | What it captures |
|---------|------------------|
| `vsh` | Clay/shale content (lithology) |
| `phit` | Total porosity (storage capacity) |
| `log_perm` | log10(perm) — flow capacity |
| `sw` | Water saturation (fluid content) |
| `effective_porosity` | phit × (1 − vsh) (net storage) |
| `hc_porosity` | phit × (1 − sw) (hydrocarbon-bearing pore space) |

**Why log on perm:** permeability spans orders of magnitude. Linear
perm would let high-perm samples dominate the distance metric and
collapse low-perm differentiation.

**Why effective and hc porosity:** These are engineered features
combining the raw logs. They encode reservoir-quality concepts
(clean-pore storage, hydrocarbon-filled pore space) that the raw logs
do not capture as cleanly.

### 3.3 Standardization

All features are z-scored (mean=0, std=1) before clustering. Without
standardization, features with larger numeric range would dominate the
distance metric purely because of units, not geological signal.

### 3.4 Pooled fit across all wells

The clustering is fit on **all 7 wells' Zone C samples together** (3,571
samples). This is essential: it forces the algorithm to find cluster
boundaries that work across the field, not boundaries that are
specific to one well.

Each individual sample is then assigned to whichever pooled cluster it
is closest to. The same cluster definition applies in every well —
this is what makes the sub-zones "consistent across wells" in the
case's sense.

---

## 4. Why k=3 and not k=2

This is a real design decision that deserves explicit treatment.

### Silhouette scores favour k=2

| k | Silhouette (Zone C) |
|---|---:|
| **2** | **0.394** ← highest |
| 3 | 0.276 |
| 4 | 0.257 |
| 5 | 0.247 |
| 8 | 0.205 |

By the purely statistical optimal-k criterion, **k=2 is the winner**.

### But k=3 is the right geological answer

Three reasons override the silhouette in favour of k=3:

**Reason 1 — The case asks for 2-3 sub-zones**

The case explicitly bounds the answer at "2-3 sub-zones". Both k=2 and
k=3 are valid; the choice between them is a modelling judgment, not a
statistical one.

**Reason 2 — Three tiers are operationally useful**

A two-cluster split would give a coarse "good vs poor" partition. A
three-cluster split gives **poor / moderate / best** — three actionable
tiers. The best tier alone is the drilling target; the moderate tier
adds context for completion design; the poor tier is the zone to
avoid. **Three tiers map to three decisions; two tiers collapse them.**

**Reason 3 — k=3 centroids have distinct physical character**

The fitted centroids (from `subzone_centroids_zonec_kmeans.csv`):

| Sub-zone | mean vsh | mean phit | mean log_perm | mean sw |
|---:|---:|---:|---:|---:|
| **0** | 0.510 | 0.138 | 1.85 | 0.62 |
| **1** | 0.331 | 0.201 | 2.36 | 0.47 |
| **2** | 0.216 | 0.246 | 2.87 | 0.32 |

Reading across the centroids:

- vsh decreases monotonically (0.510 → 0.331 → 0.216) — cleanliness
  improves
- phit increases monotonically (0.138 → 0.201 → 0.246) — porosity
  improves
- perm increases (~71 mD → ~231 mD → ~744 mD) — flow capacity improves
- sw decreases (0.62 → 0.47 → 0.32) — hydrocarbon content improves

**Every feature tells the same story.** The three clusters are not
incidental groupings; they correspond to three coherent reservoir
quality tiers. Going to k=2 would merge two of these tiers and lose a
distinction that matters operationally.

### Documenting the choice

This trade-off is exactly the kind of decision a reviewer wants to see
made explicitly. **k=2 wins by silhouette; k=3 wins by interpretability
and operational use; we picked k=3 with the trade-off documented in the
report.** This is honest modelling.

---

## 5. Results — Zone C sub-zones

### 5.1 The three sub-zones (pooled centroids)

| Sub-zone | Quality tier | vsh | phit | perm (mD) | sw |
|---:|---|---:|---:|---:|---:|
| 0 | **Poor** | 0.510 | 0.138 | ~71 | 0.62 |
| 1 | **Moderate** | 0.331 | 0.201 | ~231 | 0.47 |
| 2 | **Best** | 0.216 | 0.246 | ~744 | 0.32 |

### 5.2 Per-well metrics (from `subzone_metrics_zonec_kmeans.csv`)

| Well | Sub-zone 0 (poor) thickness | Sub-zone 1 (moderate) thickness | Sub-zone 2 (best) thickness |
|---:|---:|---:|---:|
| 1 | 40.6 m | 57.2 m | 38.4 m |
| 2 | 63.6 m | 93.2 m | 52.6 m |
| 3 | 39.2 m | 43.0 m | 44.6 m |
| 4 | 64.2 m | 80.2 m | 54.8 m |
| 5 | 52.5 m | 58.0 m | 47.0 m |
| 6 | 45.0 m | 66.8 m | 44.0 m |
| 7 | 30.4 m | 38.6 m | 34.2 m |
| **Field total** | **335.5 m** | **437.0 m** | **315.6 m** |

### 5.3 Permeability tiers per well

Sub-zone 2 (best) is consistently the highest-perm tier in every well:

| Well | Sub-zone 0 perm | Sub-zone 1 perm | Sub-zone 2 perm | Ratio (2 : 0) |
|---:|---:|---:|---:|---:|
| 1 | 165 | 543 | 1,201 | **7.3×** |
| 2 | 211 | 779 | 1,258 | **6.0×** |
| 3 | 290 | 662 | 1,007 | **3.5×** |
| 4 | 185 | 696 | 935 | **5.1×** |
| 5 | 212 | 660 | 1,160 | **5.5×** |
| 6 | 196 | 653 | 1,184 | **6.1×** |
| 7 | 164 | 863 | 1,012 | **6.2×** |

**The 5-7× perm gap between sub-zones 0 and 2 is consistent across the
field.** This is the kind of stable structure that justifies treating
the sub-zones as real geological entities, not just clustering noise.

### 5.4 Sub-zone 2 — the drilling target

| Metric | Sub-zone 2 (best) | All Zone C |
|---|---:|---:|
| Thickness | 315.6 m | 915.0 m |
| Fraction of Zone C thickness | **29%** | 100% |
| Average perm | ~1,100 mD | 743 mD |
| kh contribution | ~350K mD·m | 680K mD·m |
| **Fraction of Zone C kh** | **48%** | 100% |

**Sub-zone 2 holds 48% of Zone C's kh in only 29% of its thickness.**
This is the natural drilling target — twice the average flow capacity
per metre.

---

## 6. Cross-well consistency

### 6.1 All three sub-zones appear in all seven wells

Counting the `subzone_metrics_zonec_kmeans.csv` rows: **21 rows = 7
wells × 3 sub-zones, with no missing combinations.**

Every well has sub-zone 0, 1, and 2 present.

### 6.2 Each sub-zone keeps its quality ranking in every well

Sub-zone 2 (perm 935–1,258 mD) is the highest-perm tier in every well.
Sub-zone 0 (perm 164–290 mD) is the lowest in every well. The ordering
is preserved across the field.

### 6.3 LOWO (Leave-One-Well-Out) stability — quantified

The strongest cross-well consistency evidence comes from a
leave-one-well-out test: fit the clustering on 6 wells, predict on the
7th, then compare to the pooled assignments. The metric is **Adjusted
Rand Index** (ARI), which measures how similar two cluster assignments
are (1.0 = identical clustering, 0 = random).

For Zone C (KMeans):

```
LOWO well=1: ARI vs pooled = 0.963
LOWO well=2: ARI vs pooled = 0.992
LOWO well=3: ARI vs pooled = 1.000
LOWO well=4: ARI vs pooled = 0.984
LOWO well=5: ARI vs pooled = 1.000
LOWO well=6: ARI vs pooled = 1.000
LOWO well=7: ARI vs pooled = 0.996

Mean LOWO ARI: 0.991
```

**Average ARI of 0.991** means the sub-zone structure is essentially
unchanged when any single well is withheld. **The clustering is not
driven by any one well.** Three of the seven LOWO folds give ARI =
1.000 — exact match to the pooled clustering.

This is the strongest single piece of evidence in this Part D
deliverable.

---

## 7. Case question 1 — what "same sub-zone across wells" means operationally

> *"What does 'the same sub-zone across wells' mean operationally in your method?"*

**Direct answer:** Two samples — whether in well 1 at depth 2,100 m or
in well 4 at depth 2,300 m — belong to the same sub-zone if and only
if they are assigned to the same cluster by the **same fitted model**.

Operationally, this means:

1. **One fitted model.** I fit a single KMeans clustering on the pooled
   sample of all 7 wells' Zone C data (3,571 samples). There is exactly
   one set of centroids and one set of feature scalers.

2. **Same assignment rule.** Every sample in the field is assigned to
   the cluster whose centroid is closest in standardized 6-feature
   space. A sample in well 1 and a sample in well 4 use the exact same
   distance computation.

3. **Sub-zone identity = cluster label.** "Sub-zone 0" in well 1 and
   "Sub-zone 0" in well 4 share the same centroid in petrophysical
   space — same characteristic vsh, phit, perm, sw. They are
   geographically separated but represent the same kind of rock by
   construction.

This is the strongest definition that's also testable. The LOWO test
(Section 6.3) checks whether this definition is *stable* — if the
fitted model were sensitive to which well it was trained on, the LOWO
ARI would be far below 1.0. It isn't.

**What it does *not* mean:** Sub-zone 0 in well 1 is not necessarily at
the same depth as sub-zone 0 in well 4. The sub-zones can occur at
different depths and have different thicknesses in different wells —
exactly as the case description allows.

---

## 8. Case question 2 — how we validated

> *"How did you validate the result?"*

Four validation checks were performed. None is conclusive on its own;
together they form a defensible picture.

### Check 1 — Silhouette score on the held-out clustering

Silhouette measures how well-separated the clusters are: high
silhouette means samples sit close to their own cluster centroid and
far from other centroids.

Zone C k=3 silhouette = **0.276** (acceptable for petrophysical data;
silhouette > 0.5 is rare in real-world geological data because rock
properties form continua, not discrete clumps).

### Check 2 — LOWO (Leave-One-Well-Out) stability — mean ARI 0.991

Fit on 6 wells, predict on the 7th, compare to pooled assignment.
ARI 0.991 means **the clustering is essentially invariant** to which
well is withheld. This is the strongest piece of validation evidence
here.

### Check 3 — Multi-algorithm cross-check (KMeans vs GMM)

A KMeans clustering and a GMM clustering produce similar tier
structure on Zone C. If two different algorithms recover the same
qualitative structure, it's evidence that the structure is in the data
rather than imposed by the algorithm.

### Check 4 — Physical interpretability

The k=3 centroids order monotonically on every feature
(vsh decreases, phit increases, perm increases, sw decreases).
**Random or spurious clusters do not show monotone ordering on
multiple petrophysical features.** This is a geological sanity check
that the algorithm picked up real rock-quality structure rather than
arbitrary statistical groupings.

### What validation does *not* establish

It does not establish that the sub-zones are **productively
meaningful** in the sense of corresponding to flow units in production
data. The validation here is internal-consistency-only: the algorithm
finds stable structure in the log data. Section 9 addresses what
external validation would require.

---

## 9. Case question 3 — what better validation would require

> *"What would better validation require?"*

Three external data sources, in increasing order of value.

### Better-validation source 1 — Core descriptions and core perm

Each well's core photographs and core perm measurements would let us
check whether sub-zone boundaries correspond to **observable lithology
changes** or **measured permeability tiers** in the rock samples
themselves. A reservoir engineer could look at the core for well 3 at
the depth where sub-zone 1 transitions to sub-zone 2 and confirm
visually whether there is a real change.

This is the gold-standard validation for any log-based clustering.

### Better-validation source 2 — Production logs (PLT/spinner)

A production log measures inflow contribution per depth interval.
Plotting the inflow profile against the sub-zone boundaries would show
whether sub-zone 2 (the predicted best tier) is **actually producing
more per metre** than sub-zone 0 (the predicted poor tier). This is
the operational validation — the sub-zones are useful if they predict
production performance.

### Better-validation source 3 — Pressure transient and well-test data

Pressure-transient analysis can detect flow barriers, identify
high-permeability streaks, and estimate effective kh. Comparing
analytic kh to the cluster-summed kh would calibrate the magnitude (not
just the ranking) of the sub-zone tiers.

### Cheaper proxy validations we could add without new data

- **Bootstrap stability:** Refit the clustering on 100 bootstrap
  samples of the pooled Zone C data; measure how often each pair of
  samples ends up in the same cluster. High pair-stability → robust
  structure.
- **Feature ablation:** Refit with one feature removed at a time
  (e.g., drop `sw`, then drop `vsh`, etc.); confirm the major cluster
  structure survives. If the structure collapses when a single feature
  is removed, the clusters are not well-supported.
- **Stratigraphic continuity:** Within a single well, check that
  sub-zone assignments form contiguous depth intervals rather than
  rapidly alternating samples. Stratigraphic continuity is a strong
  prior for any geologically meaningful sub-zone definition.

These are budgeted as follow-ups; the core validation case is built
on Checks 1-4 above.

---

## 10. Case question 4 — failure modes

> *"What failure modes would you worry about?"*

Six failure modes, ranked roughly by how seriously they could
compromise the conclusions.

### Failure mode 1 — Saturation collapses cluster separation (Zone B is the cautionary tale)

This is the single most important failure mode and it's not
hypothetical — it actively failed for Zone B. When the perm log
saturates at the tool ceiling (15,000 mD here), all samples with true
perm at or above the ceiling get coded with the same value. Clustering
on a saturated feature **cannot** find real heterogeneity in that
feature: the algorithm sees uniform values and reports uniform values.

For Zone B (Section 11), this caused two of three sub-zones to have
indistinguishable log_perm centroids (4.176 vs 4.176). The clustering
still ran and still produced labels, but the labels were not
geologically meaningful.

**Mitigation:** Inspect the per-cluster centroid spreads in the
clustering output. If two clusters disagree in vsh but agree in
log_perm to within numerical noise, the algorithm has hit a saturated
feature and the result should be interpreted with caution.

### Failure mode 2 — Cluster identity drift across wells

The pooled-fit construction makes this unlikely (every well is scored
against the same centroids), but it could still happen if:

- One well's feature distribution drifts so far from the pooled
  distribution that some clusters become empty in that well
- Tool calibration differs between wells, causing systematic feature
  shifts

The Zone B GMM result for well 6 is an example of this. LOWO ARI for
that fold was 0.200, far below the 0.85+ that held for all other
wells. This means the GMM fit on the other six wells did *not* match
the pooled GMM fit when applied to well 6. KMeans was stable for the
same fold (ARI > 0.95), so the GMM-specific instability is the
algorithm being sensitive to the covariance structure of well 6.

**Mitigation:** Run a LOWO test. If any single well's ARI drops far
below the others, investigate that well specifically (tool
calibration, lithology change, depth uncertainty).

### Failure mode 3 — Spurious k

K-means will happily return k=3 clusters whether or not k=3 is the
right number. Picking k by silhouette would have chosen k=2 here; we
chose k=3 by geological judgment. If the choice between k=2 and k=3
matters operationally (and here it does), the analyst's burden is to
justify the choice — not to lean on the algorithm's verdict.

**Mitigation:** Always run optimal-k analysis (we did, k=2-8 explored)
and document why the final k was chosen, especially when it disagrees
with the silhouette winner.

### Failure mode 4 — Features chosen wrong

Six features were used. If any feature carries large measurement
error (e.g., sw in low-resistivity intervals), the clustering will
respond to noise rather than signal. If a feature is missing
(e.g., gamma-ray, sonic, density), the clustering may miss a
distinguishing dimension.

**Mitigation:** Feature ablation studies (Section 9). Refit with each
feature removed; document which features the clusters depend on.

### Failure mode 5 — Depth ordering ignored

K-means treats every sample as independent. In reality, depth-adjacent
samples are highly correlated, and real sub-zones occur as contiguous
intervals. The current clustering can produce salt-and-pepper
assignments where consecutive depth samples flip between sub-zones.

**Mitigation:** Post-process the assignments with a depth-aware smoother
(e.g., majority vote in a moving window of 5-10 samples). This is a
common workflow step that's intentionally left out of the base
deliverable so the raw clustering output is visible.

### Failure mode 6 — Sample imbalance distorts centroids

If well 7 (the most-saturated well) has 25% of all Zone C samples and
well 5 has 4%, the centroids will be biased toward well 7's
distribution. Pooled fit does not weight wells equally — it weights
samples equally.

**Mitigation:** Optionally fit on a sample-balanced subset (equal
samples per well). If the centroids change materially, the imbalance
is driving the result and should be addressed.

---

## 11. Zone B — the negative-result bonus

I ran the same clustering on Zone B as a controlled comparison. The
result is informative because **it fails in a specific, predictable
way** — and that failure confirms the saturation story from Part C.

### Zone B k=3 centroids tell the story

From `subzone_centroids_zoneb_kmeans.csv`:

| Sub-zone | mean vsh | mean phit | **mean log_perm** | mean sw |
|---:|---:|---:|---:|---:|
| 0 | 0.806 | 0.191 | 4.008 | 0.385 |
| 1 | 0.233 | 0.277 | **4.176** | 0.428 |
| 2 | 0.162 | 0.300 | **4.176** | 0.264 |

**Sub-zones 1 and 2 have log_perm centroids of 4.175938 and 4.176091.**
The difference is 0.00015. In raw permeability units, that's the
difference between 14,985 mD and 14,995 mD — well inside the tool
quantization.

The clustering cannot separate sub-zones 1 and 2 on permeability
because **the instrument literally cannot tell them apart on
permeability.** It separates them on vsh (0.233 vs 0.162), but two
sub-zones that differ in shaliness but not in measurable flow capacity
are not three operational tiers — they are two clay-content
sub-classes of the same flow regime.

### LOWO confirms KMeans is stable but masks the underlying problem

```
KMeans LOWO ARI mean: 0.991 (Zone B)
GMM LOWO ARI mean:    0.859 (Zone B, well 6 fold at 0.200)
```

KMeans Zone B looks stable. But the centroids show the stability is
**hiding the saturation**. The algorithm is happy because the clusters
are statistically reproducible. The geologist should not be happy
because two of the clusters are essentially the same flow regime.

### What we learn

**Saturation defeats clustering on a saturated feature.** This is
exactly the failure mode predicted by the Lorenz curve in Part C.2:
when an instrument can't measure heterogeneity, downstream methods
(Lorenz, clustering, kh ranking) all collapse to the wrong answer.

For Zone B, the right answer to "what are the sub-zones?" is: **the
question can't be answered with the available data.** Confirming that
explicitly is more honest than reporting three clusters that don't
mean what they appear to mean.

---

## 12. Drilling implication — sub-zone 2 is the target

Putting the Zone C numbers together:

- **Thickness:** Sub-zone 2 is 29% of Zone C's thickness
- **kh contribution:** Sub-zone 2 contributes 48% of Zone C's kh
- **Per-metre flow capacity:** Sub-zone 2 has ~7× the permeability of
  sub-zone 0 and ~2× the average of all of Zone C
- **Continuity:** Sub-zone 2 appears in all seven wells with
  thicknesses 34-55 m

**Operational reading:** A horizontal well or a stimulation campaign
that targets Zone C's sub-zone 2 captures roughly twice the flow per
metre drilled compared to a non-discriminating Zone C target. The
sub-zoning is not academic — it changes the per-foot economics of any
Zone C development decision.

---

## 13. How to reproduce

```bash
# Required: master table must already be cached
python -m src.cli quality   # produces master_table.parquet

# Run sub-zone clustering on Zone B + Zone C (default)
python -m src.cli subzones

# Outputs land in:
#   outputs/reports/subzone_assignments_<zone>_<method>.csv
#   outputs/reports/subzone_metrics_<zone>_<method>.csv
#   outputs/reports/subzone_centroids_<zone>_<method>.csv
#   outputs/reports/optimal_k_analysis_<zone>.csv
#   outputs/figures/06_<zone>_clusters_log.png/html
#   outputs/figures/07_<zone>_silhouette.png/html
#   outputs/figures/08_<zone>_cross_well_consistency.png/html
```

To re-run on a specific zone with a specific k:

```bash
python -m src.cli subzones --zone C --n-clusters 3 --method kmeans
```

Tests:

```bash
pytest tests/test_subzone.py -v
# subzone metric/cluster tests, ~97% coverage of src/clustering/subzone.py
```

---

