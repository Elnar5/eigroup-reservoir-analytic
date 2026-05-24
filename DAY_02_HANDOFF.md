# Day 2 Handoff — Real-Data Foundation + Part B

Bu sənəd 2-ci günün nə qədər tamamlandığını, real-data tapıntılarını,
presentation üçün danışacağın əsas məqamları və Day 3 planını izah edir.

---

## ✅ Gün 2-də nə tamamlandı

### Real-data foundation (Part A real ilə yenidən qaçırıldı)

7 well + zones.csv lokal SharePoint-dən endirildi və `data/raw/`-a qoyuldu.
Bütün Day 1 pipeline-ı **real data ilə** yenidən işlədi, və 3 önəmli
real-world xüsusiyyəti tutdu:

1. **NaN values in well_3.phit** — 78 sample (4%), digər well-lərdə yox
2. **Heterogeneous sampling step** — well_5-də dz=0.5 m, digər 6 well-də dz=0.2 m
3. **Permeability saturation at 15000 mD** — bütün well-lərdə 14-30% sample
   tool-cap-də (right-censored data)

Bu üç tapıntı `outputs/reports/data_quality.md`-də avtomatik flag olunur.

### Part B — per-(well, zone) metrics

`src/analytics/metrics.py` yaradıldı. Tələb olunan 5 metrika + 7 bonus
metrika hesablanır:

**Tələb olunan (assignment-dən):**
- `gross_thickness_m` — total interval qalınlığı
- `net_thickness_m` — net reservoir qalınlığı (vsh ≤ cutoff VƏ phit ≥ cutoff)
- `avg_phit` — net interval-da orta porosity
- `avg_perm_mD` — net interval-da orta perm (arithmetic mean)
- `kh_mD_m` — sum(perm × dz) net interval-da

**Bonus (real-data sophistication üçün):**
- `ntg` — net-to-gross ratio
- `avg_perm_kh_weighted_mD` — kh / net_thickness (flow-relevant)
- `lorenz_coefficient` — flow heterogeneity (Stiles/Schmalz-Rahme method)
- `n_samples` — sample count (sanity check)
- `n_samples_net` — net interval sample count
- `n_phit_nan` — NaN-a görə net-dən çıxarılan sample sayı
- `n_perm_saturated_in_net` — tool-cap-də olan net sample sayı

**Field-level rollups:**
- `field_summary_by_zone(metrics)` — zone-bazlı aggregation
- `field_summary_by_well(metrics)` — well-bazlı aggregation

### CLI

`src/cli.py`-də `metrics` komandası tam işlək vəziyyətdə:

```bash
python -m src.cli metrics                       # default cutoffs
python -m src.cli metrics --vsh-max 0.3         # CLI override
python -m src.cli metrics --phit-min 0.12       # CLI override
```

CSV (insan üçün) + parquet (sonrakı modullar üçün) output-ları yazır.
Master table cache-dən oxuyur (yoxdursa yenidən qurur).

### Tests

`tests/test_metrics.py` — **27 yeni test**, 8 test class:

- `TestArithmeticInvariants` (5) — gross=sum(dz), net≤gross, kh=sum(k·dz), və s.
- `TestRangeInvariants` (4) — NTG ∈ [0,1], Lorenz ∈ [0,1], net≤gross
- `TestNaNHandling` (3) — NaN phit/vsh net-dən çıxarılır, ayrıca count edilir
- `TestPermSaturation` (3) — saturated sample-lar kh-da saxlanılır, flag edilir
- `TestMixedDz` (2) — well_5-in 0.5m step-i kh və net-thickness-də doğru tutulur
- `TestCutoffMonotonicity` (2) — Part C.1 sweep üçün vacib invariant
- `TestLorenz` (3) — uniform→0, extreme→~1, empty→NaN
- `TestFieldSummaries` (3) — rollup-lar group-sum-lara bərabərdir
- `TestInputValidation` (2) — missing columns raise, NaN zones drop edilir

**Cəmi: 42 test (Day 1 + Day 2), hamısı keçir, metrics.py 99% coverage.**

---

## 🔑 Real-data tapıntıları — sayılarla

Bunları **presentation-da mütləq danış**. Hər biri **bir interview slide-i dəyərində**.

