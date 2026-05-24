# Presentation Slide Outline

**Target duration:** 20-25 minutes (14 slides × ~1.5 min each).
**Audience:** eiGroup interview panel — mix of technical and business.
**Style:** Each slide has 1 chart + 3-5 bullets + 1 takeaway line. Talk to the
chart, not the bullets.

---

## Slide 1 — Title

**Title:** Reservoir-volume characterization across 7 wells
**Subtitle:** Method, findings, and a defensible field strategy
**Bottom strip:** Kamil Muradli · eiGroup Associate Data Scientist assessment · May 2026

**Speaker notes (30 sec):**
> Good morning. I'll walk through the analysis in three layers — what I found
> in the data, what the analytics say about reservoir volumes, and where I
> think the field strategy should focus. I'll close with a method critique:
> one place clustering didn't work, and why that's a feature, not a bug.

---

## Slide 2 — Three real-data issues caught in QC

**Title:** Three findings that shape every downstream decision
**Visual:** Three icons or a 3-row bullet
**Bullets:**
- well_3 has 78 NaN porosity samples (4%) → excluded from net, counted
  separately so they never silently inflate volumes
- well_5 is logged at 0.5 m spacing; others at 0.2 m → dz computed per
  well, so kh is unaffected
- All 7 wells have **15-30% permeability samples at the 15,000 mD tool cap**
  → flagged on every metric; kh saturation count surfaces in every chart

**Takeaway line:** "The QC step is not paperwork — these three issues drive
the choice of every metric and the credibility of every number that follows."

**Speaker notes:**
> A common failure mode in this kind of analysis is treating the data as
> clean. I built three QC checks into the pipeline as separate functions,
> ran them on real data, and flagged what I found. Two are nuisance issues
> well_3's NaN porosity and well_5's coarser sampling. The third is the
> story: permeability tool saturation. We'll come back to this.

---

## Slide 3 — Per-zone metrics with two surprises

**Title:** Net-to-Gross tells the geological story
**Visual:** Chart 02 — stacked bar of kh per well, decomposed by zone
**Bullets:**
- Zone B dominates: 93% NTG, 10× the kh of any other zone
- Zone D has 10% NTG everywhere — tight rock, not reservoir
- Zone C is the silent second story (NTG 84%, 0.68 M kh)
- All 7 wells follow this pattern — geology is reproducible

**Takeaway line:** "Net-to-Gross by zone is more diagnostic than any single
permeability number."

**Speaker notes:**
> The stacked bar shows the same pattern in every well: Zone B is the bulk of
> the flow, but the other zones are not negligible. Zone C in particular is
> consistently 5-10% of total kh — important when we get to drilling targets.
> Zone D has essentially zero contribution.

---

## Slide 4 — Cutoff sensitivity tells us which volumes are brittle

**Title:** Reservoir-volume estimate stability across vsh cutoffs
**Visual:** Chart 04 — NTG sensitivity curves
**Bullets:**
- Zone B NTG: stable across the full sweep (range only 0.11)
- Zone A NTG: highly sensitive (0.15 → 0.95 across the sweep)
- All zones have their "knee" at vsh ≈ 0.35 (same in all 7 wells)
- The default cutoff (0.5) sits on the flat part of each curve — defensible

**Takeaway line:** "Zone B is the most defensible volume estimate in the
field — its NTG is stable across any realistic cutoff."

**Speaker notes:**
> I swept the vsh cutoff from 0.30 to 0.70 in steps of 0.05 and recomputed
> every metric. Zone B's curve is nearly flat — meaning the choice of cutoff
> barely affects the answer. Zone A's curve is steep — meaning small changes
> in the cutoff matter a lot for Zone A volumes.
>
> In production, this tells me which zones need careful cutoff calibration
> against core data, and which are robust to defaults.

---

## Slide 5 — When "homogeneous" is an instrument artefact

**Title:** Lorenz curves expose tool censoring
**Visual:** Chart 05 — Lorenz curves
**Bullets:**
- Zone C: L = 0.65 — genuinely heterogeneous, top 30% delivers 80% of kh
- Zone E: L = 0.52, Zone A: L = 0.46 — moderate heterogeneity
- **Zone B: L = 0.00 — but this is a tool artefact, not homogeneity**
- 88% of Zone B samples are at the 15,000 mD cap → Lorenz curve flattens
  into the 45° diagonal

**Takeaway line:** "The strongest signal of Zone B's saturation problem
isn't a number — it's a flat Lorenz curve."

**Speaker notes:**
> Lorenz coefficient is the standard reservoir-engineering measure of flow
> heterogeneity. Zero means homogeneous, one means a single sample carries
> all the flow. Most zones cluster in 0.4-0.65 — typical clastic
> heterogeneity.
>
> Zone B's L = 0.00 looks like a perfectly homogeneous reservoir. It isn't.
> When 88% of your samples are at the same value because that's the tool
> ceiling, you can't measure heterogeneity. The Lorenz curve here is a
> diagnostic of the *measurement*, not of the *rock*.

---

## Slide 6 — Why kh ranking can mislead well selection

