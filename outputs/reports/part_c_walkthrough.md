# Part C — Complete Walkthrough

**Cutoff Sensitivity & Field-Level Views**

This is the unified walkthrough of Part C. It covers what we did, why we did
it, every chart, every number, and every interview answer. The two
sub-deliverables (`sensitivity_analysis.md` for C.1 and `field_views.md` for
C.2) remain the authoritative technical documents; this file is the single
read-through that ties them together.

---

## Table of contents

1. [What Part C asks for](#1-what-part-c-asks-for)
2. [What we built](#2-what-we-built)
3. [Part C.1 — Cutoff sensitivity sweep](#3-part-c1--cutoff-sensitivity-sweep)
4. [Part C.2 — The six field-level charts](#4-part-c2--the-six-field-level-charts)
5. [Chart 1 — kh heatmap](#5-chart-1--kh-heatmap)
6. [Chart 2 — kh stacked bar per well](#6-chart-2--kh-stacked-bar-per-well)
7. [Chart 3 — porosity vs permeability cross-plot](#7-chart-3--porosity-vs-permeability-cross-plot)
8. [Chart 4 — NTG sensitivity curves](#8-chart-4--ntg-sensitivity-curves)
9. [Chart 5 — Lorenz curves](#9-chart-5--lorenz-curves)
10. [Chart 9 — Zone-quality box plot](#10-chart-9--zone-quality-box-plot)
11. [How the six charts work together](#11-how-the-six-charts-work-together)
12. [Robust vs cutoff-driven findings](#12-robust-vs-cutoff-driven-findings)
13. [How to choose a cutoff (case requirement)](#13-how-to-choose-a-cutoff-case-requirement)
14. [Tradeoffs (case requirement)](#14-tradeoffs-case-requirement)


---

## 1. What Part C asks for

The case statement has two parts.

### C.1 — Cutoff sensitivity

> "Sweep the vsh cutoff from 0.3 to 0.7 in 0.05 steps, keeping the phit
> cutoff fixed. Show how net reservoir thickness changes as a function of
> the vsh cutoff, broken out by zone. Pick visualizations that make trends
> easy to compare across zones. Describe how you would choose a cutoff and
> what tradeoffs you see."
>
> "This exercise is about sensitivity, understanding how much your reservoir
> volume estimate shifts with the threshold."

### C.2 — Field-level views

> "Build 2–3 field-level views. Consider: how a given zone's reservoir
> quality varies across wells, how zones rank against each other on key
> metrics within a well, and how net reservoir thickness distributes
> across the field."
>
> "These charts should help answer questions like: which zones are
> consistently strong or weak across the field, and whether any spatial
> trends in reservoir quality are visible."

---

## 2. What we built

| Part | Deliverable | Format | Size |
|------|-------------|--------|------|
| C.1 | `sweep_results.csv` | 315 rows (9 cutoffs × 35 (well, zone)) | Machine-readable |
| C.1 | `sweep_field_summary.csv` | 45 rows (5 zones × 9 cutoffs) | Machine-readable |
| C.1 | `knee_points_ntg.csv` | 35 rows (regime-change cutoffs) | Bonus |
| C.1 | `kh_bootstrap_ci.csv` | 105 rows (90% CI on kh) | Bonus |
| C.1 | `sensitivity_analysis.md` | 340-line narrative | Human-readable |
| C.2 | 6 PNG + 6 HTML charts | `outputs/figures/` | Visual deliverable |
| C.2 | `field_views.md` | 413-line narrative | Human-readable |
| C.2 | `dashboard.html` | 9 interactive charts on one page | Presentation tool |

**Six charts** (case asked for 2-3 — we over-delivered to cover every sub-question):

| # | File | Question it answers |
|---|------|---------------------|
| 1 | `01_kh_heatmap.png` | Where in the field is flow capacity? |
| 2 | `02_kh_stacked_bar.png` | How does each well's kh decompose by zone? |
| 3 | `03_phit_perm_crossplot.png` | Is the rock physics sane? |
| 4 | `04_ntg_sensitivity.png` | How does net thickness respond to cutoff? |
| 5 | `05_lorenz_curves.png` | How heterogeneous is flow within each zone? |
| 9 | `09_zone_quality_boxplot.png` | Which zones are consistently strong/weak? |

> Numbering jumps from 5 to 9 because charts 6-8 are Part D outputs (clustering).
> The box plot was added after Part D was already producing charts under those
> numbers, so it landed at 9 to avoid collision.

---

## 3. Part C.1 — Cutoff sensitivity sweep

### 3.1 Why we sweep instead of picking a cutoff

The data dictionary's `vsh ≤ 0.5` is a **literature default**, not a
calibrated value. The case explicitly notes:

> "In practice, cutoffs are calibrated against core measurements or
> production data, which are **not available here**."

Without calibration, picking one cutoff is a guess. The honest move is to
**bound the conclusions** — show which findings survive any reasonable
cutoff (robust) and which depend on the threshold (cutoff-driven).

### 3.2 The sweep — 9 cutoffs × 35 groups = 315 rows

The range [0.30, 0.70] in 0.05 steps gives nine cutoffs:

```
0.30, 0.35, 0.40, 0.45, 0.50, 0.55, 0.60, 0.65, 0.70
```

- **0.30** — strict "pure reservoir" definition
- **0.50** — literature default (baseline)
- **0.70** — permissive "inclusive reservoir" definition

For each cutoff, we recompute every Part B metric. That produces 315 rows.

### 3.3 The headline table — NTG_field by zone and cutoff

| Zone | 0.30 | 0.35 | 0.40 | 0.45 | **0.50** | 0.55 | 0.60 | 0.65 | 0.70 | Range |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **A** | 0.150 | 0.245 | 0.367 | 0.499 | **0.630** | 0.740 | 0.828 | 0.894 | 0.939 | **79 pp** |
| **B** | 0.794 | 0.876 | 0.911 | 0.924 | **0.930** | 0.930 | 0.930 | 0.930 | 0.930 | **14 pp** |
| **C** | 0.381 | 0.513 | 0.634 | 0.751 | **0.836** | 0.882 | 0.915 | 0.932 | 0.941 | **56 pp** |
| **D** | 0.008 | 0.016 | 0.033 | 0.062 | **0.103** | 0.166 | 0.215 | 0.258 | **0.288** | **28 pp** |
| **E** | 0.316 | 0.409 | 0.513 | 0.606 | **0.699** | 0.770 | 0.821 | 0.859 | 0.885 | **57 pp** |

> *pp = percentage points. Default cutoff (0.50) in bold.*

### 3.4 Three response signatures

**Signature 1 — Zone B: robust by cleanliness**

NTG ranges only 79% to 93% and plateaus at 93% by cutoff 0.55. **No Zone
B sample has vsh > 0.55** — the zone is geologically clean. The default
93% NTG is reliable.

> **Caveat:** Zone B's average perm is exactly 14,997 mD at every cutoff —
> the tool-cap signature. Saturation is invariant to vsh choice; loosening
> the cutoff does not improve our visibility into actual permeability.
> kh remains a lower bound at every threshold.

**Signature 2 — Zone D: tight rock at any cutoff**

NTG climbs steadily as the cutoff loosens but **never exceeds 28.8%**, even
at vsh = 0.70. Average perm stays below 1 mD across the entire sweep.

- Cutting vsh further would not help — the binding constraint is phit
  (held fixed at 0.08), and underlying perm is sub-mD.
- This is **not a methodology artefact**. It is a physical property.
- A volume decision involving Zone D should treat it as non-reservoir,
  regardless of cutoff.

**Signature 3 — Zones A, C, E: smoothly sensitive**

These three zones swing 56-79 percentage points across the sweep. Volume
estimates for these zones inherit the cutoff uncertainty.

### 3.5 Net thickness — what the case literally asks for

The case asks for net thickness "as a function of the vsh cutoff". Full
table:

| Zone | net @ 0.30 (m) | net @ 0.50 (m) | net @ 0.70 (m) | Multiplier |
|---|---:|---:|---:|---:|
| A | 110.9 | 466.0 | 694.9 | **6.3×** |
| B | 607.8 | 711.9 | 712.1 | 1.2× |
| C | 416.5 | 915.0 | 1030.7 | 2.5× |
| D | 4.2 | 52.9 | 147.7 | **35×** (capped low) |
| E | 265.5 | 586.8 | 742.5 | 2.8× |

Two stories:

- **Zone D shifts by 35×** in relative terms — but the absolute net (4 m to
  148 m, against 513 m gross) still tops out near 29% NTG. Big multiplier,
  small reservoir.
- **Zone B barely shifts** — already at its geological ceiling.

### 3.6 Bootstrap CI — what it captures, what it doesn't

The `--bootstrap` option computes 90% CI on kh via 200 sample-level
resamples at three cutoffs (0.30, 0.50, 0.70).

| Captures | Doesn't capture |
|----------|-----------------|
| Sampling variability given existing measurements | Tool-cap (saturation) uncertainty |
|  | Inter-well geological variability |
|  | Zone-top picking uncertainty |

**Practical reading:**

- Wide CI (Zone D) signals real statistical fragility — small samples
  driving the estimate.
- Narrow CI (Zone B) is *not* a guarantee of accuracy — it can be a
  censoring artefact.

---

## 4. Part C.2 — The six field-level charts

### 4.1 Why six instead of two-three

The case asks "Build 2-3 field-level views" but lists five distinct
questions to consider:

1. How a zone's quality varies across wells
2. How zones rank against each other within a well
3. How net thickness distributes across the field
4. Which zones are consistently strong or weak
5. Spatial trends

Six charts let each question get a chart that answers it directly,
rather than forcing a single visual to do three jobs poorly.

### 4.2 Design principles across all six

| Principle | What it is | Why |
|-----------|------------|-----|
| Fixed colour palette | Zone B always blue, Zone D always grey, etc. (Wong CVD-safe) | Pattern-match across charts without reading legends |
| Dual figure output | Each chart produces both PNG (matplotlib) and HTML (plotly) | Static for slides, interactive for dashboard |
| Saturation surfacing | Three charts annotate or mark tool-cap samples | The dataset's biggest caveat — hiding it would mislead |
| Log scales where needed | kh on heatmap and box plot; perm on crossplot | 5-6 orders of magnitude across zones |

### 4.3 The six charts at a glance

| Chart | View | Best at answering |
|-------|------|-------------------|
| 1. Heatmap | 7×5 grid of cells | "Where exactly is kh?" |
| 2. Stacked bar | 7 bars, zone segments | "How do wells rank?" |
| 3. Crossplot | scatter, phit vs log(perm) | "Is the data sane?" |
| 4. Sensitivity | 5 curves vs cutoff | "Robust or threshold-dependent?" |
| 5. Lorenz | 5 curves vs storage fraction | "Is flow concentrated?" |
| 9. Box plot | 5 boxes per panel × 2 panels | "Consistent across wells?" |

---

## 5. Chart 1 — kh heatmap

### 5.1 What it shows

A 7×5 grid: 7 wells (rows), 5 zones (columns), each cell coloured by kh on
a log scale. Annotations on each cell show kh, and where present, the
count of samples at the 15,000 mD tool ceiling.

### 5.2 Real-data observations

**Zone B column** — uniformly bright across all wells. Real numbers:

```
well 1 Zone B: 1,965,000 mD·m  (saturated: 655)
well 2 Zone B: 1,355,876 mD·m  (saturated: 451)
well 3 Zone B: 1,155,000 mD·m  (saturated: 385)
well 4 Zone B: 1,358,675 mD·m  (saturated: 452)
well 5 Zone B: 1,132,500 mD·m  (saturated: 151)
well 6 Zone B: 1,339,888 mD·m  (saturated: 445)
well 7 Zone B: 2,369,753 mD·m  (saturated: 789)  ← field maximum
```

**Zone D column** — uniformly dark (sub-15 mD·m kh):

```
well 1 Zone D: 4
well 2 Zone D: 8
well 3 Zone D: 1
well 4 Zone D: 7
well 5 Zone D: 3
well 6 Zone D: 9
well 7 Zone D: 10
```

**Three orders of magnitude separate Zone B from Zone D.**

### 5.3 Why log colour scale

Linear colour would collapse Zone D into near-black against everything
else. Log scale spreads the dynamic range evenly. A note on the colourbar
makes the log transformation explicit.

### 5.4 Why some saturation counts are missing

The code only annotates the saturated count when it's > 0. Cells with no
saturated samples leave that line blank. Zones A and D never hit the tool
ceiling, so their cells show only the kh number. **This itself is
information** — Zone A and Zone D values are reliable, Zone B values are
lower bounds.

### 5.5 Interview answer

> "The kh heatmap shows flow capacity at every well-zone intersection.
> Three things are immediately visible: **Zone B dominates uniformly**
> with kh between 1M and 2.4M mD·m, **Zone D is uniformly weak** (three
> orders of magnitude lower), and **well 7 leads the field** at 2.37M
> mD·m. The saturated-sample counts annotated on Zone B cells flag those
> kh values as lower bounds — the tool can't measure above 15,000 mD."

---

## 6. Chart 2 — kh stacked bar per well

### 6.1 What it shows

Seven bars (one per well), each decomposed into five colour segments
(one per zone). Bar height is total kh; segment height is that zone's
contribution.

### 6.2 Real-data observations

| Well | Total kh | Zone B share |
|------|----------|--------------|
| well 1 | 2,266,121 | 87% |
| well 2 | 1,763,870 | 77% |
| well 3 | 1,405,687 | 82% |
| well 4 | 1,670,935 | 81% |
| well 5 | 1,434,821 | 79% |
| well 6 | 1,692,769 | 79% |
| **well 7** | **2,591,532** ⭐ | 91% |

**Zone B contributes 77-91% of every well's total kh.**

Zone D's segment is **visually invisible** in every bar (kh measured in
single-digit mD·m against a y-axis that spans millions).

### 6.3 Why stacked, not grouped

Grouped bars would let you compare zones within a well, but you'd lose
the total. Stacked compresses ranking and decomposition into a single
visual — total height for well ranking, segment heights for zone
contribution.

### 6.4 Interview answer

> "The stacked bar makes two things immediately readable: bar height
> ranks the wells (well 7 leads at 2.6M mD·m kh), and the blue segment
> in every bar shows Zone B contributing 77-91% of each well's total.
> **Field-wide strategy targeting aggregate kh is really a Zone B
> strategy.** Zone D's grey segment is visually absent — its kh is below
> the visible threshold, confirming the heatmap's pattern."

---

## 7. Chart 3 — porosity vs permeability cross-plot

### 7.1 What it shows

Scatter plot. Each dot is one depth sample (subsampled to ~20% for
legibility; ~3,633 visible). X-axis is porosity (`phit`); Y-axis is
log10(perm) ranging from -1 to 5. Colour by zone. **Red ✕ markers** mark
all saturated samples (these are *not* subsampled — every one shown).

### 7.2 Why log y-axis

Perm spans 0.5 mD (Zone D) to 15,000 mD (Zone B cap). Linear y-axis would
collapse Zone D into the x-axis. Log spreads them:

```
log_perm = 0     → perm = 1 mD
log_perm = 1     → perm = 10 mD
log_perm = 2     → perm = 100 mD
log_perm = 3     → perm = 1,000 mD
log_perm = 4     → perm = 10,000 mD
log_perm = 4.18  → perm = 15,000 mD  ← tool ceiling
```

### 7.3 Three things the chart shows

**(1) Carman-Kozeny trend** — log(perm) climbs roughly linearly with phit.
This is the classical petrophysical relationship. **The data is
internally consistent.**

**(2) Saturation band** — every red ✕ sits at exactly log_perm = 4.18.
This is a **horizontal band**, not a geological feature — it's the
instrument's measurement limit drawn directly on the data.

**(3) Zone clusters** — each zone occupies a different region:

| Zone | Phit range | log(perm) range | Position |
|------|-----------|-----------------|----------|
| D (grey) | 0.05-0.10 | -1 to 1 | **Bottom-left** |
| A (green) | 0.10-0.25 | 1.5-3.5 | Middle-lower |
| C (orange) | 0.15-0.25 | 2-3.5 | Middle |
| E (red) | 0.18-0.25 | 2.5-3.5 | Middle-upper |
| B (blue) | 0.25-0.35 | **4.18 (cap)** | **Top band** |

**Zone D in the bottom-left is the visual proof of tight rock.** Both phit
and perm are at the floor of the dataset.

### 7.4 What it doesn't answer directly

This chart doesn't directly answer the five case sub-questions. Its job is
**data quality** — sanity check + saturation visualization. Both are
critical context for trusting the kh numbers in the other charts.

### 7.5 Interview answer

> "Chart 3 serves two purposes. **First, sanity check** — the diagonal
> Carman-Kozeny trend confirms phit and perm are correlated as expected.
> The data is internally consistent. **Second, saturation** — every red
> mark sits at log_perm = 4.18 (the 15,000 mD tool ceiling), most densely
> in Zone B's high-phit region. The horizontal band is the instrument's
> measurement limit, drawn directly on the data. **Zone D clusters in
> the bottom-left** — visual proof of tight rock."

---

## 8. Chart 4 — NTG sensitivity curves

### 8.1 What it shows

Line chart, x-axis is vsh cutoff (0.30-0.70), y-axis is NTG_field.
**Five bold lines** (zone averages across 7 wells) and **35 thin lines**
(per-well trajectories). Dashed vertical line at vsh = 0.50 marks the
default.

### 8.2 What the chart shows

**Zone B (blue, top)** — essentially flat above NTG = 0.79 across the
entire sweep. Robust by cleanliness.

**Zone D (grey, bottom)** — essentially flat below NTG = 0.29 across the
entire sweep. Robust by tightness. **Same flat-line behaviour, opposite
story.**

**Zones A, C, E** — smooth ascending curves through the default region.
Volume estimates are cutoff-driven.

**Thin lines** show well-to-well spread — tight for Zones B and D
(consistent), wider for Zones A and C (variable).

### 8.3 Can well-to-well differences be read from this chart?

**Yes, but with effort.** The thin lines do show per-well trajectories.
But with 40 lines on one chart, the patterns are dense. For a clean
read on well consistency, **Chart 9 (the box plot) is the right tool**.

### 8.4 Interview answer

> "Chart 4 is the sensitivity sweep visualized. **Three patterns**: Zone
> B is flat at the top — robust by cleanliness, NTG 79-93% across the
> entire sweep. Zone D is flat at the bottom — robust by tightness, NTG
> never exceeds 29%. **Two flat zones bracket three sensitive ones** —
> Zones A, C, E all ascend smoothly through the default cutoff region.
> Their volume estimates depend on the threshold choice. This chart is
> what bounds the conclusions."

---

## 9. Chart 5 — Lorenz curves

### 9.1 What Lorenz measures

A heterogeneity index in [0, 1]:

- **0** = flow contributed equally across all samples (homogeneous)
- **1** = flow concentrated in a single super-streak (extreme heterogeneity)

Construction (5 steps):

1. Sort samples by perm descending
2. Compute flow capacity (perm × dz) per sample
3. Cumulative flow fraction = F (cumulative sum / total)
4. Cumulative storage fraction = C (sample count / total)
5. Plot F vs C. Distance from the 45° diagonal = Lorenz coefficient.

### 9.2 Real-data Lorenz values

| Zone | Lorenz | Interpretation |
|------|--------|----------------|
| Zone B | **~0.001** | Glued to diagonal — but **saturation artefact** |
| Zone D | 0.30-0.48 | Moderate, but small samples make this noisy |
| Zone A | 0.43-0.48 | Moderate |
| Zone E | 0.51-0.54 | Moderate-high |
| **Zone C** | **~0.65** | **High heterogeneity — real** |

### 9.3 Three stories

**Zone C — real heterogeneity (motivation for Part D)**

The curve arches well above the diagonal. This is **not a saturation
artefact** — Zone C has only 1-5 saturated samples per well, so its
permeability range is genuinely visible. The high Lorenz coefficient
says some Zone C intervals carry far more flow than others. **This is
the signal that motivates the sub-zone clustering in Part D**, which
finds 3 reproducible sub-zones.

**Zone B — Lorenz is misleading (saturation artefact)**

The curve is glued to the diagonal. Lorenz ≈ 0.001 suggests perfect
homogeneity — but **99.85% of Zone B's net samples report exactly 15,000
mD**. By construction, identical perm values contribute equally to flow,
forcing the curve onto the diagonal. The instrument cannot distinguish a
50,000 mD streak from a 20,000 mD streak; both register as 15,000. Any
Lorenz curve over a saturated zone collapses to the diagonal as an
inevitable consequence.

**Zones A, E — moderate, expected**

Lorenz 0.43-0.54 is typical for clean sand reservoirs. Moderate
heterogeneity — not concentrated enough to need sub-zoning.

### 9.4 Interview answer

> "Chart 5 shows Lorenz curves — the standard reservoir-engineering tool
> for flow heterogeneity. A curve glued to the diagonal means uniform
> contribution; an arched curve means concentrated flow.
>
> **Zone C arches strongly** (Lorenz ≈ 0.65) — real, measurable
> heterogeneity. **This is the signal that motivates the sub-zone
> clustering in Part D**, which found 3 reproducible sub-zones.
>
> **Zone B's curve is glued to the diagonal** (Lorenz ≈ 0.001). **This is
> not a homogeneity finding — it's a saturation artefact.** 99.85% of
> Zone B's net samples report exactly 15,000 mD, so they all contribute
> equally by definition. The tool cannot see the heterogeneity that is
> probably there."

---

## 10. Chart 9 — Zone-quality box plot

### 10.1 What it shows

Two side-by-side panels, both with one box per zone. Each box summarises
how that zone's metric varies **across the 7 wells**.

- **Left panel:** NTG distribution (range [0, 1])
- **Right panel:** log10(kh) distribution

For each box:
- Top of box = 75th percentile
- Bottom of box = 25th percentile
- Line in box = median
- White diamond = mean
- Whiskers = min/max range (within 1.5× IQR)

**Tight box = consistent across wells. Wide box = variable.**

### 10.2 Real-data observations

**NTG panel (left)** — across 7 wells:

| Zone | Median | IQR (25-75%) | Box width |
|------|--------|--------------|-----------|
| A | 0.62 | 0.60-0.66 | **Widest** |
| B | 0.93 | 0.92-0.94 | **Tightest** |
| C | 0.84 | 0.81-0.87 | Moderate |
| D | 0.10 | 0.09-0.14 | **Tight** |
| E | 0.70 | 0.69-0.73 | Moderate |

**log(kh) panel (right)** — five orders of magnitude separate the zones:

| Zone | Median log(kh) | Real kh range (mD·m) |
|------|---------------|----------------------|
| B | **~6.2** | **1.1M - 2.4M** |
| E | ~5.2 | 120K - 235K |
| C | ~5.0 | 70K - 145K |
| A | ~4.5 | 23K - 55K |
| D | **~0.9** | **1 - 10** |

### 10.3 The three stories — same shape, different y-position

**Zone B — consistently strong**

Tight box at the top of the NTG panel (~0.93) and tight box near the
top of the kh panel (~10⁶ mD·m). Every well has near-identical Zone B
behaviour.

**Zone D — consistently weak**

Tight box at the bottom of both panels. NTG ~10%, kh ~10⁰ mD·m, every
well. **Field-wide tight rock confirmed, not a localized issue.**

**Zone A — most variable**

Widest box on the NTG panel. Some wells have Zone A at NTG ≥ 0.66, others
below 0.60. **Site-specific decisions on Zone A need to account for
well-to-well variability.**

### 10.4 Why two panels, not one

NTG (a fraction in [0, 1]) and kh (positive, spanning six orders of
magnitude) need different y-axis scales. One chart would force log-NTG,
which is hard to read, or collapse kh detail. Side-by-side panels share
the x-axis (zones) so the patterns cross-check at a glance — Zone B is
tight in NTG **and** tight in kh.

### 10.5 Why this is the chart for the case prompt

The case asks specifically for "which zones are consistently strong or
weak across the field." Other charts touch this question indirectly:

- The heatmap shows it cell-by-cell — reader has to scan and pattern-match
- The stacked bar shows it implicitly through bar composition
- The sensitivity and Lorenz curves answer different questions

**Chart 9 answers the question head-on.** Five seconds, no scanning.

### 10.6 Interview answer

> "Chart 9 is the box plot that directly answers the case prompt 'which
> zones are consistently strong or weak across the field'.
>
> **Zone B sits at the top with a tight box** — every well has Zone B
> NTG around 93% and log(kh) around 6.2. **Consistently strong** across
> the entire field.
>
> **Zone D sits at the bottom with a tight box** — every well has Zone D
> NTG around 10% and log(kh) around 1. **Consistently weak** — field-wide
> tight rock, not localized.
>
> **Zone A has the widest box** — most variable across wells. Volume
> estimates for Zone A should account for that variability."

---

## 11. How the six charts work together

Each chart answers a different question; together they cover the field
from six angles.

| Question | Chart |
|---|---|
| Where is the flow concentrated? | 1 (heatmap) |
| Which wells lead and how? | 2 (stacked bar) |
| Is the rock physics sane? | 3 (crossplot) |
| How sensitive is the result to threshold choice? | 4 (sensitivity) |
| Is flow uniform within each zone, or concentrated? | 5 (Lorenz) |
| Which zones are consistently strong or weak? | 9 (box plot) |

A reviewer with five minutes should look at all six in the order above,
which builds the story end-to-end:

1. Flow lives mostly in Zone B (heatmap)
2. Every well's kh is dominated by Zone B (stacked bar)
3. Most of Zone B is at the tool ceiling (crossplot)
4. Zone B finding is robust to cutoff; Zone D finding is robust the
   opposite way (sensitivity)
5. Among non-saturated zones, Zone C is the heterogeneous one worth
   sub-zoning (Lorenz)
6. Both findings (Zone B strong, Zone D weak) hold across every well
   (box plot)

A reviewer with one chart should pick the heatmap — it carries the most
information per pixel.

---

## 12. Robust vs cutoff-driven findings

The sweep tells us which conclusions survive any reasonable cutoff and
which depend on the threshold.

| Finding | Robust? | Why? |
|---------|---------|------|
| Zone B is the field's main flow zone | ✅ Yes | NTG ≥ 79% at every cutoff |
| Zone B kh is a lower bound (saturation) | ✅ Yes | Saturation count invariant to vsh |
| Zone D is effectively non-reservoir | ✅ Yes | NTG ≤ 29% at every cutoff |
| Well 7 has the highest single-well kh | ✅ Yes | True at every cutoff |
| Zone E is the most reliable high-perm zone | ✅ Yes | Low saturation at all cutoffs |
| Zone A's NTG is 0.63 | ⚠️ No | Ranges 0.15-0.94 across sweep |
| Zone C's NTG is 0.84 | ⚠️ No | Ranges 0.38-0.94 |
| Lorenz coefficient is meaningful for Zone B | ❌ No | Saturated samples flatten the curve |

**The first six findings are defensible without further data. The last
three require either calibration or explicit cutoff disclosure.**

---

## 13. How to choose a cutoff (case requirement)

The case asks: "Describe how you would choose a cutoff."

Three layers, in order of preference.

### Layer 1 — calibrate against core or production data

If core or production data were available, fit the cutoff so that net
intervals correspond to rock that actually produced. This converts a
guess into a measurement. **Standard industry workflow.**

**Not available here**, per the case statement.

### Layer 2 — report ranges, not point estimates

Without calibration, report metrics across a band of plausible cutoffs
and let the reviewer see the variation. Instead of "Zone C NTG is 0.84",
write "Zone C NTG is 0.75-0.88 across vsh = 0.45-0.55."

For robust findings (Zone B strong, Zone D tight), point estimates are
fine. For cutoff-driven findings (Zone A NTG), report ranges.

### Layer 3 — if a single cutoff is required, pick 0.50 with awareness

The default 0.50 is defensible:

- Median of the published reservoir-engineering range (0.40-0.55 typical
  for sand-shale)
- For Zones A and C, sits near the inflection of the NTG curve
- For Zones B and E, the choice barely matters in the plateau region
- For Zone D, no cutoff will change the conclusion

So `vsh ≤ 0.50, phit ≥ 0.08` is the best default *for reporting*,
provided the analyst flags the sensitivity wherever the answer is
cutoff-driven.

---

## 14. Tradeoffs (case requirement)

The case asks: "What tradeoffs do you see?"

Volume capture vs reservoir-quality discipline.

### Strict (vsh ≤ 0.30)

| Pros | Cons |
|------|------|
| Highest-quality "pure" reservoir | Smallest volume — under-estimates reserves |
| Highest avg phit and perm | Marginal-but-productive rock excluded |
| Low risk of including non-productive shale | Statistically thin for some zones (Zone D drops to ~4 m field-wide) |

### Default (vsh ≤ 0.50)

| Pros | Cons |
|------|------|
| Matches literature default | A literature default — not calibrated here |
| Near the inflection for most zones | No physical justification beyond convention |
| Reasonable balance | Zone B already at ceiling; Zone D still tight |

### Permissive (vsh ≤ 0.70)

| Pros | Cons |
|------|------|
| Largest volume | Includes shaly rock that may not produce |
| Larger statistical sample | NTG and kh systematically inflated |
| Lower risk of missing marginal pay | Without core, the inclusion is arbitrary |

### Practical rule

> **If a one-cutoff answer is required, use vsh ≤ 0.50. But always report
> what would change at 0.40 and 0.60, so the reviewer can see the cutoff
> sensitivity directly.**

For this submission, Part B headline metrics are computed at 0.50, and
the Part C.1 sweep tables stand as the disclosure of how much those
headlines depend on the choice.

---

