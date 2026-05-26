# Part A — Complete Walkthrough

**Data Loading, Joining, and Quality Assessment**

This is the unified walkthrough of Part A. It covers what we did, why
we did it, every quality issue we found, and every interview answer.
The technical document `data_quality.md` remains the authoritative
machine-readable QC report; this file is the human-readable
read-through that ties it together with the story.

---

## Table of contents

1. [What Part A asks for](#1-what-part-a-asks-for)
2. [What we built](#2-what-we-built)
3. [Step 1 — Loading the raw CSVs](#3-step-1--loading-the-raw-csvs)
4. [Step 2 — Joining wells with zones](#4-step-2--joining-wells-with-zones)
5. [Step 3 — Quality assessment](#5-step-3--quality-assessment)
6. [Finding 1 — The saturation discovery](#6-finding-1--the-saturation-discovery)
7. [Finding 2 — Well 5 sampling anomaly](#7-finding-2--well-5-sampling-anomaly)
8. [Finding 3 — Well 3 missing phit values](#8-finding-3--well-3-missing-phit-values)
9. [The master table — final shape](#9-the-master-table--final-shape)
10. [How findings propagate to Parts B, C, D](#10-how-findings-propagate-to-parts-b-c-d)

---

## 1. What Part A asks for

The case statement asks for **data integration and quality assessment**:

- Load multi-well log data
- Join with zone information
- Identify and document data quality issues
- Build a clean, analysis-ready master table

The case explicitly mentions that the dataset has been deliberately
constructed with quality issues that the candidate must discover and
handle.

---

## 2. What we built

| Deliverable | Format | Location |
|-------------|--------|----------|
| Master table (analysis-ready) | Parquet | `data/processed/master_table.parquet` |
| Per-well QC summary | CSV | (in master table columns) |
| Quality report | Markdown | `outputs/reports/data_quality.md` |
| This walkthrough | Markdown | `outputs/reports/part_a_walkthrough.md` |

Pipeline orchestration:

```bash
python -m src.cli quality
```

Single command. Loads 7 well CSVs + zones CSV, joins them, runs quality
checks, writes the master table and QC report.

---

## 3. Step 1 — Loading the raw CSVs

### 3.1 Input files

```
data/raw/
├── well_1.csv      96 KB
├── well_2.csv     123 KB
├── well_3.csv      70 KB
├── well_4.csv     117 KB
├── well_5.csv      38 KB  ← smallest (anomaly hint)
├── well_6.csv     112 KB
├── well_7.csv      99 KB
└── zones.csv      436 B   ← single small file
```

Total: ~660 KB of raw data spread across 8 files.

### 3.2 Per-well schema

Each well CSV has the same columns:

| Column | Type | Description |
|--------|------|-------------|
| `depth` | float | Measured depth in metres |
| `vsh` | float | Shale volume fraction (0-1) |
| `phit` | float | Total porosity fraction (0-1) |
| `perm` | float | Permeability in mD |
| `sw` | float | Water saturation fraction (0-1) |

### 3.3 Zones table schema

```
zones.csv columns: well_id, zone_id, top_depth, base_depth
```

This is the **lookup table** that maps depth ranges to zone labels
(A, B, C, D, E) per well. Each well has 5 zone records (one per zone),
giving 35 rows total.

### 3.4 Loader implementation (`src/data/loader.py`)

The loader:

1. **Reads each well CSV** with explicit schema validation
2. **Adds a `well_id` column** (1-7) for downstream joining
3. **Concatenates all 7 wells** into a single long-format DataFrame
4. **Validates schema** — column types, presence, no unexpected columns

Output: a long-format DataFrame with 18,167 rows (well × depth samples).

---

## 4. Step 2 — Joining wells with zones

### 4.1 The challenge — depth ranges, not exact matches

A well log has samples at every metre or half-metre interval; zones are
defined as **depth ranges** (top_depth to base_depth). A naive equality
join doesn't work because no sample's depth exactly equals a zone
boundary.

### 4.2 The solution — `merge_asof`

Pandas `merge_asof` performs a **range-based merge**. For each sample,
it finds the zone whose `top_depth` is the largest value still ≤ the
sample's depth. This assigns each sample to the zone that contains it.

```python
# Pseudocode
merge_asof(
    left=samples_sorted_by_depth,
    right=zones,
    by="well_id",          # join per-well separately
    left_on="depth",
    right_on="top_depth",
    direction="backward"   # find largest top_depth ≤ sample depth
)
```

### 4.3 Boundary validation

After the asof-merge, a sanity check ensures every sample's depth falls
within `[top_depth, base_depth]` of its assigned zone. Samples that
don't (e.g., depth below the deepest zone's base) are flagged and
either dropped or labelled "outside_zone."

### 4.4 Per-well depth step (dz) calculation

Each sample's `dz` (vertical thickness it represents) is computed as
the **gap between adjacent depth points within the same well**:

```python
dz = depth.diff()
```

This per-sample `dz` is what every Part B metric (net thickness,
kh = perm × dz, etc.) integrates over.

**Critical point:** `dz` is **per-well**, not global. Different wells
can have different sampling intervals — and one well does (Section 7).

---

## 5. Step 3 — Quality assessment

The QC module (`src/data/quality.py`) runs three families of checks:

### 5.1 Schema and type checks

- All required columns present
- Numeric types where expected
- No extra unexpected columns

**Result:** All 7 wells pass.

### 5.2 Range checks (physical sanity)

| Column | Expected range | Reason |
|--------|---------------|--------|
| `vsh` | [0, 1] | Volume fraction |
| `phit` | [0, 1] | Porosity fraction |
| `sw` | [0, 1] | Saturation fraction |
| `perm` | > 0 | Permeability is positive |
| `depth` | > 0 | Depth is positive |

**Result:** All values in valid physical ranges. No negative
permeabilities, no porosities > 1.

### 5.3 Missing-value checks

| Column | Total NaN count | Affected well |
|--------|----------------|---------------|
| `phit` | 78 | well_3 only |
| (others) | 0 | — |

**Result:** Only `phit` has missing values, only in well_3. Investigated
in Section 8.

### 5.4 Saturation flag

A boolean column `perm_saturated` is added: True wherever `perm >=
15000 mD`. This is the single most important quality flag in the entire
project. Its discovery is detailed in Section 6.

---

## 6. Finding 1 — The saturation discovery

This is **the single most important finding** in Part A and the one that
shapes the interpretation of every downstream result.

### 6.1 The observation

When inspecting the permeability distribution, an unusual pattern
appears: a large number of samples report `perm = 15000.0` to **machine
precision** — not 14,985, not 15,012, but exactly 15,000.

```
Distinct perm values near the maximum:
  14,892 mD  (1 sample)
  14,915 mD  (1 sample)
  14,937 mD  (1 sample)
  ...
  15,000 mD  (3,514 samples!)  ← anomaly
```

### 6.2 Interpretation — tool ceiling, not real measurement

A genuine permeability measurement near 15,000 mD would produce a
continuous distribution of values around that number. **The spike of
exactly 3,514 samples at exactly 15,000 mD is the signature of a tool
saturation ceiling** — the measurement instrument cannot record values
above 15,000 mD, so anything higher is recorded as exactly 15,000.

This is a standard limitation in petrophysical logging tools, but it
**must be flagged** because it changes how downstream metrics should be
interpreted.

### 6.3 Field-wide saturation footprint

| Scope | Saturated samples | Fraction |
|-------|-------------------|----------|
| **All samples** | 3,514 / 18,167 | **19.34%** |
| Per-well range | 14% - 30% | — |
| Well 7 (maximum) | ~30% | Highest tool saturation |

Detailed per-zone breakdown (which zone is hit hardest) is in Part B.

### 6.4 What it means for every downstream metric

| Metric | Effect of saturation |
|--------|---------------------|
| `kh = perm × dz` | Saturated samples contribute 15,000 × dz, not the (higher) true value → **kh is a lower bound** |
| `avg_perm_in_net` | Mean dragged down by capped values → **underestimates true mean** |
| Lorenz coefficient | All saturated samples have identical perm → **artificial uniformity** → Lorenz collapses to 0 |
| Clustering on perm | Saturated samples are indistinguishable → **clustering fails on this feature** |

Every downstream deliverable (Part B metrics, Part C charts, Part D
clustering) handles this issue either by surfacing the saturation count
explicitly or by working around the affected feature.

### 6.5 How we handled it

**We did not drop saturated samples.** Dropping them would:
- Bias kh estimates downward further (they're real samples contributing
  real flow)
- Remove information about which zones the tool struggled with

Instead, we **kept the samples and added a `perm_saturated` boolean
column**. Every downstream report annotates kh values with the
saturated count when present, so the reviewer can read both the kh
estimate and the implied uncertainty.

---

## 7. Finding 2 — Well 5 sampling anomaly

### 7.1 The observation

Computing the per-well depth step:

```
well 1: median dz = 0.2 m
well 2: median dz = 0.2 m
well 3: median dz = 0.2 m
well 4: median dz = 0.2 m
well 5: median dz = 0.5 m   ← anomaly
well 6: median dz = 0.2 m
well 7: median dz = 0.2 m
```

**Well 5 is sampled at 0.5 m intervals; every other well is at 0.2 m.**

### 7.2 Why it matters

Six of the seven wells have ~2,800 samples; well 5 has only ~1,000.
That's a 2.8× difference in sample density.

If we computed any metric as a simple sample count (e.g., "fraction of
samples meeting the net cutoff"), well 5 would systematically appear
to have less reservoir than it actually does — purely because of
sampling cadence, not geology.

### 7.3 The fix — depth-weighted everything

All Part B metrics integrate over `dz` rather than counting samples:

```python
net_thickness = (samples_meeting_cutoff[dz]).sum()
# NOT: samples_meeting_cutoff.count()
```

This makes the metrics **sample-cadence invariant**. Well 5's 0.5 m
samples each contribute 2.5× the thickness of a 0.2 m sample, so the
final thickness is what would have been obtained with finer sampling.

The `dz` column is computed per-well in the loader (Section 4.4), so
this invariance is automatic for every downstream metric.

### 7.4 Verification

Net thickness for well 5 (Zone B at default cutoff) matches the
expected order of magnitude given the gross zone thickness and the
field-wide Zone B NTG. The 0.5 m sampling does not produce an outlier
in any volume metric.

---

## 8. Finding 3 — Well 3 missing phit values

### 8.1 The observation

Well 3 has **78 rows with NaN porosity** (`phit = NaN`). Every other
well has zero NaN values.

```
well_3 phit NaN count: 78
all other wells: 0
```

### 8.2 Why these 78 — pattern check

The 78 NaN samples are not randomly distributed; they cluster in
specific depth intervals. This suggests a **tool malfunction at
specific depths** in well 3 rather than random sampling errors.

### 8.3 How we handled it

For Part A: the NaN samples are kept in the master table, flagged.
For Part B: any metric that requires `phit` (e.g., the `phit ≥ 0.08`
net-reservoir cutoff) automatically excludes NaN rows via pandas'
default NaN handling. **This is the safe default** — we don't impute
porosity from neighbouring depths because the missing intervals span
multiple metres, so neighbour-imputation could introduce systematic
bias.

### 8.4 Impact on metrics

78 / 18,167 = **0.43% of total samples**. The bias on field-wide
metrics is negligible. The bias on well_3-specific metrics is small
(~3% of well_3's samples) but worth disclosing in the QC report.

---

## 9. The master table — final shape

After loading, joining, and QC:

| Field | Value |
|-------|------:|
| **Total samples** | **18,167** |
| Wells | 7 |
| Zones | 5 (A, B, C, D, E) |
| Columns | 9 (depth, vsh, phit, perm, sw, well_id, zone_id, dz, perm_saturated) |
| File size | ~340 KB (parquet) |
| Format | Parquet (columnar, fast for downstream analytics) |

### 9.1 Per-well sample counts

| Well | Samples | Median dz | Saturated % |
|-----:|--------:|----------:|------------:|
| 1 | ~2,800 | 0.2 m | ~22% |
| 2 | ~2,800 | 0.2 m | ~16% |
| 3 | ~2,800 | 0.2 m | ~14% |
| 4 | ~2,800 | 0.2 m | ~17% |
| 5 | ~1,000 | **0.5 m** | ~15% |
| 6 | ~2,800 | 0.2 m | ~16% |
| 7 | ~2,800 | 0.2 m | **~30%** |
| **Total** | **18,167** | — | **19.34%** |

### 9.2 Why parquet, not CSV

- **Schema preserved** — column types travel with the file
- **Column-oriented** — downstream analytics that read a few columns
  are much faster
- **Compressed** — smaller than equivalent CSV
- **Standard for analytics pipelines** in Python (pandas, polars,
  duckdb all read it natively)

---

## 10. How findings propagate to Parts B, C, D

| Finding | Affects which Parts? | How |
|---------|---------------------|-----|
| **Saturation (19.34%)** | B, C, D | All kh estimates are lower bounds. Part C's Lorenz coefficient collapses for Zone B. Part D's Zone B clustering fails because two of three sub-zones have indistinguishable perm centroids. |
| **Well 5 anomaly (0.5 m dz)** | B, C | All metrics are depth-weighted (integrate over `dz`), so volumes are correct. No metric is biased by sample count. |
| **Well 3 NaN phit** | B | 0.43% of samples auto-excluded from any metric requiring phit. Negligible field-wide impact, small well-3-specific impact (disclosed). |

This is the value of doing Part A carefully: every downstream finding
in B, C, D rests on these three observations.

---
