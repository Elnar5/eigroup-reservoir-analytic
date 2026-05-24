# Day 1 Handoff — Kamil's Local Setup Guide

Bu sənəd 1-ci günün nə qədər tamamlandığını və sənin lokalda nə edəcəyini izah edir.

---

## ✅ Gün 1-də nə hazırlandı?

### Tam tamamlanmış işlər

1. **Repo skeleton** — bütün direktoriya strukturu, `pyproject.toml`, `.gitignore`, `README.md`, `Makefile`
2. **Hydra config sistemi** — `configs/config.yaml`, `configs/cutoffs/default.yaml`, `configs/clustering/default.yaml`
3. **Part A loader** (`src/data/loader.py`) — well CSV-ləri kəşf edir, yükləyir, schema validate edir
4. **Part A quality report** (`src/data/quality.py`) — inventory, missing values, range checks, perm saturation
5. **Part A joiner** (`src/data/joiner.py`) — `merge_asof` ilə zone assignment, dz hesablama
6. **CLI** (`src/cli.py`) — `python -m src.cli quality` işləyir
7. **Tests** — 15 unit test, hamısı keçir
8. **CI** — GitHub Actions konfiqurasiyası
9. **Smoke test scripti** — `scripts/smoke_test_part_a.py`
10. **EDA notebook** — `notebooks/01_eda.ipynb`

### İlkin nəticələr (test datasında — 7 quyu)

- 17,407 toplam sample
- 7 quyu, dərinlik aralığı 1800-2700 m
- 35 zone top, 5 unique zone (A-E)
- 6 sample zone-suz qaldı (top zone-dan 0.01-0.07 m yuxarıda — bu **real data quality issue**-dur, **bug deyil**, və quality reportda flag edilib)
- Hər sütunda ~2% missing values
- Permeability saturation 0.3-3 sample/well (test data üçün)

---

## 🔄 Lokala köçürmə addımları

### 1. Zip-i aç və oryentasiya

```bash
unzip eigroup-reservoir-analytics-day1.zip
cd eigroup-reservoir-analytics
ls -la
```

### 2. ⚠️ Test datasını real data ilə əvəz et

**Bu çox vacibdir.** Mən pipeline-ı test etmək üçün **sintetik** well_1.csv ... well_7.csv yaratdım. Sən onları əvəz etməlisən:

```bash
# Test datasını sil
rm data/raw/well_*.csv data/raw/zones.csv

# eiGroup SharePoint-dan endirdiklərini yerinə qoy:
# https://eigcom-my.sharepoint.com/:f:/g/personal/sabina_gulizade_ei-g_com/...
cp /path/to/downloaded/well_1.csv data/raw/
cp /path/to/downloaded/well_2.csv data/raw/
# ... və ya sadəcə bütün faylları köçür:
# cp /path/to/downloaded/*.csv data/raw/

# Yoxla:
ls data/raw/
# Gözlənilən: well_1.csv ... well_7.csv, zones.csv
```

### 3. Virtual mühit qur (uv tövsiyə olunur)

```bash
# uv ilə (səndə var)
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"

# və ya plain pip ilə
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### 4. Yoxla — Part A işləyirmi?

```bash
# CLI ilə
PYTHONPATH=. python -m src.cli quality

# və ya Makefile ilə
make quality
```

Gözlənilən output:
```
2026-05-20 ... | INFO    | src.data.loader | Discovered 7 wells: [1, 2, 3, 4, 5, 6, 7]
2026-05-20 ... | INFO    | src.data.loader | Loaded 7 wells, XXXX total samples
2026-05-20 ... | INFO    | src.data.quality | Wrote quality report to outputs/reports/data_quality.md
2026-05-20 ... | INFO    | __main__ | Saved master table: data/processed/master_table.parquet
```

### 5. Quality report-u oxu

```bash
cat outputs/reports/data_quality.md
# və ya VSCode-da aç
code outputs/reports/data_quality.md
```

**Real data ilə nələri yoxla:**
- Hər quyu üçün step_mode düz 0.2-dirmi?
- `irregular_steps` sıfırdırmı? Əgər deyilsə, hansı quyularda problem var?
- `total_out_of_range` sıfırdırmı? Real datada bəzən vsh > 1 və ya phit < 0 olur — bunu yoxla
- `fraction_saturated` (perm = 15000) **çox yüksəkdirsə**, presentasiyada bunu mütləq qeyd et

### 6. Testləri işlət

```bash
make test
# və ya
PYTHONPATH=. pytest -v --no-cov
```

15 test keçməlidir. Real datayla pipeline işlədikdən sonra bu testlər hələ də keçəcək (testlər synthetic tmp datasında işləyir).

### 7. EDA notebook-unu aç

```bash
jupyter notebook notebooks/01_eda.ipynb
```

Hər cell-i `Shift+Enter` ilə işlət. Bu sənin real datanın "first look"-udur. Hər plotu nəzərdən keçir — anomaliya, surprise, və ya maraqlı pattern axtar.

### 8. Git initialize et

```bash
git init
git add .
git commit -m "Day 1: project scaffolding + Part A foundation"