**Title:** Saturation pollutes well rankings
**Visual:** Chart 01 — kh heatmap with saturation overlay (the ⚠ marks)
**Bullets:**
- well_7 ranks #1 by kh (2.59 M mD·m) — but 30% of its samples are tool-capped
- well_1 ranks #2 (2.27 M) — 25% tool-capped
- A saturation-aware ranking would weight these down
- Wells 2, 4, 5, 6 (14-15% saturation) are more defensible "best wells"

**Takeaway line:** "If we pick the highest-kh well as our exemplar, we're
partly picking the well with the most aggressive saturation."

**Speaker notes:**
> Decision-makers naturally want a ranked list of wells. But the simple kh
> sum isn't trustworthy here. The wells with the highest kh also have the
> highest fraction of samples at the cap — they're not necessarily "best,"
> they're "most censored."
>
> A production analysis would either correct for censoring with a regression
> model, or report uncertainty bounds on the kh rank.

---

## Slide 7 — Zone D fails on porosity, not shale

**Title:** Zone D should be bypassed
**Visual:** NTG vs cutoff for Zone D specifically (subset of Chart 04)
**Bullets:**
- Zone D NTG never exceeds 32% — even at the loosest cutoff (vsh ≤ 0.7)
- avg phit in Zone D is 0.092 — right at the phit cutoff (0.08)
- Samples fail the *porosity* test, not the *shale* test
- No matter how generous our shale tolerance, Zone D is not reservoir

**Takeaway line:** "Bypassing Zone D is unambiguous. The geology says so."

**Speaker notes:**
> One specific decision we can make with confidence: skip Zone D. I ran the
> cutoff sweep with porosity held fixed, then checked the porosity
> distribution within Zone D. The mean porosity is 0.09 — barely above the
> 0.08 cutoff. Zone D samples just don't have pore space; relaxing the shale
> threshold won't recover that. It's tight non-reservoir.

---

## Slide 8 — Bootstrap confidence intervals on kh

**Title:** Where our kh estimates are most uncertain
**Visual:** Bootstrap CI on kh per (well, zone) at the default cutoff (or
small table)
**Bullets:**
- Bootstrap: 200 resamples per group, 90% confidence interval
- Most Zone B kh values: very tight CI (high sample count, low variance)
- Zone D: wide CI relative to point estimate — but the magnitude is tiny
- Practical impact: Zone B kh certainty is high; Zone D's uncertainty
  doesn't matter because the values are sub-millidarcy

**Takeaway line:** "The bootstrap shows our numbers are precise. Whether
they're *accurate* depends on the tool saturation — that's a different
problem."

**Speaker notes:**
> I added bootstrap confidence intervals on kh — 200 resamples within each
> well-zone group. The CIs are tight because sample counts are large. But
> bootstrap measures *sampling* uncertainty, not *measurement* uncertainty.
> A censored tool is a measurement bias the bootstrap can't see. That's why
> I keep coming back to the saturation issue — it's the dominant source of
> uncertainty in Zone B, and the bootstrap can't fix it.

---

## Slide 9 — Choosing the zone for sub-zone clustering

**Title:** Two attempts: Zone B (instructive failure) → Zone C (success)
**Visual:** Side-by-side bullet table or a "decision tree" graphic
**Bullets:**
- Zone B was the obvious first choice — highest kh, highest NTG
- Clustering failed: silhouette peaks at k=2 (0.65), but the two clusters
  have identical centroids (vsh 0.24, log_perm 4.17) because they're both
  96% saturated
- LOWO ARI = 0.97 — reproducibly meaningless
- Re-targeted Zone C: <1% saturation, real Lorenz heterogeneity, 7 wells
  available

**Takeaway line:** "Clustering can only see what the tool measures. When the
tool is censored, the clustering reproduces the censoring."

**Speaker notes:**
> I want to be transparent about this: my first attempt at Part D was on Zone
> B. It came out reproducible but meaningless. Two sub-zones that look
> identical on every metric — same average porosity, same average
> permeability, same saturation fraction. The high reproducibility score
> made it *worse*, not better, because it looked like the model was working.
>
> Rather than force a 3-cluster solution on Zone B with arbitrary features,
> I diagnosed the failure and re-targeted Zone C. That's the right call for
> production — knowing when not to trust your own model.

---

## Slide 10 — Zone C splits into 3 reproducible sub-zones

**Title:** Three rock types, one geological column, 7 wells
**Visual:** Chart 06 (Zone C) — depth profile per well
**Bullets:**
- Sub-zone 0: tight (avg perm ~200 mD, avg phit 0.14, vsh 0.45)
- Sub-zone 1: mid-quality (~700 mD, phit 0.21, vsh 0.34)
- **Sub-zone 2: best rock (~1,100 mD, phit 0.23, vsh 0.29)**
- Same vertical stack in all 7 wells: best on top, tight in middle, mid at base
- LOWO Adjusted Rand Index = 0.97 — geology is reproducible

**Takeaway line:** "This is what a successful reservoir cluster looks like:
three orders of magnitude in permeability, identical stack across all wells."

