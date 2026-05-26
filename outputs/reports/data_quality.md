# Data Quality Report (Part A)

## Summary

- **Total wells:** 7
- **Total depth samples:** 18,167
- **Zone tops defined:** 35
- **Unique zone names:** A, B, C, D, E
- **Field depth range:** 1800.00 – 2750.00 m

## Per-Well Inventory

|   well |   n_rows |   depth_min |   depth_max |   gross_thickness |   step_mode |   step_min |   step_max |   irregular_steps |
|-------:|---------:|------------:|------------:|------------------:|------------:|-----------:|-----------:|------------------:|
|      1 |     2651 |   1850.0000 |   2380.0000 |          530.0000 |      0.2000 |     0.2000 |     0.2000 |                 0 |
|      2 |     3401 |   2010.0000 |   2690.0000 |          680.0000 |      0.2000 |     0.2000 |     0.2000 |                 0 |
|      3 |     1951 |   1920.0000 |   2310.0000 |          390.0000 |      0.2000 |     0.2000 |     0.2000 |                 0 |
|      4 |     3251 |   2100.0000 |   2750.0000 |          650.0000 |      0.2000 |     0.2000 |     0.2000 |                 0 |
|      5 |     1061 |   1970.0000 |   2500.0000 |          530.0000 |      0.5000 |     0.5000 |     0.5000 |                 0 |
|      6 |     3101 |   1800.0000 |   2420.0000 |          620.0000 |      0.2000 |     0.2000 |     0.2000 |                 0 |
|      7 |     2751 |   2050.0000 |   2600.0000 |          550.0000 |      0.2000 |     0.2000 |     0.2000 |                 0 |

## Missing Values

|   well | column   |   n_missing |   fraction_missing |
|-------:|:---------|------------:|-------------------:|
|      1 | vsh      |           0 |             0.0000 |
|      1 | phit     |           0 |             0.0000 |
|      1 | sw       |           0 |             0.0000 |
|      1 | perm     |           0 |             0.0000 |
|      2 | vsh      |           0 |             0.0000 |
|      2 | phit     |           0 |             0.0000 |
|      2 | sw       |           0 |             0.0000 |
|      2 | perm     |           0 |             0.0000 |
|      3 | vsh      |           0 |             0.0000 |
|      3 | phit     |          78 |             0.0400 |
|      3 | sw       |           0 |             0.0000 |
|      3 | perm     |           0 |             0.0000 |
|      4 | vsh      |           0 |             0.0000 |
|      4 | phit     |           0 |             0.0000 |
|      4 | sw       |           0 |             0.0000 |
|      4 | perm     |           0 |             0.0000 |
|      5 | vsh      |           0 |             0.0000 |
|      5 | phit     |           0 |             0.0000 |
|      5 | sw       |           0 |             0.0000 |
|      5 | perm     |           0 |             0.0000 |
|      6 | vsh      |           0 |             0.0000 |
|      6 | phit     |           0 |             0.0000 |
|      6 | sw       |           0 |             0.0000 |
|      6 | perm     |           0 |             0.0000 |
|      7 | vsh      |           0 |             0.0000 |
|      7 | phit     |           0 |             0.0000 |
|      7 | sw       |           0 |             0.0000 |
|      7 | perm     |           0 |             0.0000 |

## Range Validity (samples outside data_dictionary ranges)

