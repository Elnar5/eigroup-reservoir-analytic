# =============================================================================
# eiGroup Reservoir Analytics — pipeline orchestration
# =============================================================================
# Usage:
#   make install   # install package + dev dependencies
#   make quality   # Part A — data quality report + master table
#   make metrics   # Part B — per-(well, zone) analytical table
#   make sweep     # Part C.1 — cutoff sensitivity
#   make field     # Part C.2 — field-level views
#   make subzones  # Part D — clustering
#   make all       # full pipeline (quality -> metrics -> sweep -> field -> subzones)
#   make test      # pytest with coverage
#   make lint      # ruff check
#   make clean     # remove generated outputs
# =============================================================================

PY ?= python
PYTHONPATH := .

.PHONY: install all quality metrics sweep field subzones test lint clean help

help:
	@echo "Targets:"
	@echo "  install   Install package + dev dependencies"
	@echo "  quality   Part A — data quality report and master table"
	@echo "  metrics   Part B — analytical table per (well, zone)"
	@echo "  sweep     Part C.1 — vsh cutoff sensitivity"
	@echo "  field     Part C.2 — field-level views"
	@echo "  subzones  Part D — clustering for sub-zone definition"
	@echo "  all       Run the full pipeline"
	@echo "  test      Run pytest with coverage"
	@echo "  lint      Run ruff"
	@echo "  clean     Remove generated outputs (keeps data/raw)"

install:
	pip install -e ".[dev]"

quality:
	PYTHONPATH=$(PYTHONPATH) $(PY) -m src.cli quality

metrics: quality
	PYTHONPATH=$(PYTHONPATH) $(PY) -m src.cli metrics

sweep: metrics
	PYTHONPATH=$(PYTHONPATH) $(PY) -m src.cli sweep

field: metrics
	PYTHONPATH=$(PYTHONPATH) $(PY) -m src.cli field

subzones: quality
	PYTHONPATH=$(PYTHONPATH) $(PY) -m src.cli subzones

all: quality metrics sweep field subzones
	@echo ""
	@echo "Pipeline complete. Outputs in outputs/"

test:
	PYTHONPATH=$(PYTHONPATH) pytest -v

lint:
	ruff check src tests

clean:
	rm -rf data/processed/*.parquet
	rm -rf outputs/reports/*.md outputs/reports/*.csv
	rm -rf outputs/figures/*.png outputs/figures/*.html
	rm -rf outputs/dashboard.html
	rm -rf outputs/coverage_html
	rm -rf outputs/hydra
	@echo "Cleaned generated outputs (raw data preserved)"