### Tapıntı 1 — Zone B fenomenal yüksək keçiricilikli, AMMA right-censored

Field-by-zone (default cutoffs):

| Zone | NTG  | avg_perm_kh_w | kh_total (mD·m) | Saturated samples |
|------|------|---------------|-----------------|-------------------|
| A    | 0.63 | 573           | 267,000         | 0                 |
| **B** | **0.93** | **14,997**   | **10,680,000** | **3,119 (88% of net B)** |
| C    | 0.84 | 743           | 680,000         | 17                |
| D    | 0.10 | 0.79          | 42              | 0                 |
| E    | 0.70 | 2,045         | 1,202,000       | 39                |

Zone B NTG 93%, kh digər zonaların 10 qat-dan çoxudur — **AMMA** sample-ların
88%-i 15000 mD-də capped. Bu o deməkdir ki, **bütün kh-əsaslı qərarlar Zone B
üçün lower-bound estimate-dir, best estimate deyil**. Həqiqi perm yəqin ki,
çox daha yüksəkdir, amma alət dynamic range-i bunu görə bilmir.

> **Presentation-da deyəcəyin cümlə:**
> "Zone B is the flow-dominant interval — 93% NTG, kh ten times any other zone.
> But 88% of net-B samples are at the 15000 mD instrument cap. The actual
> permeability is likely much higher than measured, which means **all kh-based
> rankings on Zone B are conservative lower bounds**, not best estimates."

### Tapıntı 2 — Zone D tight rock-dur, bypass edilməlidir

- NTG yalnız **0.10** (bütün well-lərdə)
- avg_perm_kh_weighted **0.79 mD** — sub-millidarcy, axın yoxdur
- avg_phit ~0.092 — net cutoff phit_min=0.08-ə çox yaxın

Zone D faktiki olaraq seal və ya tight non-reservoir-dir. Heç bir well-də
potensial yoxdur. Bu Part C.1 sensitivity sweep-də vacib olacaq: vsh cutoff-u
0.3-ə endirsən, Zone D NTG ~0%-ə düşəcək.

### Tapıntı 3 — Well-ranking saturation-dan etibarsızdır

kh_total-a görə (default cutoffs):

| Rank | Well | kh_total (mD·m) | n_saturated | % saturated |
|------|------|------------------|-------------|-------------|
| 1    | **well_7** | 2,591,000   | 798         | **29%**     |
| 2    | well_1 | 2,266,000        | 662         | 25%         |
| 3    | well_2 | 1,764,000        | 466         | 14%         |
| 4    | well_6 | 1,693,000        | 454         | 15%         |
| 5    | well_4 | 1,671,000        | 457         | 14%         |
| 6    | well_5 | 1,435,000        | 152         | 14%         |
| 7    | well_3 | 1,406,000        | 395         | 20%         |

well_7 və well_1 ən yüksək kh göstərir, AMMA onlar həm də ən yüksək saturation
faizinə malikdir. Yəni "ən yaxşı well-lər" demək asan deyil — **ranking qismən
alət artefaktıdır**.

> **Presentation-da:**
> "Well 7 ranks first by kh, but 29% of its samples are at the perm cap — the
> ranking is partly an artifact of the instrument's dynamic range. A more
> defensible ranking would weight by saturation-aware confidence."

### Tapıntı 4 — well_3 NaN-ları düzgün idarə olundu

well_3-də 78 NaN phit sample var (cəmi sample-ların 4%-i). Bunlar zonalara
belə paylanır: A=15, B=14, C=31, D=0, E=18. Bütün hallarda **net thickness-ə
daxil edilmədi**, ayrıca count edildi (`n_phit_nan` kolonkası).

Bu interview-də "how do you handle missing data" sualına konkret cavabdır:
**Conservative — missing data ≠ reservoir**. Production-da bu sample-lar
imputation gözləyər, amma reservoir summary üçün exclude etmək tək doğru
qərardır.

### Tapıntı 5 — well_5-in fərqli step-i problem yaratmadı

well_5 yalnız 1061 sample-a malikdir (digərlərinin yarısı qədər), çünki step
0.5 m-dir. Buna baxmayaraq, NTG/perm/kh metrikaları digər well-lərlə tam
müqayisəli oldu, çünki `compute_dz` per-well dinamik step hesablayır.