|   well | column   |   valid_min |   valid_max |   below_min |   above_max |   total_out_of_range |
|-------:|:---------|------------:|------------:|------------:|------------:|---------------------:|
|      1 | vsh      |      0.0000 |      1.0000 |           0 |           0 |                    0 |
|      1 | phit     |      0.0000 |      0.5000 |           0 |           0 |                    0 |
|      1 | sw       |      0.0000 |      1.0000 |           0 |           0 |                    0 |
|      1 | perm     |      0.0010 |  15000.0000 |           0 |           0 |                    0 |
|      2 | vsh      |      0.0000 |      1.0000 |           0 |           0 |                    0 |
|      2 | phit     |      0.0000 |      0.5000 |           0 |           0 |                    0 |
|      2 | sw       |      0.0000 |      1.0000 |           0 |           0 |                    0 |
|      2 | perm     |      0.0010 |  15000.0000 |           0 |           0 |                    0 |
|      3 | vsh      |      0.0000 |      1.0000 |           0 |           0 |                    0 |
|      3 | phit     |      0.0000 |      0.5000 |           0 |           0 |                    0 |
|      3 | sw       |      0.0000 |      1.0000 |           0 |           0 |                    0 |
|      3 | perm     |      0.0010 |  15000.0000 |           0 |           0 |                    0 |
|      4 | vsh      |      0.0000 |      1.0000 |           0 |           0 |                    0 |
|      4 | phit     |      0.0000 |      0.5000 |           0 |           0 |                    0 |
|      4 | sw       |      0.0000 |      1.0000 |           0 |           0 |                    0 |
|      4 | perm     |      0.0010 |  15000.0000 |           0 |           0 |                    0 |
|      5 | vsh      |      0.0000 |      1.0000 |           0 |           0 |                    0 |
|      5 | phit     |      0.0000 |      0.5000 |           0 |           0 |                    0 |
|      5 | sw       |      0.0000 |      1.0000 |           0 |           0 |                    0 |
|      5 | perm     |      0.0010 |  15000.0000 |           0 |           0 |                    0 |
|      6 | vsh      |      0.0000 |      1.0000 |           0 |           0 |                    0 |
|      6 | phit     |      0.0000 |      0.5000 |           0 |           0 |                    0 |
|      6 | sw       |      0.0000 |      1.0000 |           0 |           0 |                    0 |
|      6 | perm     |      0.0010 |  15000.0000 |           0 |           0 |                    0 |
|      7 | vsh      |      0.0000 |      1.0000 |           0 |           0 |                    0 |
|      7 | phit     |      0.0000 |      0.5000 |           0 |           0 |                    0 |
|      7 | sw       |      0.0000 |      1.0000 |           0 |           0 |                    0 |
|      7 | perm     |      0.0010 |  15000.0000 |           0 |           0 |                    0 |

## Permeability Saturation Check

Samples where perm ≥ 14999 mD are likely capped at the tool's upper
dynamic-range limit. A high saturation fraction inflates downstream kh
estimates and should be surfaced before any volumetric ranking.

|   well |   n_samples |   n_perm_saturated |   fraction_saturated |
|-------:|------------:|-------------------:|---------------------:|
|      1 |        2651 |                691 |               0.2607 |
|      2 |        3401 |                481 |               0.1414 |
|      3 |        1951 |                420 |               0.2153 |
|      4 |        3251 |                473 |               0.1455 |
|      5 |        1061 |                155 |               0.1461 |
|      6 |        3101 |                464 |               0.1496 |
|      7 |        2751 |                830 |               0.3017 |

## Join Strategy

**Combining the well logs with `zones.csv` to produce the master table.**

### The problem

Two independent data sources must be combined:

- **Well logs** (`well_<id>.csv`): one row per depth sample, five measurements (vsh, phit, sw, perm) per row. No zone label.
- **Zone tops** (`zones.csv`): 35 rows recording only the depth at which each zone *begins* in each well, not the interval.

The data dictionary specifies that each zone extends from its listed depth down to the top of the next zone in the same well (or to the bottom of the log for the last zone). Every depth sample must be assigned the zone it belongs to.

### Why an equality join does not work

Log sample depths form a regular grid (1850.00, 1850.20, 1850.40, ...) while zone-top depths are irregular (1850.07, 1925.00, ...). These values never coincide, so a standard `INNER JOIN ON depth` would return zero rows.

What is needed is an **inequality join**: for each log sample, find the zone top whose depth is closest *at-or-below* the sample, within the same well.

### Chosen approach — `pandas.merge_asof`

