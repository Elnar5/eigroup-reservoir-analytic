# eiGroup Reservoir Analytics

Petrophysical well-log analytics for the eiGroup Associate Data Scientist
technical task. Loads multi-well log data, computes per-zone reservoir
metrics, sweeps net-reservoir cutoffs to expose volumetric sensitivity,
and identifies cross-well sub-zone facies via unsupervised clustering.

**Author:** Kamil Muradli
**Submission date:** May 27, 2026
**Task deadline:** May 27, 2026

---

## At a glance

- **7 wells × 5 zones × 18,167 samples** processed end-to-end
- **35 (well, zone) metrics** + bonus (NTG, kh-weighted perm, Lorenz)
- **315-row vsh sweep** + 21,000 bootstrap kh resamples
- **10 charts** (5 field views + 3 clustering per zone, PNG + interactive HTML)
- **105 pytest tests**, 96-100% coverage on hot paths
- **5 CLI commands**, single-machine reproducible from raw CSVs in <2 minutes

---

## Quick start

```bash
# 1. Clone and enter the repo
git clone <repo-url> eigroup-reservoir-analytics
cd eigroup-reservoir-analytics

# 2. Create a Python 3.11+ environment (uv recommended)
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"

# 3. Place raw data in data/raw/
#    Required: well_1.csv ... well_7.csv, zones.csv

# 4. Run the entire pipeline
python -m src.cli quality       # Part A — load, join, QC report
python -m src.cli metrics       # Part B — per-(well, zone) metrics
python -m src.cli sweep         # Part C.1 — vsh sensitivity sweep
python -m src.cli sweep --bootstrap   # + bootstrap CI on kh
python -m src.cli field         # Part C.2 — 5 field-view charts
python -m src.cli subzones --target-zone B --n-clusters 3   # Part D — Zone B clustering
python -m src.cli subzones --target-zone C --n-clusters 3   # Part D — Zone C clustering

# 5. Build the deliverables
python scripts/build_architecture_diagram.py    # outputs/figures/00_architecture.png
python scripts/build_dashboard.py               # outputs/dashboard.html
python scripts/build_slides.py                  # presentation/eigroup_reservoir_analytics.pptx
```

After running the above:
- **Charts:** `outputs/figures/*.png` and `*.html` (10 of each)
- **Reports:** `outputs/reports/*.csv` and `*.md` (incl. executive_summary.md)
- **Dashboard:** `outputs/dashboard.html` (open in browser)
- **Slide deck:** `presentation/eigroup_reservoir_analytics.pptx`

---

## Repository layout

```
eigroup-reservoir-analytics/
├── configs/                  # Hydra YAML (cutoffs, sensitivity, clustering)
├── data/
│   ├── raw/                  # Input: well_<id>.csv + zones.csv
│   └── processed/            # Pipeline parquet snapshots
├── src/
│   ├── data/
│   │   ├── loader.py         # Multi-well CSV load + schema validation
│   │   ├── joiner.py         # merge_asof zone assignment + per-well dz
│   │   └── quality.py        # NaN, range, saturation flags
│   ├── analytics/
│   │   ├── metrics.py        # Part B: 12 metrics per (well, zone)
│   │   └── sensitivity.py    # Part C.1: vsh sweep + bootstrap + knee detection
│   ├── visualization/
│   │   ├── field.py          # Part C.2: 5 field-view charts
│   │   └── clustering.py     # Part D: 3 clustering charts
│   ├── clustering/
│   │   └── subzone.py        # Part D: pooled K-Means + GMM + LOWO
│   └── cli.py                # Typer CLI orchestrator
├── tests/                    # 105 pytest tests, all green
├── scripts/                  # Helper scripts (smoke test, dashboard, slides)
├── outputs/
│   ├── figures/              # All charts (PNG + interactive HTML)
│   ├── reports/              # All CSV + Markdown deliverables
│   └── dashboard.html        # Single-page interactive dashboard
└── presentation/
    ├── slides.md             # Slide outline + speaker notes
    └── eigroup_reservoir_analytics.pptx   # Generated deck
```

