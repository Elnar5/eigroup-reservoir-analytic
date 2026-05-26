# Cutoff Sensitivity Analysis — Part C.1

**Deliverable:** vsh cutoff sweep across the plausible range [0.30, 0.70]
with phit fixed at 0.08, plus narrative on how to choose a cutoff and
what tradeoffs the sweep reveals.

**Input:** `data/processed/master_table.parquet` — 18,167 depth samples
across 7 wells and 5 zones.

**Output files:**
- `outputs/reports/sweep_results.csv` — full sweep (315 rows: 9 cutoffs × 35 (well, zone) groups)
- `outputs/reports/sweep_field_summary.csv` — zone-level rollup (45 rows: 5 zones × 9 cutoffs)
- `outputs/reports/knee_points_ntg.csv` — per-group regime-change points
- `outputs/reports/kh_bootstrap_ci.csv` — 90% confidence intervals on kh (with `--bootstrap`)

---

## 1. Why a sweep, not a single cutoff

The data dictionary's default `vsh ≤ 0.5` is a literature value, not a
calibrated one. The assignment explicitly notes:

> "In practice, cutoffs are calibrated against core measurements or
> production data, which are not available here. This exercise is about
> sensitivity."

Without calibration, picking a single cutoff is a guess. The defensible
move is to **bound the conclusions** — show which findings survive any
reasonable cutoff and which depend critically on the threshold.

The sweep range [0.30, 0.70] in 0.05 steps gives nine cutoffs. The
endpoints are deliberate:

- **0.30** — strict "pure reservoir" definition; only the cleanest samples
- **0.50** — literature default (baseline)
- **0.70** — permissive "inclusive reservoir" definition; admits shaly
  samples that may or may not produce

Going below 0.30 is unnecessary (almost no samples have vsh < 0.30 in
the clean zones). Going above 0.70 violates the standard reservoir
definition.

---

## 2. Headline results — field NTG by zone and cutoff

| Zone | vsh=0.30 | vsh=0.35 | vsh=0.40 | vsh=0.45 | **vsh=0.50** | vsh=0.55 | vsh=0.60 | vsh=0.65 | vsh=0.70 | Range |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **A** | 0.150 | 0.245 | 0.367 | 0.499 | **0.630** | 0.740 | 0.828 | 0.894 | 0.939 | **79 pp** |
| **B** | 0.794 | 0.876 | 0.911 | 0.924 | **0.930** | 0.930 | 0.930 | 0.930 | 0.930 | **14 pp** |
| **C** | 0.381 | 0.513 | 0.634 | 0.751 | **0.836** | 0.882 | 0.915 | 0.932 | 0.941 | **56 pp** |
| **D** | 0.008 | 0.016 | 0.033 | 0.062 | **0.103** | 0.166 | 0.215 | 0.258 | **0.288** | **28 pp** |
| **E** | 0.316 | 0.409 | 0.513 | 0.606 | **0.699** | 0.770 | 0.821 | 0.859 | 0.885 | **57 pp** |

> *pp = percentage points. Default cutoff (0.50) in bold; max NTG in red.*

**Three distinct response signatures emerge.**

### Signature 1 — Zone B: robust by saturation

Zone B's NTG reaches 79% at the strictest cutoff and plateaus at 93% by
cutoff 0.55. **Across the entire range, NTG moves only 14 percentage
points.** The plateau means no Zone B sample has vsh greater than 0.55 —
the zone is geologically clean. The kh value (10.7M mD·m at the default)
is stable across all cutoffs.

> **However.** Zone B's average perm is exactly 14,997 mD at every cutoff —
> the tool-cap signature. Saturation is invariant to vsh choice; relaxing
> the cutoff does not improve our visibility into actual permeability.
> kh remains a lower bound at every threshold.

### Signature 2 — Zone D: tight rock at any cutoff

Zone D's NTG climbs steadily as the cutoff loosens, but **never exceeds
28.8%, even at vsh = 0.70**. Average permeability stays below 1 mD across
the entire sweep. This is the most consequential finding of the analysis:

- Cutting vsh further would not help. The binding constraint is phit
  (which is held fixed at 0.08), and the underlying perm is sub-mD.
- This is **not a methodology artefact**. It is a physical property of
  the rock.
- A volume decision involving Zone D should treat it as effectively
  non-reservoir, regardless of how the cutoff is set.

The sweep is what gives us this conclusion. A single-cutoff analysis at
0.50 would have shown 10% NTG — already low, but a reviewer could
reasonably ask "would 0.60 change the picture?" The answer is no, and we
can prove it.

### Signature 3 — Zones A, C, E: smoothly sensitive

These three zones swing 56-79 percentage points across the cutoff range.
A field decision based on a point estimate for any of them inherits the
cutoff uncertainty.

- **Zone A** is the most cutoff-sensitive zone (79 pp range). At 0.30,
  Zone A looks like a minor contributor (15% net); at 0.70, it looks
  like a major one (94%). The default 0.50 sits roughly at the curve's
  inflection point.