```python
merged = pd.merge_asof(
    left=logs_sorted,
    right=zones_sorted,
    on="depth",
    by="well",
    direction="backward",
)
```

| Parameter | Value | Why |
|---|---|---|
| `on` | `"depth"` | The inequality key — depth comparison drives the match. |
| `by` | `"well"` | Match scope. Each sample is matched only against zone tops in the **same** well; the search never crosses well boundaries. |
| `direction` | `"backward"` | For each sample, pick the largest zone-top depth ≤ the sample depth — the most recent zone that has already begun. |

**Why `backward`, not `forward` or `nearest`.** For a sample at depth 1900 m in well_1, where zones A and B begin at 1850 and 1925:

- `backward` returns Zone A (1850 ≤ 1900) — correct: A is the most recent to have begun.
- `forward` returns Zone B (1925 ≥ 1900) — wrong: B has not begun yet.
- `nearest` returns Zone B (closer in distance) — wrong: proximity is not the geological criterion.

Only `backward` matches the data dictionary's interval definition.

**Performance.** On 18,167 samples × 35 zone tops, `merge_asof` performs roughly 93 K operations versus 636 K for a nested loop — and runs the inner loop in pandas' C extension. End-to-end join time is about 50 ms.

### Spec-compliance fix — the snap step

A literal `merge_asof` on the raw data leaves 7 samples unassigned. In every one of the 7 wells, the log starts a few centimetres **above** the first listed zone top:

| Well | Log start | First zone top | Gap |
|---|---|---|---|
| 1 | 1850.00 | 1850.07 | 0.07 m |
| 2 | 2010.00 | 2010.03 | 0.03 m |
| 3 | 1920.00 | 1920.01 | 0.01 m |
| 4 | 2100.00 | 2100.06 | 0.06 m |
| 5 | 1970.00 | 1970.01 | 0.01 m |
| 6 | 1800.00 | 1800.07 | 0.07 m |
| 7 | 2050.00 | 2050.04 | 0.04 m |

Without correction, each well's first sample would receive `zone = NaN` — a direct spec violation.

**The fix.** Before merging, each well's earliest zone top is moved up to that well's first log depth. Maximum snap distance is 7 cm — well below the 20 cm sampling resolution, so no calculated metric changes. The raw CSVs are never modified; snapping happens on a copy of the zones DataFrame inside `assign_zones`.

Post-snap, zone assignment is **100% complete** — zero NaN zones.

### Per-sample thickness `dz`

After zone assignment, each sample needs a thickness `dz` so kh (= sum of perm·dz) can be computed. The data dictionary defines:

```
dz[i]    = depth[i+1] - depth[i]   # forward difference
dz[last] = dz[last-1]              # repeat the last step
```

This is computed **per well**, not globally, because sampling steps differ. Well_5 uses 0.5 m; the other six wells use 0.2 m. A global `np.diff` on the concatenated table would produce nonsense at well boundaries (e.g. well_4 ends at 2750 m, well_5 starts at 1970 m, giving a boundary 'thickness' of −780 m).

### Summary

| Step | Tool | Purpose |
|---|---|---|
| 1. Load 7 well CSVs | `loader.load_all_wells` | One row per depth sample |
| 2. Load zones.csv | `loader.load_zones` | Zone tops, 35 rows |
| 3. Snap earliest zone tops | `joiner.assign_zones` | Spec compliance — 7 cm max correction |
| 4. Sort both frames by depth | (within `assign_zones`) | `merge_asof` precondition |
| 5. `merge_asof` inequality join | `joiner.assign_zones` | Assigns `zone` column |
| 6. Compute per-well `dz` | `joiner.compute_dz` | Per-sample thickness for kh |
| 7. Cache as Parquet | `cli.quality_cmd` | Single source of truth for Parts B/C/D |

The resulting master table — 18,167 rows with columns (well, depth, vsh, phit, sw, perm, zone, dz) — is cached as `data/processed/master_table.parquet` and serves as the single source of truth for every downstream deliverable.