# GitHub-da repo yarat (private, sonra eiGroup-a paylaşa biləsən):
gh repo create eigroup-reservoir-analytics --private --source=. --remote=origin
git push -u origin main
```

CI yaşıl olacaq çünki bütün testlər keçir.

---

## 📋 Gün 2 plan (sabah)

Səhər mənə **2 şey** göndər:
1. Real data ilə `outputs/reports/data_quality.md` faylının məzmunu (yapışdır chat-a)
2. EDA notebook-da diqqətini cəlb edən hər hansı maraqlı pattern (məsələn: "well 4-də phit çox aşağıdır" və ya "zone C-də perm dağılımı bimodal görünür")

Bunlardan sonra:
- **Part A polish** (1 saat) — quality report-u real data tapıntıları əsasında zənginləşdir
- **Part B implement** (3-4 saat):
  - `src/analytics/metrics.py` — gross, net, avg phit/perm, kh
  - Bonus metrics: NTG, kh-weighted avg perm, Lorenz coefficient
  - `outputs/reports/part_b_summary.csv` generate et
- **Tests** (1 saat) — metrics module üçün test yaz

---

## ⚠️ Diqqət edilməli məsələlər

### 1. Real well_1.csv farklı ola bilər

Sənin context-də göstərdiyin well_1 ~2000 sətirdi və `perm=15000` çox yer aldı. Real datada bu pattern fərqli ola bilər. Quality report-a baxmaq vacibdir.

### 2. Zone top dəqiqliyi

Smoke test-də biz gördük ki, zones.csv top depthləri (məs. 1924.66) log sample dərinliklərinə (məs. 1924.6 və 1924.8) dəqiq uyğunlaşmır. Bu **normaldır** — geologlar zone topu cm dəqiqliyi ilə qeyd edir, log sampling isə 0.2m-də olur. Bizim joiner backward fill-i düzgün edir, bu problem deyil. Amma presentasiyada bunu izah edə bilərsən.

### 3. Hydra config-i hələ tam Hydra runtime istifadə etmir

Sadələşdirmək üçün mən özüm config-i load edirəm (OmegaConf ilə). Bu Hydra-nın 90%-ni verir, lakin `--multirun` kimi advanced sweep features istifadə etmir. Lazım olarsa Gün 3-də upgrade edə bilərik.

### 4. Linting hələ tətbiq olunmayıb

Mən kodda type hints və docstrings yazdım, amma `ruff` ilə formatting hələ etməmişəm. Lokala köçürəndə bunu et:

```bash
ruff check src tests --fix
ruff format src tests
```

---

## 🎯 Day 1 — "Done" checklist

Lokalda bu siyahıda hamısı işləməlidir:

- [ ] `make install` problem vermir
- [ ] `data/raw/` real eiGroup data-sı ilə doldurulub
- [ ] `make quality` Part A pipeline-ı işlədir
- [ ] `outputs/reports/data_quality.md` yaranıb və real datadakı issue-ları göstərir
- [ ] `make test` 15/15 test keçir
- [ ] `notebooks/01_eda.ipynb` heç bir error olmadan run olur
- [ ] Git repo initialized, ilk commit edilib

---

## Sual olarsa

Sabah söhbətə başlayanda mənə deyirsən:
- "Quality report bu cür çıxdı: [yapışdır]"
- "EDA-da gördüm ki [pattern]"
- "Bu yerdə bug var: [traceback]"

Gün 2-də Part B-ə start verəcəyik.

**Uğurlar Kamil! 🚀**