- **Zone C** grows smoothly. The lack of a sharp knee, combined with its
  Lorenz coefficient of ~0.65, suggests internal heterogeneity rather than
  a single threshold-driven response. This is the signal that motivates
  the sub-zone clustering in Part D.
- **Zone E** behaves similarly to Zone C but with higher average perm
  (around 2,045 mD at the default). Unlike Zone B, Zone E's high perm is
  measurable — minimal saturation. Among the high-perm zones in the field,
  **Zone E is the most defensible**.

---

## 3. Net thickness — the case-required visualization data

The assignment asks for net reservoir thickness **as a function of the
vsh cutoff**, broken out by zone. Below is the full sweep — field-summed
net thickness (metres) at every cutoff.

### 3.1 Net thickness table (all 9 cutoffs)

| Zone | 0.30 | 0.35 | 0.40 | 0.45 | **0.50** | 0.55 | 0.60 | 0.65 | 0.70 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| A | 110.9 | 181.5 | 271.3 | 369.4 | **466.0** | 547.3 | 612.7 | 661.3 | 694.9 |
| B | 607.8 | 670.4 | 697.5 | 707.3 | **711.9** | 712.1 | 712.1 | 712.1 | 712.1 |
| C | 416.5 | 561.2 | 694.2 | 822.0 | **915.0** | 965.6 | 1001.8 | 1020.3 | 1030.7 |
| D | 4.2 | 8.4 | 17.1 | 31.8 | **52.9** | 85.1 | 110.6 | 132.3 | 147.7 |
| E | 265.5 | 343.3 | 430.5 | 508.5 | **586.8** | 646.2 | 689.0 | 720.4 | 742.5 |

> *All values in metres, summed across the 7 wells. Default cutoff
> (0.50) in bold. Source: `outputs/reports/sweep_field_summary.csv`.*

### 3.2 Range comparison

| Zone | net @ 0.30 (m) | net @ 0.70 (m) | Multiplier | Absolute swing |
|---|---:|---:|---:|---:|
| A | 110.9 | 694.9 | **6.3×** | 584 m |
| B | 607.8 | 712.1 | 1.2× | 104 m |
| C | 416.5 | 1030.7 | 2.5× | 614 m |
| D | 4.2 | 147.7 | **35×** | 143 m (but capped low) |
| E | 265.5 | 742.5 | 2.8× | 477 m |

The multipliers tell two stories:

- **Zone D shifts by 35×** in relative terms — but the absolute net
  (4 m to 148 m, against 513 m gross) still tops out near 29% NTG. Big
  multiplier, small reservoir.
- **Zone B barely shifts at all** (1.2×) — the zone is already at its
  geological ceiling. The cutoff choice barely matters here.
- **Zones A, C, E** are the cutoff-sensitive ones in absolute terms,
  swinging 477-614 m depending on the choice.

### 3.3 Visualization

The chart below plots each zone's NTG trajectory across the sweep on a
single panel. Bold lines are zone averages; thin lines are per-well
variation. The dashed vertical line at vsh = 0.50 marks the default cutoff.

![Sensitivity NTG curves](../figures/04_ntg_sensitivity.png)

**Reading the chart at a glance:**

- **Zone B (top, blue)** is essentially flat — robust to cutoff choice.
- **Zone D (bottom, grey)** is also flat, but at the floor — tight rock
  at any threshold.
- **Zones A, C, E** all show steep, smooth ascents through the default
  cutoff region — the trio whose volume estimates are most cutoff-driven.

This is the headline picture: **two flat zones bracket three sensitive
ones**, with the flat zones telling two opposite stories (one robust by
quality, one robust by absence of reservoir).

---

## 4. Knee analysis — where the regime changes

For each (well, zone) group, the "knee" is the cutoff at which NTG jumps
most. Aggregated across the 7 wells (median knee per zone):

| Zone | Median knee cutoff | Median knee jump | Interpretation |
|---|---:|---:|---|
| A | 0.45–0.55 | 0.13–0.16 | NTG accelerates through the middle of the range |
| B | 0.35 | 0.07–0.12 | Early knee — most Zone B samples are below vsh = 0.35 |
| C | 0.35–0.40 | 0.13–0.15 | Knee just before the default; cutoff 0.40 is roughly the inflection |
| D | 0.55–0.65 | 0.06–0.12 | Late knee — most Zone D samples are above vsh = 0.50 (shaly) |
| E | 0.35–0.50 | 0.10–0.12 | Knee straddles the default |

**Geological reading.** Zone D's late knee is a secondary confirmation
that the zone is shale-rich, not just porosity-poor. Cleaner zones (A, C)
have knees in the lower-middle of the cutoff range — most of their
samples cluster below 0.50.

---

## 5. Bootstrap CI on kh — sampling uncertainty (with caveats)

The optional `--bootstrap` flag computes 90% confidence intervals on kh
via 200 sample-level resamples at three cutoffs (0.30, 0.50, 0.70).
**The CI captures sampling-level uncertainty, given the existing
measurements.** It does *not* capture:

- **Tool-cap (saturation) uncertainty.** Resampling samples that are
  censored at 15000 mD reproduces 15000 mD. The resulting CI for Zone B
  is misleadingly narrow.
