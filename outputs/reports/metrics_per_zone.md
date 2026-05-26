# Reservoir Metrics per (Well, Zone) — Part B

**Deliverable:** Per-(well, zone) analytical table covering the five required
metrics from the assignment plus seven bonus diagnostics that surface real-data
caveats (tool saturation, NaN porosity, flow heterogeneity).

**Input:** `data/processed/master_table.parquet` — 18,167 depth samples joined
to 35 zone tops (Part A output).

**Cutoffs:** `vsh_max = 0.5`, `phit_min = 0.08` (data-dictionary defaults).

**Output files:**
- `outputs/reports/metrics_per_zone.csv` — full 35-row table (this report)
- `outputs/reports/field_summary_by_zone.csv` — 5 rows (rolled up to zone)
- `outputs/reports/field_summary_by_well.csv` — 7 rows (rolled up to well)

---

## 1. Required metrics

For each (well, zone) group, the five required metrics are computed as follows.

| Metric | Definition | Formula |
|---|---|---|
| Gross thickness | Total interval length of the zone | `sum(dz)` over all rows in the group |
| Net reservoir thickness | Thickness where `vsh ≤ 0.5` AND `phit ≥ 0.08` | `sum(dz)` over rows passing the net mask |
| Avg phit (net) | Mean porosity in the net interval | `mean(phit)` over net rows |
| Avg perm (net) | Arithmetic mean permeability in the net interval | `mean(perm)` over net rows |
| kh (net) | Flow capacity in the net interval | `sum(perm × dz)` over net rows |

**NaN handling.** Samples with NaN `vsh` or `phit` are excluded from net.
This is the conservative choice — missing data is not reservoir. The count
is reported separately as `n_phit_nan` so the exclusion is visible.

**Saturated samples.** Permeability values at or above 14999 mD are kept in
the kh calculation. Censoring them would systematically under-estimate flow
capacity. The count is reported as `n_perm_saturated_in_net` so reviewers
see exactly where the kh estimate is a lower bound.

---

## 2. Bonus diagnostics

| Metric | Why it's included |
|---|---|
| NTG (`ntg`) | Net-to-gross ratio = `net_thickness / gross_thickness`. Standard reservoir-quality indicator. |
| kh-weighted avg perm | `kh / net_thickness`. Engineering-correct mean when sampling step varies. |
| Lorenz coefficient | Flow heterogeneity index in [0, 1]. 0 = uniform, 1 = single super-streak. Signals zones that may need sub-zoning. |
| `n_samples_net` | Sanity check — how many samples passed the net mask. |
| `n_phit_nan` | NaN porosity samples excluded from net (well_3 has 78). |
| `n_perm_saturated_in_net` | Net samples at the 15000 mD tool ceiling. Surfaces lower-bound kh. |

---

## 3. Per-(well, zone) results — 35 rows

Showing the most consequential columns. Full table is in
`outputs/reports/metrics_per_zone.csv`.

### Well 1

| Zone | Gross (m) | Net (m) | NTG | Avg phit | Avg perm (mD) | kh (mD·m) | Lorenz | N saturated |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| A | 74.8 | 48.4 | 0.65 | 0.170 | 502.5 | 24,323 | 0.43 | 0 |
| B | 141.8 | 131.0 | 0.92 | 0.291 | 15,000 | **1,965,000** | 0.00 ⚠ | **655** |
| C | 136.2 | 110.6 | 0.81 | 0.201 | 709.5 | 78,471 | 0.63 | 1 |
| D | 37.6 | 4.6 | 0.12 | 0.092 | 0.8 | 4 | 0.45 | 0 |
| E | 139.8 | 97.4 | 0.70 | 0.207 | 2,036 | 198,323 | 0.51 | 6 |

### Well 2

| Zone | Gross (m) | Net (m) | NTG | Avg phit | Avg perm (mD) | kh (mD·m) | Lorenz | N saturated |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| A | 119.2 | 79.0 | 0.66 | 0.171 | 576.8 | 45,567 | 0.45 | 0 |
| B | 96.4 | 90.4 | 0.94 | 0.288 | 14,999 | 1,355,876 | 0.00 ⚠ | 451 |
| C | 209.4 | 176.6 | 0.84 | 0.204 | 816.7 | 144,221 | 0.68 | 5 |
| D | 109.6 | 10.0 | 0.09 | 0.094 | 0.8 | 8 | 0.44 | 0 |
| E | 145.6 | 106.2 | 0.73 | 0.205 | 2,055 | 218,197 | 0.52 | 10 |

### Well 3

