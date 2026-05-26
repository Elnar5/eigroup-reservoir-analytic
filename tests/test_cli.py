"""
Tests for src.cli.

CLI testing strategy:
  - smoke tests via Typer's CliRunner — verify each sub-command is registered
    and that `--help` exits cleanly
  - unit tests for the `_load_config` helper which does the Hydra-style
    defaults composition

We intentionally do NOT run full sub-commands here; those are covered by
the dedicated module tests (test_quality, test_metrics, test_sensitivity,
test_subzone) which exercise the underlying functions directly.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from src.cli import _load_config, app


runner = CliRunner()


# -----------------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------------

@pytest.fixture
def basic_config(tmp_path: Path) -> Path:
    """A minimal config.yaml with no `defaults:` block."""
    cfg = tmp_path / "config.yaml"
    cfg.write_text(
        """
data:
  raw_dir: data/raw
  zones_file: zones.csv
runtime:
  log_level: INFO
""".strip()
    )
    return cfg


@pytest.fixture
def config_with_defaults(tmp_path: Path) -> Path:
    """
    A config.yaml that references a sub-group via `defaults:` —
    mirrors the real configs/config.yaml + configs/cutoffs/default.yaml pattern.
    """
    # Sub-config: configs/cutoffs/default.yaml
    cutoffs_dir = tmp_path / "cutoffs"
    cutoffs_dir.mkdir()
    (cutoffs_dir / "default.yaml").write_text(
        """
vsh_max: 0.5
phit_min: 0.08
""".strip()
    )

    # Main config
    main = tmp_path / "config.yaml"
    main.write_text(
        """
defaults:
  - cutoffs: default
  - _self_
data:
  raw_dir: data/raw
""".strip()
    )
    return main


# -----------------------------------------------------------------------------
# Tests — CLI smoke tests (4 tests)
# -----------------------------------------------------------------------------

class TestCliRegistration:

    def test_app_help_exits_cleanly(self):
        """Top-level --help shows the app description and lists sub-commands."""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "reservoir" in result.stdout.lower() or "pipeline" in result.stdout.lower()

    def test_all_subcommands_registered(self):
        """All six expected sub-commands appear in --help output."""
        result = runner.invoke(app, ["--help"])
        for sub in ["quality", "metrics", "sweep", "field", "subzones", "run-all"]:
            assert sub in result.stdout, f"sub-command '{sub}' not registered"

    def test_quality_help_exits_cleanly(self):
        """quality --help shows the command's docstring."""
        result = runner.invoke(app, ["quality", "--help"])
        assert result.exit_code == 0

    def test_no_args_shows_help(self):
        """Invoking the app without a sub-command shows help (no_args_is_help=True)."""
        result = runner.invoke(app, [])
        # Typer returns exit code 2 (or 0) when showing help via no_args_is_help;
        # the key signal is that it doesn't crash unexpectedly.
        assert result.exit_code in (0, 2)


# -----------------------------------------------------------------------------
# Tests — _load_config (4 tests)
# -----------------------------------------------------------------------------

class TestLoadConfig:

    def test_load_basic_config(self, basic_config):
        """A simple YAML with no defaults loads as-is."""
        cfg = _load_config(str(basic_config))
        assert cfg.data.raw_dir == "data/raw"
        assert cfg.data.zones_file == "zones.csv"
        assert cfg.runtime.log_level == "INFO"

    def test_load_config_resolves_defaults_group(self, config_with_defaults):
        """When `defaults:` references cutoffs/default, the sub-config is merged in."""
        cfg = _load_config(str(config_with_defaults))
        # Sub-config values are now accessible under cfg.cutoffs
        assert cfg.cutoffs.vsh_max == 0.5
        assert cfg.cutoffs.phit_min == 0.08

    def test_load_config_strips_defaults_marker(self, config_with_defaults):
        """The `defaults` key is removed after composition (it's a marker, not data)."""
        cfg = _load_config(str(config_with_defaults))
        assert "defaults" not in cfg

    def test_load_config_preserves_base_keys(self, config_with_defaults):
        """Non-defaults keys in the main config are preserved alongside the merged sub-config."""
        cfg = _load_config(str(config_with_defaults))
        # Base config has data.raw_dir; sub-config has cutoffs.vsh_max — both must be present
        assert cfg.data.raw_dir == "data/raw"
        assert cfg.cutoffs.vsh_max == 0.5
