# Part B — Complete Walkthrough

**Per-(Well, Zone) Reservoir Metrics**

This is the unified walkthrough of Part B. It covers what we computed,
why we chose each formula, what the numbers mean per zone and per
well, and every interview answer. The technical document
`metrics_per_zone.md` remains the authoritative machine-readable
deliverable; this file is the human-readable read-through that tells
the story.

---

## Table of contents

1. [What Part B asks for](#1-what-part-b-asks-for)
2. [What we built](#2-what-we-built)
3. [The five required metrics](#3-the-five-required-metrics)
4. [Bonus diagnostics — why we added them](#4-bonus-diagnostics--why-we-added-them)
5. [Three critical design choices](#5-three-critical-design-choices)
6. [Zone A — clean top reservoir](#6-zone-a--clean-top-reservoir)
7. [Zone B — the saturation-capped flow champion](#7-zone-b--the-saturation-capped-flow-champion)
8. [Zone C — heterogeneous secondary reservoir](#8-zone-c--heterogeneous-secondary-reservoir)
9. [Zone D — tight rock](#9-zone-d--tight-rock)
10. [Zone E — deep reliable reservoir](#10-zone-e--deep-reliable-reservoir)
11. [Well-level rollup and the well 7 paradox](#11-well-level-rollup-and-the-well-7-paradox)
12. [Interview prep — short answers](#12-interview-prep--short-answers)

---

## 1. What Part B asks for

The case statement asks for **per-(well, zone) reservoir metrics**:

> "For each well and zone combination, compute:
> 1. Gross thickness
> 2. Net reservoir thickness (using vsh and phit cutoffs)
> 3. Average porosity in net interval
> 4. Average permeability in net interval
> 5. Flow capacity (kh) in net interval"

Five required metrics × 35 (well, zone) groups = 175 numbers. The case
also expects sensible NaN handling and reasoning about edge cases.

---

## 2. What we built

| Deliverable | Format | Location |
|-------------|--------|----------|
| Per-(well, zone) metrics (35 rows × 12 columns) | CSV + Parquet | `outputs/reports/metrics_per_zone.csv` |
| Field rollup by zone (5 rows) | CSV | `outputs/reports/field_summary_by_zone.csv` |
| Field rollup by well (7 rows) | CSV | `outputs/reports/field_summary_by_well.csv` |
| Per-zone narrative report | Markdown | `outputs/reports/metrics_per_zone.md` |
| This walkthrough | Markdown | `outputs/reports/part_b_walkthrough.md` |

Pipeline orchestration:

```bash
python -m src.cli metrics
```

Single command. Reads the Part A master table, computes 12 metrics
per (well, zone), writes everything out in one pass.

---

## 3. The five required metrics

All five metrics use the cutoffs from the data dictionary:
**vsh ≤ 0.5 AND phit ≥ 0.08**.

### 3.1 Gross thickness

```
gross_thickness = sum(dz) over all rows in the (well, zone) group
```

The total interval length of the zone in that well. Uses **per-well
dz** from Part A (Section 4.4), so well 5's 0.5 m step is handled
transparently — every sample contributes its actual thickness.

### 3.2 Net reservoir thickness

```
net_mask = (vsh <= 0.5) & (phit >= 0.08)
net_thickness = sum(dz) over rows where net_mask is True
```

This is what the case calls "net reservoir." Samples that don't meet
**both** cutoffs are excluded — too shaly (high vsh) or too tight (low
phit).

### 3.3 Average porosity in net interval

```
avg_phit_in_net = mean(phit) over net rows
```

The arithmetic mean of porosity among samples that qualify as net.

### 3.4 Average permeability in net interval

```
avg_perm_in_net = mean(perm) over net rows
```

The arithmetic mean of permeability among net samples. **Important
caveat:** saturated samples (perm = 15,000 mD) are kept in this mean.
That means the mean is dragged *down* — real perm at the saturated
samples is higher than 15,000 mD, but the recorded value is exactly
15,000.

For zones with heavy saturation (Zone B), the arithmetic mean reads
~14,997 mD — essentially the ceiling. A second metric,
**kh-weighted average perm** (Section 4), captures the engineering-
relevant mean.

### 3.5 kh (flow capacity)

```
kh = sum(perm × dz) over net rows
```

Flow capacity has units of mD·m. It's the integral of permeability
over the net thickness — the standard reservoir-engineering measure
of how much flow a zone can sustain.

**Saturation caveat:** when perm is capped at 15,000 mD, the contribution
`perm × dz` is also capped. The reported kh is therefore a
**conservative lower bound** anywhere saturation is present. We do not
correct it upward (we can't — the true value is unknown), but we
surface the saturated count alongside every kh number so the bound is
visible.

---

## 4. Bonus diagnostics — why we added them

Beyond the five required metrics, we added seven bonus columns. Each
solves a real problem that the required metrics alone leave hidden.

| Bonus metric | Why it earns its place |
|--------------|------------------------|
| **NTG** (net-to-gross) | Quality ratio = net / gross. Standard reservoir-quality KPI; immediately readable on a 0-1 scale. |
| **kh-weighted avg perm** | = kh / net_thickness. The engineering-correct mean when sampling step varies between wells. |
| **Lorenz coefficient** | Heterogeneity index in [0, 1]. Signals which zones may need sub-zoning (motivates Part D). |
| `n_samples_net` | Sanity check on the net mask — how many samples passed. |
| `n_phit_nan` | NaN porosity excluded from net. Concentrated entirely in well 3 (78 total). |
| **`n_perm_saturated_in_net`** | Net samples at the 15,000 mD tool ceiling. **Surfaces the lower-bound nature of kh.** |
| `frac_saturated` | Saturated count / total net count. Useful when comparing across zones of different size. |

### Why NTG matters

`net = 466 m` is hard to interpret in isolation. `NTG = 0.63` says
"63% of the zone is reservoir-quality rock." That single number is
what a reviewer wants to compare across zones.

### Why kh-weighted perm matters

The arithmetic mean of perm (Section 3.4) treats every sample equally,
regardless of how much thickness it represents. The **kh-weighted
mean** weights each sample by its `dz`, giving the engineering
average:

```
kh_weighted_avg_perm = kh / net_thickness
                    = sum(perm × dz) / sum(dz)
```

This is the value a reservoir engineer would actually use in flow
calculations.

### Why the Lorenz coefficient matters

A high Lorenz coefficient (~0.6+) signals **internal heterogeneity** —
some samples carry far more flow capacity than others. That's the
signal that a zone might benefit from being subdivided. **Zone C's
Lorenz of 0.65 is what motivated the Part D clustering**, which
successfully found three reproducible sub-zones.

The Lorenz coefficient is computed **on net samples only** — non-
reservoir rock shouldn't dilute the heterogeneity signal we're trying
to detect.

---

## 5. Three critical design choices

### Choice 1 — Cutoffs are parameters, not constants

The `vsh_max` and `phit_min` cutoffs are passed as function arguments,
not hardcoded. This is what lets Part C.1 sweep across nine cutoffs
without rewriting the computation — same function, different
parameters.

### Choice 2 — NaN handling: exclude conservatively, count visibly

Samples with NaN `vsh` or `phit` are excluded from net by default.
**Missing data is not reservoir.** But the exclusion is counted
separately in `n_phit_nan` so the impact is visible.

For well 3 specifically (Section 8 of Part A), 78 NaN porosity samples
are spread across all five zones. Each zone's net thickness for well 3
is therefore a conservative lower bound — if those measurements had
succeeded, additional thickness might have qualified.

### Choice 3 — Saturation handling: keep, count, surface

The opposite policy applies to the perm tool ceiling. **Saturated
samples are kept in kh.** Dropping them would systematically
under-estimate flow capacity. Instead:

- Saturated samples contribute `15,000 × dz` to kh (a lower bound,
  but the best we can do)
- The count is reported in `n_perm_saturated_in_net`
- Every downstream chart annotates this count

The exclusion policy for NaN and the inclusion policy for saturation
are **both biases toward conservative under-estimation** — but
intentional ones, with the magnitude visible to the reviewer.

---

## 6. Zone A — clean top reservoir

### 6.1 Field rollup

| Metric | Value |
|--------|------:|
| Gross thickness | 739.7 m |
| Net thickness | 466.0 m |
| **NTG** | **0.63** |
| Avg phit | 0.171 |
| Avg perm (kh-weighted) | 572 mD |
| Total kh | 267,428 mD·m |
| Saturated samples | 0 |

### 6.2 What this zone is

Zone A is the **top reservoir interval** across the field. The numbers
read like a textbook clean reservoir:

- **63% net** — well above the field-wide threshold for "good
  reservoir"
- **17% porosity** — normal range for clean sandstone
- **~570 mD perm** — moderate, well within the tool's measurement
  range
- **Zero saturated samples** — the kh of 267K is a real measurement,
  not a lower bound

### 6.3 Why Zone A is the most "honest" zone

Every other reservoir-quality zone (B, C, E) has at least some
saturation. Zone A has none. That means Zone A's kh of 267K mD·m is
a **fully defensible** number — no asterisks, no censoring caveats.

### 6.4 Per-well stability

Across the 7 wells, Zone A's NTG ranges 0.60-0.66, avg phit ranges
0.170-0.173, and avg perm ranges 502-622 mD. **The zone is
remarkably consistent across the field.**

### 6.5 Cutoff sensitivity (foreshadow to Part C.1)

Zone A is **the most cutoff-sensitive zone** — NTG ranges from 15%
(strict cutoff vsh ≤ 0.30) to 94% (permissive cutoff vsh ≤ 0.70).
A 79-percentage-point swing. Cutoff sensitivity is the price of being
a vsh-borderline zone.

---

## 7. Zone B — the saturation-capped flow champion

This zone deserves its own treatment because it carries the biggest
findings of Part B.

### 7.1 Field rollup

| Metric | Value |
|--------|------:|
| Gross thickness | 765.3 m |
| Net thickness | 711.9 m |
| **NTG** | **0.93** |
| Avg phit | 0.288 |
| Avg perm (kh-weighted) | **14,997 mD** ⚠️ |
| **Total kh** | **10,676,695 mD·m** ⚠️ |
| **Saturated samples** | **3,328 of 3,333 net** |

### 7.2 The headline number — and the asterisk

**Zone B contributes 10.7 million mD·m of kh** — 16× the next-largest
zone (Zone E at 1.2M). On the surface, this is the dominant flow zone
of the entire field.

**The asterisk:** 99.85% of Zone B's net samples are at the 15,000 mD
tool ceiling. The kh of 10.7M is the integral of `perm × dz` where
nearly every `perm` is exactly 15,000 — the tool's upper limit, not
the real value.

The true Zone B kh is **higher than 10.7M, by an unknown multiple.**
If the real perm is 25,000 mD on average, the true kh is closer to
18M. If it's 50,000 mD, the true kh is closer to 35M. We can't tell.

### 7.3 Why the arithmetic mean of perm is 14,997 mD

Of 3,333 net samples, **3,328 are at 15,000 mD**. Only 5 samples are
below the ceiling. The arithmetic mean is forced to within ~3 mD of
the ceiling by construction.

This is the diagnostic signature of saturation collapse — when 99.85%
of samples have an identical value, every mean-based metric reduces
to that value.

### 7.4 Lorenz coefficient ≈ 0.00 — the inevitable consequence

The Lorenz coefficient measures heterogeneity. If every sample has the
same perm value, every sample contributes equally to flow, and the
Lorenz curve glues to the 45° diagonal — Lorenz coefficient ≈ 0.

**Zone B's Lorenz ≈ 0.00 is not a homogeneity finding.** It's the
mathematical guarantee of saturation. Two sub-intervals with true perm
of 20,000 mD and 80,000 mD both report as 15,000 mD, and so register
as identically contributing. Heterogeneity that exists in the rock is
invisible to the instrument and therefore invisible to the metric.

### 7.5 Per-well consistency

Zone B is consistent across wells:
- NTG: 0.91-0.94 (very tight)
- Avg phit: 0.286-0.292 (almost identical)
- Saturation count per well: 151-789

The high saturation count in well 7 (789) is what makes well 7 the kh
leader. But every well's Zone B looks essentially the same in terms of
quality — they differ mainly in **thickness** and in **how heavily the
tool ceiling has been hit.**

### 7.6 The downstream consequence

- **Part C.1 sweep:** Zone B's NTG plateaus at 93% by cutoff 0.55 —
  cutoff choice doesn't matter, the zone is clean by lithology
  regardless.
- **Part C.2 Lorenz chart:** Zone B's curve glued to the diagonal is
  the textbook example of saturation collapse.
- **Part D clustering:** Zone B's sub-zones 1 and 2 have log_perm
  centroids of 4.175938 and 4.176091 — indistinguishable. The
  clustering "succeeds" statistically but is geologically meaningless.

Zone B's story is **the single most important finding** in the
deliverable.

---

## 8. Zone C — heterogeneous secondary reservoir

### 8.1 Field rollup

| Metric | Value |
|--------|------:|
| Gross thickness | **1,094.3 m** (thickest zone) |
| Net thickness | 915.0 m |
| **NTG** | **0.84** |
| Avg phit | 0.203 |
| Avg perm (kh-weighted) | 743 mD |
| Total kh | 679,837 mD·m |
| Saturated samples | 17 (0.4%) |
| **Lorenz** | **~0.65** ⭐ |

### 8.2 What makes Zone C interesting

**Lorenz coefficient ≈ 0.65.** That's the **highest among
non-saturated zones**, and it tells you that within Zone C, flow
capacity is unequally distributed. Some sub-intervals are carrying
far more than their share.

Combined with:
- **The thickest zone in the field** (1,094 m gross)
- **84% NTG** — most of it is reservoir
- **Only 0.4% saturation** — the instrument actually sees Zone C's
  perm range honestly

…Zone C is the natural candidate for sub-zoning. **And in Part D,
clustering successfully splits it into 3 reproducible sub-zones with
LOWO ARI 0.991.**

### 8.3 The three latent sub-zones (foreshadow to Part D)

Part D found three Zone C sub-zones with monotonically improving
quality:
- Sub-zone 0 (poor): ~70 mD perm, vsh ~0.51
- Sub-zone 1 (moderate): ~230 mD perm, vsh ~0.33
- Sub-zone 2 (best): ~744 mD perm, vsh ~0.22

The Lorenz coefficient of 0.65 — computed in Part B — is what predicted
this structure existed. Lorenz is the bridge from "this zone is
heterogeneous" to "let's go find the sub-structure."

### 8.4 Per-well consistency

Zone C is consistent across wells:
- NTG: 0.80-0.87
- Avg phit: 0.201-0.204 (tight)
- Avg perm: 669-817 mD

Heterogeneity is **within** Zone C, not between wells. That's what makes
the sub-zoning analysis work — the same three sub-zones exist
everywhere, just at different depths and thicknesses.

---

## 9. Zone D — tight rock

### 9.1 Field rollup

| Metric | Value |
|--------|------:|
| Gross thickness | 513.3 m |
| Net thickness | **52.9 m** |
| **NTG** | **0.10** |
| Avg phit | 0.092 |
| Avg perm (kh-weighted) | **0.79 mD** |
| Total kh | **42 mD·m** |
| Saturated samples | **0** |

### 9.2 Three orders of magnitude below everything else

Zone D's total kh of 42 mD·m is:
- 10 million × lower than Zone B's 10.7M
- 16,000 × lower than Zone E's 1.2M
- 6,300 × lower than Zone A's 267K

This is not a marginal reservoir. This is **non-reservoir**.

### 9.3 Why it's non-reservoir — the binding constraint

The vsh cutoff (≤ 0.5) is **not** what's blocking Zone D. The binding
constraint is **phit ≥ 0.08**:

- Average phit in Zone D's net interval is 0.092 — barely above the
  cutoff
- Average perm is **0.79 mD** — sub-millidarcy

Even if we relaxed vsh to 0.70 (Part C.1's permissive end),
Zone D's NTG only climbs to 0.29. Even at the loosest cutoff, most of
Zone D fails the porosity test. **It's tight rock, period.**

### 9.4 Zero saturated samples — confirms it's not a tool artefact

Unlike Zone B, where 99.85% saturation makes the result a tool
limitation, Zone D has **zero saturated samples**. The 0.79 mD perm
is a real measurement, not a censored one. The instrument is fully
visible here — and what it sees is sub-millidarcy rock.

### 9.5 Per-well consistency

Zone D is the most consistent zone in the dataset:
- NTG: 0.06-0.14
- Avg phit: 0.090-0.095
- Avg perm: 0.6-0.9 mD

Every well sees the same Zone D — **tight rock, field-wide, robustly
unproductive.**

### 9.6 Why this finding is robust

Part C.1 confirms Zone D's status holds across **every cutoff** tested.
At the strictest cutoff (vsh ≤ 0.30), Zone D's field NTG is 0.008
(less than 1%). At the loosest (vsh ≤ 0.70), it's 0.29. **The ceiling
of 29% means Zone D is non-reservoir at any reasonable definition.**

---

## 10. Zone E — deep reliable reservoir

### 10.1 Field rollup

| Metric | Value |
|--------|------:|
| Gross thickness | 839.1 m |
| Net thickness | 586.8 m |
| **NTG** | **0.70** |
| Avg phit | 0.205 |
| Avg perm (kh-weighted) | **2,045 mD** |
| Total kh | **1,201,733 mD·m** |
| Saturated samples | 39 (1.4%) |

### 10.2 The most defensible high-perm zone

Zone E carries the second-largest total kh in the field (1.2M mD·m,
behind only Zone B's saturation-inflated 10.7M). The key difference
from Zone B: **only 1.4% saturation.**

That means:
- Average perm of **2,045 mD** is a real number, not a ceiling
- Total kh of 1.2M is a **defensible** estimate, not a lower bound
- Reservoir-engineering calculations using Zone E's perm distribution
  are trustworthy

### 10.3 Why Zone E may be more important than headline rankings suggest

When you rank zones by kh:
1. Zone B: 10.7M (but real value is much higher than this — lower bound)
2. Zone E: 1.2M (real value)
3. Zone C: 680K (real value)
4. Zone A: 267K (real value)
5. Zone D: 42 (real value)

For **uncertain reservoir engineering**, you want kh numbers you can
trust. **Zone E's 1.2M is the largest defensible kh in the field.**
Zone B's headline is bigger, but its lower-bound status means any
flow calculation based on it carries unbounded upside.

### 10.4 Per-well consistency

- NTG: 0.68-0.73
- Avg phit: 0.202-0.207
- Avg perm: 1,842-2,213 mD

Consistent and reliable. Zone E is the kind of zone a development
team wants — predictable, high perm, low censoring.

---

## 11. Well-level rollup and the well 7 paradox

### 11.1 Per-well summary

| Well | Net (m) | NTG | kh (mD·m) | Saturated count |
|---:|---:|---:|---:|---:|
| 1 | 392.0 | 0.74 | 2,266,121 | 662 |
| 2 | 462.2 | 0.68 | 1,763,870 | 466 |
| 3 | 291.6 | **0.75** | 1,405,687 | 395 |
| 4 | 438.2 | 0.67 | 1,670,935 | 457 |
| 5 | 355.0 | 0.67 | 1,434,821 | **152** |
| 6 | 408.0 | 0.66 | 1,692,769 | 454 |
| **7** | 385.6 | 0.70 | **2,591,532** ⭐ | **798** ⚠️ |

### 11.2 Three well-level observations

**Observation 1 — Well 7 leads on kh AND on saturation.**

Well 7 has the highest total kh (2.59M mD·m) AND the highest saturated
sample count (798). These go together — saturation inflates the
visible kh up to the tool ceiling, then leaves the true value
unknowable. **The bound is loosest where the headline number is
largest.**

Well 7's true kh is **higher than 2.59M, by an unknown multiple.**
If we corrected for the tool ceiling, the gap between well 7 and the
rest of the field would likely widen further.

**Observation 2 — Well 3 has the highest NTG despite being the
smallest.**

Well 3 has only 390 m of gross thickness (the smallest well) but the
highest NTG (0.75). Per metre drilled, well 3 is the most efficient
well in the field — though it also carries the only NaN porosity
issue (78 samples lost to tool malfunction).

**Observation 3 — Well 5 is the low-censoring reference.**

Well 5's 152 saturated samples is the lowest count by a wide margin.
Partly this reflects its 0.5 m step (fewer samples overall), but
even normalized to its sample count, well 5's saturation fraction is
genuinely lower (~15%). For any comparison where you want a baseline
**uncensored** view of the field, well 5 is the cleanest reference.

### 11.3 The well-ranking caveat

The headline well kh ranking (well 7 first, well 1 second) is **partly
an instrument artefact**. Wells with more saturated samples report
inflated lower-bound kh. A reviewer asking "which well is best?"
should be told:

> "Well 7 leads on visible kh, but it's also the most censored.
> A more defensible ranking would weight by saturation fraction —
> well 5 is the most reliable single-well view, well 1 is a good
> compromise, well 7's true number is unknowable from this dataset
> alone."

---

## 12. Interview prep — short answers

### "Walk me through Part B."

> "Part B computes the five required metrics per (well, zone) — gross
> thickness, net thickness, average porosity, average permeability,
> and kh — plus seven bonus diagnostics including NTG, kh-weighted
> mean perm, Lorenz coefficient, and saturation counts. The output is
> a 35-row × 12-column tidy DataFrame, plus two rollup tables by zone
> and by well. The findings split into five clear zone signatures and
> one critical caveat: Zone B's headline kh of 10.7M is a lower bound,
> because 99.85% of its net samples are at the tool ceiling."

### "Why did you add bonus columns?"

> "Three of them earn their place by answering specific questions the
> required metrics leave open. **NTG** turns 'net = 466 m' into 'this
> is 63% reservoir-quality rock', which is more interpretable.
> **kh-weighted average perm** is the engineering-correct mean when
> dz varies between wells. **Lorenz coefficient** signals internal
> heterogeneity — Zone C's 0.65 is what motivated the Part D
> clustering. The other four are sanity counts that make the
> reviewer's job easier."

### "How do you handle NaN porosity?"

> "Exclude conservatively, count visibly. Samples with NaN phit are
> excluded from the net mask because missing data is not reservoir.
> But the count of excluded samples appears in `n_phit_nan`, so the
> reviewer can see exactly how much thickness was potentially lost.
> Well 3 has 78 NaN values across all five zones — about 4% of well
> 3's samples — so well 3's net is technically a lower bound."

### "Why do you keep saturated samples in kh?"

> "Two reasons. First, dropping them would systematically
> under-estimate flow capacity — they're real samples carrying real
> flow, just at the upper measurement limit. Second, by keeping them
> and counting them in `n_perm_saturated_in_net`, the lower-bound
> nature of kh is **visible**. Every kh number in the table is
> annotated with its saturated count. If I had dropped the samples,
> kh would have been smaller and reviewers would have had no way to
> tell that any censoring had occurred."

### "Why is Zone B's Lorenz coefficient zero?"

> "Mathematical inevitability. The Lorenz coefficient measures
> heterogeneity. If 99.85% of Zone B's samples have an identical perm
> value, by construction they all contribute equally to flow, and the
> Lorenz curve collapses to the 45° diagonal — coefficient ≈ 0. This
> is not a homogeneity finding. It's the diagnostic signature of
> saturation. Two sub-intervals with true perm of 20,000 mD and
> 80,000 mD both register as 15,000 mD; the tool is blind to their
> difference, and so is any heterogeneity metric computed from those
> measurements."

### "Which zone deserves the most attention?"

> "Two answers depending on what you're optimizing. **For maximum
> visible kh**, Zone B — but its number is a lower bound by an
> unknown multiple. **For maximum defensible kh**, Zone E — its 1.2M
> mD·m is a real measurement, with only 1.4% saturation. For a
> development decision, I'd target Zone E as the primary high-perm
> zone and treat Zone B's true magnitude as a key uncertainty to
> resolve with core or production data."

### "Why is Zone D non-reservoir?"

> "Three orders of magnitude. Total kh is 42 mD·m, compared to 267,000
> for Zone A and over a million for Zone E. Average perm is sub-1 mD.
> NTG is 10% at default cutoffs and never exceeds 29% even at the
> loosest cutoff Part C.1 tested. Zero saturated samples means this
> is a real measurement, not a tool artefact. The binding constraint
> is porosity, not shaliness — most of Zone D fails the phit ≥ 0.08
> threshold, regardless of how vsh is set. Zone D is tight rock,
> field-wide, robustly unproductive."

### "What's the well 7 paradox?"

> "Well 7 has the highest kh in the field (2.59M mD·m) AND the highest
> saturated sample count (798). The two go together. Saturation
> pushes visible perm up to the tool ceiling, inflating apparent kh
> while making the true value unknowable. Well 7's true kh is higher
> than its reported number, by an unknown multiple. So when ranking
> wells, well 7 leads — but the gap to the rest of the field could
> be even larger than the table suggests, and the absolute number
> shouldn't be trusted for downstream reservoir calculations."

### "If you had one more day, what would you add?"

> "Three things. First, **a saturation-corrected kh estimate** for
> Zone B — using order-of-magnitude bounds from typical
> sandstone-perm distributions, I could give an upper bound to pair
> with the current lower bound. Second, **a per-zone uncertainty
> column** that combines saturation fraction and NaN fraction into a
> single 'how much do I trust this number' index. Third, **a
> sample-count vs depth-weighted comparison** — show that the
> depth-weighting is doing its job by demonstrating well 5's metrics
> match what they would have been at 0.2 m sampling."

### "Summarize Part B in one sentence."

> "Thirty-five (well, zone) rows with five required metrics and seven
> bonus diagnostics, telling five distinct zone stories: Zone A clean
> top reservoir, Zone B saturation-capped flow champion with a lower-
> bound kh of 10.7M, Zone C heterogeneous secondary that motivates
> Part D's clustering, Zone D non-reservoir tight rock at any cutoff,
> and Zone E the most defensible high-perm zone at 2,045 mD."