| Zone | Gross (m) | Net (m) | NTG | Avg phit | Avg perm (mD) | kh (mD·m) | Lorenz | N saturated | N phit NaN |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| A | 60.6 | 37.4 | 0.62 | 0.173 | 619.4 | 23,167 | 0.47 | 0 | **15** |
| B | 84.6 | 77.0 | 0.91 | 0.288 | 15,000 | 1,155,000 | 0.00 ⚠ | 385 | **14** |
| C | 133.0 | 106.4 | 0.80 | 0.203 | 748.9 | 79,682 | 0.65 | 3 | **31** |
| D | 11.8 | 1.2 | 0.10 | 0.090 | 0.9 | 1 | 0.41 | 0 | 0 |
| E | 100.2 | 69.6 | 0.69 | 0.207 | 2,124 | 147,838 | 0.51 | 7 | **18** |

> **Well 3 anomaly.** 78 porosity samples (4% of well_3) are NaN, distributed
> across all five zones. These samples are excluded from net by the conservative
> NaN-handling policy. Net thicknesses for well_3 are therefore lower bounds —
> if those measurements had succeeded, additional thickness could have qualified.

### Well 4

| Zone | Gross (m) | Net (m) | NTG | Avg phit | Avg perm (mD) | kh (mD·m) | Lorenz | N saturated |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| A | 149.8 | 92.4 | 0.62 | 0.172 | 589.0 | 54,426 | 0.46 | 0 |
| B | 96.8 | 90.6 | 0.94 | 0.286 | 14,996 | 1,358,676 | 0.00 ⚠ | 452 |
| C | 199.2 | 166.0 | 0.83 | 0.203 | 669.9 | 111,199 | 0.62 | 1 |
| D | 89.0 | 9.6 | 0.11 | 0.094 | 0.7 | 7 | 0.35 | 0 |
| E | 115.4 | 79.6 | 0.69 | 0.202 | 1,842 | 146,628 | 0.51 | 4 |

### Well 5 (0.5 m sampling step)

| Zone | Gross (m) | Net (m) | NTG | Avg phit | Avg perm (mD) | kh (mD·m) | Lorenz | N saturated |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| A | 112.5 | 67.0 | 0.60 | 0.171 | 622.0 | 41,672 | 0.48 | 0 |
| B | 80.5 | 75.5 | 0.94 | 0.292 | 15,000 | 1,132,500 | 0.00 ⚠ | 151 |
| C | 157.5 | 135.0 | 0.86 | 0.203 | 734.0 | 99,096 | 0.64 | 0 |
| D | 76.5 | 4.5 | 0.06 | 0.090 | 0.6 | 3 | 0.30 | 0 |
| E | 103.5 | 73.0 | 0.71 | 0.206 | 2,213 | 161,550 | 0.53 | 1 |

> **Well 5 sampling step.** Uses 0.5 m vertical step versus 0.2 m for the
> other six wells. The per-well `dz` computation in the joiner handles this
> transparently — kh in well_5 multiplies perm by 0.5 m thickness per sample,
> not 0.2 m.

### Well 6

| Zone | Gross (m) | Net (m) | NTG | Avg phit | Avg perm (mD) | kh (mD·m) | Lorenz | N saturated |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| A | 125.8 | 78.0 | 0.62 | 0.173 | 584.3 | 45,572 | 0.46 | 0 |
| B | 95.0 | 89.4 | 0.94 | 0.287 | 14,988 | 1,339,889 | 0.00 ⚠ | 445 |
| C | 155.8 | 131.0 | 0.84 | 0.203 | 748.4 | 98,039 | 0.63 | 2 |
| D | 98.2 | 10.6 | 0.11 | 0.095 | 0.9 | 9 | 0.48 | 0 |
| E | 145.4 | 99.0 | 0.68 | 0.205 | 2,114 | 209,260 | 0.54 | 7 |

### Well 7

| Zone | Gross (m) | Net (m) | NTG | Avg phit | Avg perm (mD) | kh (mD·m) | Lorenz | N saturated |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| A | 97.0 | 63.8 | 0.66 | 0.170 | 512.6 | 32,701 | 0.43 | 0 |
| B | 170.2 | 158.0 | 0.93 | 0.288 | 14,998 | **2,369,754** | 0.00 ⚠ | **789** |
| C | 103.2 | 89.4 | 0.87 | 0.203 | 773.3 | 69,130 | 0.69 | 5 |
| D | 90.6 | 12.4 | 0.14 | 0.093 | 0.8 | 10 | 0.42 | 0 |
| E | 89.2 | 62.0 | 0.70 | 0.205 | 1,934 | 119,937 | 0.51 | 4 |

> **Well 7 has the highest single kh in the field** (2.37M mD·m in Zone B)
> AND the highest saturation count (789 samples capped). The two go together —
> the bound is loosest where the headline number is largest. Well 7 leads the
> ranking, but the true gap to the rest of the field could be larger than the
> table suggests.

---

## 4. Field rollup by zone