> **Presentation-da:**
> "I detected heterogeneous sampling in QC, confirmed dz is computed per-well,
> and verified through tests that mixed-dz frames produce correct kh."

### Tapıntı 6 — Lorenz pattern-i geological mənada doğrudur

- Zone B: Lorenz ~0.001 (görünür homogeneous — saturation artefaktı)
- Zone C: Lorenz ~0.65 (heterogeneous — perm aralığı geniş)
- Zone D: Lorenz ~0.40 (tight, az contrast)
- Zone E: Lorenz ~0.52 (orta heterogeneity)

**Zone B-nin Lorenz-i "yalançı" homogen olduğu üçün maraqlıdır** — saturation
həqiqi heterogenliyi gizlədir. Day 3-də bir Lorenz chart-da bunu görsətsən,
geophysicist-i çox təsirləndirəcək.

---

## 📁 Repo strukturu — Day 2 sonrası

```
eigroup-reservoir-analytics/
├── configs/
│   ├── config.yaml
│   ├── cutoffs/default.yaml
│   └── clustering/default.yaml
├── data/
│   ├── raw/
│   │   ├── well_1.csv … well_7.csv      ← real data
│   │   └── zones.csv
│   └── processed/
│       ├── master_table.parquet         ← Day 1 + smoke test
│       └── metrics_per_zone.parquet     ← NEW (Day 2)
├── outputs/
│   └── reports/
│       ├── data_quality.md              ← Day 1, real data ilə yenidən qaçırıldı
│       ├── metrics_per_zone.csv         ← NEW
│       ├── field_summary_by_zone.csv    ← NEW
│       └── field_summary_by_well.csv    ← NEW
├── src/
│   ├── cli.py                           ← metrics komandası işlək (Day 2)
│   ├── data/
│   │   ├── loader.py
│   │   ├── joiner.py
│   │   └── quality.py
│   ├── analytics/
│   │   └── metrics.py                   ← NEW (Day 2)
│   ├── visualization/                   ← Day 3-də doldurulacaq
│   └── clustering/                      ← Day 4-də doldurulacaq
├── tests/
│   ├── test_loader.py     (8 test)
│   ├── test_joiner.py     (6 test)
│   └── test_metrics.py    (27 test)     ← NEW (Day 2)
├── scripts/
│   └── smoke_test_part_a.py
├── notebooks/
│   └── 01_eda.ipynb
├── DAY_01_HANDOFF.md
├── DAY_02_HANDOFF.md                    ← bu fayl
├── README.md
├── Makefile
└── pyproject.toml
```

---

## 🧪 Necə yoxlamaq

Virtual env aktiv ikən:

```bash
# Bütün testlər
pytest -v
# 42 keçməlidir

# Part A pipeline-ı
python -m src.cli quality
# data_quality.md və master_table.parquet yaranır

# Part B — default cutoffs
python -m src.cli metrics
# 35-row metrics CSV + field summaries + parquet yaranır

# Part B — cutoff override (Part C.1 stub)
python -m src.cli metrics --vsh-max 0.3
python -m src.cli metrics --phit-min 0.12
```

**Diqqət:** Hər `metrics` runu output faylının üzərinə yazır. Default cutoff
nəticələrini bərpa etmək üçün son addımda `python -m src.cli metrics` (heç bir
flag-siz) işlət.

---

## 🚧 Day 3 — Part C planı

### C.1 — vsh cutoff sensitivity sweep (`src/analytics/sensitivity.py`)

- vsh ∈ {0.30, 0.35, 0.40, 0.45, 0.50, 0.55, 0.60, 0.65, 0.70} → 9 cutoff
- Hər cutoff üçün 35 metrika → **315 sətirlik long-form frame**
- Output: `outputs/reports/sweep_results.csv` (long-form, tidy)
- Charts:
  - Per-zone NTG vs vsh_cutoff (1 line/zone, 1 line/well)
  - Per-zone kh vs vsh_cutoff (log y-axis)
  - "Knee point" detection — cutoff harada sürətli düşürür?