---

## CLI reference

Every step is a single command. Each command is idempotent and re-uses cached
intermediates when available (re-runs are fast).

| Command | What it does | Output |
|---------|--------------|--------|
| `quality` | Part A: load 7 wells + zones, build master table, write quality report | `data_quality.md`, `master_table.parquet` |
| `metrics` | Part B: per-(well, zone) metrics with bonus columns (NTG, Lorenz, etc.) | `metrics_per_zone.csv`, `field_summary_by_*.csv` |
| `sweep` | Part C.1: vsh ∈ {0.30..0.70} sweep + knee detection | `sweep_results.csv`, `knee_points_*.csv` |
| `sweep --bootstrap` | + bootstrap CI on kh (200 resamples × 3 cutoffs) | `kh_bootstrap_ci.csv` |
| `field` | Part C.2: 5 charts (heatmap, stacked bar, cross-plot, sensitivity, Lorenz) | `outputs/figures/01-05_*.png` and `.html` |
| `subzones` | Part D: pooled clustering + LOWO + 3 charts. Use `--target-zone` and `--n-clusters` to override config. | `outputs/figures/06-08_zone*_*.png`, `subzone_metrics_*.csv`, `lowo_validation_*.csv` |

Cutoffs and clustering parameters live in `configs/config.yaml`. CLI flags
override the config for one-off runs.

---

## Key real-data findings

1. **Permeability tool saturation at 15,000 mD** — 14–30% of every well's samples
   are at the cap. Zone B is 88% saturated. kh estimates on saturated zones
   are conservative lower bounds, not best estimates.
2. **Zone D is tight rock** — NTG never exceeds 32% even at the loosest vsh
   cutoff. Fails on porosity, not shale. Bypass.
3. **Zone C splits into 3 reproducible sub-zones** across all 7 wells (LOWO ARI 0.97).
   Sub-zone 2 (top of Zone C) holds 48% of Zone C kh in 29% of its thickness.
4. **Zone B clustering fails informatively** — clustering reproduces tool
   censoring, not lithology. Documented as a method-awareness finding.
5. **Well-to-well kh ranking is partly an instrument artefact** — well_7 leads
   on kh (2.59 M) but is 30% tool-capped. A saturation-weighted ranking would
   shift the top three.

See `outputs/reports/executive_summary.md` for the full write-up.

---

## Tests

```bash
pytest -v                       # all 105 tests
pytest --cov=src                # with coverage report
pytest tests/test_metrics.py    # one module
```

Coverage on hot paths (May 2026):

| Module | Coverage |
|--------|----------|
| `metrics.py` | 99% |
| `sensitivity.py` | 96% |
| `subzone.py` | 97% |
| `field.py` | 100% |
| `clustering.py` (viz) | 100% |
| `joiner.py` | 97% |
| `loader.py` | 92% |

---

## Verification scripts

```bash
python scripts/inspect_charts.py   # Print chart metadata + per-zone metric summaries
python scripts/smoke_test_part_a.py   # End-to-end Part A pipeline smoke test
```

---

## Dependencies

- Python 3.11+
- Core: pandas, numpy, scipy, scikit-learn, statsmodels
- Viz: matplotlib, seaborn, plotly
- Config: hydra-core, omegaconf
- CLI / logging: typer, loguru, rich
- Output: python-pptx, pyarrow
- Dev: pytest, pytest-cov, ruff, mypy

Full list in `pyproject.toml`.

---

## Daily handoffs (process audit)

This project was built across 6 working days. Each day's progress, decisions,
and findings are documented:

- `DAY_01_HANDOFF.md` — Foundation, Part A
- `DAY_02_HANDOFF.md` — Real data + Part B + first findings
- `DAY_03_HANDOFF.md` — Part C sweep + 5 charts
- `DAY_04_HANDOFF.md` — Part D clustering (Zone B + Zone C two-story)

---

*Submitted in fulfilment of the eiGroup LLC Associate Data Scientist
technical assessment, May 2026.*