| Zone | N wells | Gross total (m) | Net total (m) | NTG (field) | Avg phit (mean) | Avg perm kh-w (mean, mD) | kh total (mD·m) |
|---|---:|---:|---:|---:|---:|---:|---:|
| A | 7 | 739.7 | 466.0 | 0.63 | 0.171 | 572 | 267,428 |
| B | 7 | 765.3 | 711.9 | 0.93 | 0.288 | **14,997** ⚠ | **10,676,695** ⚠ |
| C | 7 | 1,094.3 | 915.0 | 0.84 | 0.203 | 743 | 679,837 |
| D | 7 | 513.3 | 52.9 | **0.10** | 0.092 | 0.79 | 42 |
| E | 7 | 839.1 | 586.8 | 0.70 | 0.205 | 2,045 | 1,201,733 |

**Five distinct zone signatures emerge:**

- **Zone A — clean top reservoir.** 63% net, 17% porosity, ~570 mD perm,
  no saturation. Reliable baseline.
- **Zone B — saturation-capped flow champion.** Headline kh of 10.7M mD·m is
  a hard lower bound: virtually every net sample is at the 15000 mD ceiling.
  Lorenz collapses to ~0 because the tool can't distinguish a real-perm
  streak from one further up. The actual flow capacity is likely several
  multiples higher.
- **Zone C — secondary reservoir with internal heterogeneity.** Thickest
  interval (1094 m gross), 84% net, but Lorenz around 0.65 signals strong
  internal variability. This is the zone that motivates the sub-zone
  clustering in Part D.
- **Zone D — tight rock.** 10% NTG, sub-1 mD average perm, kh of 42 mD·m
  across the entire field — three orders of magnitude below the others.
  Zero saturated samples, so this isn't an instrument artefact. Cutting
  vsh further wouldn't help; phit is the binding constraint. Zone D is
  effectively non-reservoir.
- **Zone E — deep reservoir.** 70% net, 2045 mD perm with only minor
  saturation. Among the high-perm zones, Zone E provides the most reliable
  flow capacity estimate because its kh is not heavily censored.

---

## 5. Field rollup by well

| Well | N zones | Gross total (m) | Net total (m) | NTG (well) | kh total (mD·m) | N saturated |
|---|---:|---:|---:|---:|---:|---:|
| 1 | 5 | 530.2 | 392.0 | 0.74 | 2,266,121 | 662 |
| 2 | 5 | 680.2 | 462.2 | 0.68 | 1,763,870 | 466 |
| 3 | 5 | 390.2 | 291.6 | 0.75 | 1,405,687 | 395 |
| 4 | 5 | 650.2 | 438.2 | 0.67 | 1,670,935 | 457 |
| 5 | 5 | 530.5 | 355.0 | 0.67 | 1,434,821 | **152** ⓘ |
| 6 | 5 | 620.2 | 408.0 | 0.66 | 1,692,769 | 454 |
| 7 | 5 | 550.2 | 385.6 | 0.70 | **2,591,532** | **798** |

**Well-level observations:**

- **Well 7 leads the kh ranking** (2.59M mD·m) but is also the most censored
  (798 saturated samples = 30% of its samples). Any well-to-well kh
  comparison must surface this differential censoring.
- **Well 3 has the highest NTG** (0.75) despite being the smallest well by
  gross thickness (390 m). It also carries the dataset's only missing-value
  anomaly — 78 NaN porosity samples concentrated entirely in well_3.
- **Well 5 has the lowest absolute saturation count** (152) — partly because
  it has the fewest samples overall due to its 0.5 m step, but also a
  genuinely lower saturation fraction. Useful as a low-censoring reference.

---

## 6. Design choices

| Choice | Why |
|---|---|
| Cutoffs are parameters, not constants | Part C.1 reuses the same function to sweep `vsh_max` across nine values. |
| NaN porosity excluded from net | Missing data ≠ reservoir. Counted separately to keep the exclusion visible. |
| Saturated perm kept in kh | Censoring would systematically under-estimate flow. Count is surfaced so kh's lower-bound nature is explicit. |
| Lorenz computed on net only | Heterogeneity within the reservoir is the question; non-reservoir samples shouldn't dilute the signal. |
| Per-well `dz` from the joiner | Well 5's 0.5 m step is handled transparently — kh and net_thickness use the right thickness per sample. |
| Series → groupby → DataFrame | `compute_zone_metrics` returns a Series so `groupby(...).apply` produces a tidy 35-row frame in one step. |

---

## 7. How to reproduce

```bash
python -m src.cli metrics
# Reads:  data/processed/master_table.parquet
# Writes: outputs/reports/metrics_per_zone.csv
#         outputs/reports/field_summary_by_zone.csv
#         outputs/reports/field_summary_by_well.csv
#         data/processed/metrics_per_zone.parquet
```

Override cutoffs at runtime:

```bash
python -m src.cli metrics --vsh-max 0.4 --phit-min 0.10
```

Tests covering this module:

```bash
pytest tests/test_metrics.py -v
# 42 tests, ~99% coverage of src/analytics/metrics.py
```