**Bonus:** Bootstrap CI — hər cutoff üçün 200 bootstrap replicas, kh ətrafında
90% interval. Bu Tier 2 wow-effect-dir.

### C.2 — Field-view chart-lar (`src/visualization/field.py`)

3 chart, Plotly ilə:

1. **Heatmap** — rows = wells, columns = zones, color = kh; saturation overlay
   kimi annotation (textə nöqtə qoyaraq)
2. **Stacked bar** — hər well-də kh-ni zonalara görə split
3. **Cross-plot** — phit (x) vs perm log10 (y), zone-larla rənglə, saturation
   point-ləri ayrıca marker ilə

### CLI

```bash
python -m src.cli sweep      # C.1 — bütün cutoff-ları qaçırır
python -m src.cli field      # C.2 — 3 chart üçün HTML/PNG
```

### Tests (gözlənilən)

- `test_sensitivity.py` — sweep monotonicity (tight cutoff → daha az net)
- `test_field_views.py` — chart-lar yazılır, fayl-lar mövcuddur

### Vaxt qiymətləndirməsi

- C.1 code: 2-3 saat
- C.1 bootstrap CI: +1 saat
- C.2 charts (3): 2-3 saat
- Tests: 1 saat
- **Cəmi: 6-8 saat**

---

## 📅 Qalan günlərə baxış

| Gün | Tarix       | İş |
|-----|-------------|-----|
| ~~1~~ | ~~May 20~~ | ~~Foundation + Part A~~ ✅ |
| ~~2~~ | ~~May 21~~ | ~~Real data + Part B + tests~~ ✅ |
| 3   | May 22      | Part C.1 sweep + Part C.2 charts |
| 4   | May 23      | Part D — Zone B sub-zone clustering (K-Means + GMM) |
| 5   | May 24      | Part D — cross-well validation + smoothing |
| 6   | May 25      | Dashboard (Plotly), arxitektura diaqramı, executive summary |
| 7   | May 26      | Presentation hazırlığı, dry-run, polish |
| 🎯  | **May 27**  | **DEADLINE** — submit |

İndi **graph-ə görə proqramda və ya bir az öndəyik**. Stress yox.

---

## 🎙️ Presentation slide ideyaları — Day 2 nəticələrindən

Hələ slide yazmırıq, amma bu fikirlər toplanıb:

1. **Slide 3 — "Three real-data issues that shape every downstream decision"**
   - NaN values (well_3), heterogeneous sampling (well_5), perm saturation
     (all wells)
   - Each issue → my QC step caught it → my code handles it

2. **Slide 5 — "Why average permeability is misleading"**
   - Arithmetic vs kh-weighted comparison
   - Zone C example: both equal because dz uniform
   - Zone B example: both equal but both saturated

3. **Slide 6 — "Net-to-Gross by zone tells the geological story"**
   - Zone D is tight rock (NTG 10%)
   - Zone B is the flow-dominant interval (NTG 93%)
   - These two facts alone determine the field strategy

4. **Slide 9 — "Why kh ranking can mislead well selection"**
   - well_7 vs well_2: well_7 wins on kh, but 2× saturation rate
   - Confidence-weighted ranking would change top-3

5. **Slide 11 — "Lorenz coefficient reveals heterogeneity"**
   - Zone C is genuinely heterogeneous (L=0.65) — completion strategy matters
   - Zone B appears homogeneous (L≈0) — but it's the saturation flattening
     the curve

---

## ✅ Day 2 acceptance checklist

- [x] Real data 7 well + zones yükləndi
- [x] Data quality report 3 real-data issue-nu flag edir
- [x] `src/analytics/metrics.py` — 5 required + 7 bonus metrika
- [x] Field rollups (by zone, by well)
- [x] CLI: `python -m src.cli metrics` işləyir
- [x] CLI cutoff override-ləri (--vsh-max, --phit-min)
- [x] 27 yeni test, 42 cəmi, hamısı yaşıl
- [x] metrics.py 99% coverage
- [x] Real-data tapıntıları sayılarla təsdiqləndi
- [x] DAY_02_HANDOFF.md yazıldı

**Day 2 status: ✅ COMPLETE.**

---

*Son redaktə: 2026-05-21*