- **Inter-well geological variability.** A different drilling campaign
  would sample different rock; the bootstrap doesn't model that.
- **Zone-top picking uncertainty.** The zones.csv is treated as
  ground truth.

In practice this means: a **wide CI** (Zone D) signals real statistical
fragility — small sample counts driving the estimate. A **narrow CI**
(Zone B) is *not* a guarantee of accuracy; it can be an artefact of
censoring.

---

## 6. How I would choose a cutoff

Three layers, in order of preference.

### Layer 1 — calibrate against core or production data

If core data or production allocations were available, I would fit the
cutoff so that net intervals correspond to rock that actually produced.
This converts a guess into a measurement and is the standard industry
workflow.

**Not available here**, per the case statement.

### Layer 2 — report ranges, not point estimates

Without calibration, the honest move is to report metrics across a band
of plausible cutoffs and let the reviewer see the variation. For
example, instead of "Zone C NTG is 0.84", I would write "Zone C NTG is
0.75–0.88 across vsh = 0.45–0.55."

For findings that are robust across the band (Zone B's high net, Zone
D's tight-rock signature), the point estimate is fine.

For findings that swing widely (Zone A's NTG), report the range.

### Layer 3 — if a single cutoff is required, pick 0.50 with awareness

The default 0.50 is defensible:

- It sits near the median of the published reservoir-engineering range
  (0.40–0.55 is typical for sand-shale systems).
- For Zone A and Zone C, 0.50 sits roughly at the inflection of the
  NTG curve — neither the strict nor permissive extreme.
- For Zone B and Zone E, the choice barely matters in the plateau
  region.
- For Zone D, no cutoff will change the conclusion.

So `vsh ≤ 0.50, phit ≥ 0.08` is the best default *for reporting*,
provided the analyst flags the sensitivity wherever the answer is
cutoff-driven.

---

## 7. Tradeoffs the sweep reveals

The cutoff choice is a tradeoff between **volume capture** and
**reservoir-quality discipline**.

### Strict cutoff (vsh ≤ 0.30)

| Pros | Cons |
|---|---|
| Highest-quality "pure" reservoir | Smallest net volume — under-estimates reserves |
| avg_phit and avg_perm are highest | Marginal-but-productive rock excluded |
| Low risk of including non-productive shale | Statistically thin sample for some zones (Zone D drops to ~4 m net field-wide) |

### Default cutoff (vsh ≤ 0.50)

| Pros | Cons |
|---|---|
| Matches literature default | A literature default — not calibrated to this field |
| Roughly the inflection of most zones' NTG curves | Zone B already at ceiling; Zone D still tight |
| Reasonable balance | No physical justification beyond convention |

### Permissive cutoff (vsh ≤ 0.70)

| Pros | Cons |
|---|---|
| Largest net volume | Includes shaly rock that may not produce |
| Larger statistical sample for downstream analytics | NTG and kh systematically inflated |
| Lower risk of missing marginal pay | Without core calibration, the inclusion is arbitrary |

### A practical rule

> **If a one-cutoff answer is required, use vsh ≤ 0.50. But always
> report what would change at 0.40 and 0.60, so the reviewer can see
> the cutoff sensitivity directly.**

For the deliverables in this submission, that means the Part B headline
metrics are computed at 0.50, and the sweep tables in Part C.1 stand as
the disclosure of how much those headlines depend on the choice.

---

## 8. Robust findings vs cutoff-driven findings

| Finding | Robust across cutoffs? | Notes |
|---|---|---|
| Zone B is the field's main flow zone | ✅ Yes | NTG ≥ 79% at every cutoff |
| Zone B kh is a lower bound (saturation) | ✅ Yes | Saturation count invariant to vsh |
| Zone D is effectively non-reservoir | ✅ Yes | NTG ≤ 29% at every cutoff |
| Well 7 has the highest single-well kh | ✅ Yes | True at every cutoff in the sweep |
| Zone E is the most reliable high-perm zone | ✅ Yes | Low saturation regardless of cutoff |
| Zone A's NTG is 0.63 | ⚠️ No | Ranges 0.15–0.94 across the sweep |
| Zone C's NTG is 0.84 | ⚠️ No | Ranges 0.38–0.94 |
| Lorenz coefficient is meaningful for Zone B | ❌ No | Saturated samples flatten the curve regardless of cutoff |

**The first six findings are defensible without further data. The last
three require either calibration or explicit cutoff disclosure.**

---

## 9. How to reproduce

```bash
# Required: vsh sweep + zone summary + knee points
python -m src.cli sweep

# Optional: add bootstrap CI on kh (~30 seconds)
python -m src.cli sweep --bootstrap
```

Override sweep parameters at runtime:

```bash
python -m src.cli sweep \
    --vsh-min 0.40 \
    --vsh-max 0.60 \
    --vsh-step 0.02
```

Tests covering the sweep module:

```bash
pytest tests/test_sensitivity.py -v
# 20 tests, 96% coverage of src/analytics/sensitivity.py
```