**Speaker notes:**
> Pooled K-Means on six features — vsh, porosity, log permeability, water
> saturation, plus two derived: effective porosity (porosity × non-shale
> fraction) and hydrocarbon porosity (porosity × oil saturation). Standardised,
> then clustered.
>
> Three orders of magnitude separation in permeability between sub-zones.
> Same stacking order across all 7 wells. Cross-well validation by
> leave-one-out gives a near-perfect Adjusted Rand Index. That's the kind
> of clustering result you can actually plan a well program around.

---

## Slide 11 — Sub-zone 2 is the drilling target

**Title:** 29% of Zone C thickness, 48% of Zone C flow capacity
**Visual:** Stacked bar of (thickness, kh) per sub-zone, with Sub-zone 2
highlighted
**Bullets:**
- Thickness: Sub-zone 2 has 315.6 m total across 7 wells (29% of Zone C)
- kh: Sub-zone 2 has 350 K mD·m (48% of Zone C)
- Geological location: top of Zone C in every well
- Completion implication: place perforations in the top third of Zone C
- Risk: <1% saturation in Sub-zone 2 → the 1,100 mD estimate is defensible

**Takeaway line:** "The clearest operational recommendation from this whole
analysis."

**Speaker notes:**
> If I have to convert this whole analysis into one decision, this is it.
> Within Zone C, the top sub-zone disproportionately holds the flow capacity.
> It's stacked the same way in all 7 wells, so we can plan completion based
> on relative depth from the Zone C top, not absolute depth.

---

## Slide 12 — k = 3 by intuition, not by silhouette pick

**Title:** Choosing the number of clusters
**Visual:** Chart 07 — optimal-K (silhouette + BIC + elbow)
**Bullets:**
- Silhouette ranks k=2 highest in both zones (0.65, 0.39)
- BIC monotonically prefers higher k (GMM can fit more sub-structure)
- We chose k=3 for geological reasons: shallow marine clastics typically
  show three lithology classes
- Post-hoc check: at k=3 the Zone C centroids are 5× apart in permeability
  — clearly real lithologies
- k=4 splits one of the three sub-zones into noise; k=2 collapses two real
  lithologies

**Takeaway line:** "Don't outsource the lithology count to a silhouette
score."

**Speaker notes:**
> A reasonable critique would be "silhouette said k=2, why did you pick 3?"
> I want to be explicit about the reasoning. Silhouette measures cluster
> compactness vs separation, but it doesn't know about lithology classes.
> The three Zone C sub-zones I showed differ by a factor of five in
> permeability — that's not a marginal split, it's a real lithology.
> Picking k=2 would have collapsed sub-zone 0 (tight) and sub-zone 1 (mid)
> into a single fuzzy cluster, losing the drilling signal.

---

## Slide 13 — Engineering reliability

**Title:** Production-ready pipeline
**Visual:** Architecture diagram (Chart 00) — the layered pipeline
**Bullets:**
- 105 pytest tests (unit + invariant) across 6 modules
- 96-100% test coverage on the hot paths (metrics, sensitivity, clustering)
- Single-command CLI: `python -m src.cli {quality, metrics, sweep, field, subzones}`
- Hydra config: cutoffs, sweeps, clustering parameters all in one yaml
- Every chart is rendered twice: matplotlib PNG (reports) + plotly HTML
  (dashboard)
- Reproducible from raw CSVs to final dashboard in 5 commands

**Takeaway line:** "This isn't a one-off notebook — it's a pipeline."

**Speaker notes:**
> This is the bit that often goes missing in take-home assessments. I built
> this as if it were going to be re-run next quarter with new well logs. Every
> module is unit-tested, every chart is reproducible from a config file, every
> CLI command is idempotent. If you swap in new data and re-run the pipeline,
> you get a refreshed dashboard with the same five interpretations.

---

## Slide 14 — Field strategy summary

**Title:** Five decisions this analysis supports
**Visual:** Plain text, big font
**Bullets:**
1. Treat Zone B kh as a conservative *lower bound*, not a best estimate
2. Bypass Zone D — it's tight rock, not reservoir
3. Target Sub-zone 2 (top of Zone C) for drilling and completion
4. Re-rank wells using saturation-weighted kh, not raw kh
5. Calibrate Zones A and C cutoffs to core data before publishing volumes

**Closing line:** "Happy to go deep on any of these — and to discuss what
I'd do differently with more data."

**Speaker notes:**
> Closing five recommendations. Each one connects directly to a specific
> finding in the analysis — the saturation issue, the porosity failure in
> Zone D, the Zone C sub-zone result, the well-ranking artefact, and the
> cutoff sensitivity. Thank you. I'd love to talk about any of these in
> more detail.

---

## Backup slides

If asked technical follow-up questions:

- **B.1** — Bootstrap method details (per-(well, zone) resample, 90% CI)
- **B.2** — Smoothing rationale (rolling mode, min run length)
- **B.3** — Why pooled clustering, not per-well (cluster IDs would be
  uncomparable across wells)
- **B.4** — Why the Hungarian-method approach we *didn't* use (the log_perm
  reordering trick is simpler and equally stable)
- **B.5** — Production extensions: censored regression for un-capping perm,
  seismic-driven zone correlation, integration with PVT
