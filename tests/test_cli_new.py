"""Tests for `agdablueprint new` (the project scaffolder)."""

import shutil
from pathlib import Path

import pytest
from click.testing import CliRunner

from agdablueprint.cli import cli

needs_plastex = pytest.mark.skipif(
    shutil.which("plastex") is None or shutil.which("dot") is None,
    reason="requires plastex and graphviz (dot/tred) on PATH",
)

EXPECTED_FILES = [
    "plastex.cfg",
    ".github/workflows/blueprint.yml",
    "blueprint/src/web.tex",
    "blueprint/src/print.tex",
    "blueprint/src/content.tex",
    "blueprint/src/latexmkrc",
    "blueprint/src/agdablueprint.sty",
    "blueprint/src/macros/common.tex",
    "blueprint/src/macros/web.tex",
    "blueprint/src/macros/print.tex",
]


def _scaffold(dest: Path, *extra):
    return CliRunner().invoke(
        cli,
        [
            "new",
            "--defaults",
            "--dest",
            str(dest),
            "--title",
            "Test Blueprint",
            "--github",
            "https://github.com/me/test",
            *extra,
        ],
    )


def test_new_scaffolds_expected_layout(tmp_path):
    result = _scaffold(tmp_path)
    assert result.exit_code == 0, result.output
    for rel in EXPECTED_FILES:
        assert (tmp_path / rel).exists(), f"missing {rel}"

    # Templated metadata is substituted into the entry points.
    web = (tmp_path / "blueprint" / "src" / "web.tex").read_text()
    assert "\\title{Test Blueprint}" in web
    assert "\\github{https://github.com/me/test}" in web
    assert "plugins=agdablueprint" in (tmp_path / "plastex.cfg").read_text()


def test_new_refuses_existing_without_force(tmp_path):
    assert _scaffold(tmp_path).exit_code == 0
    result = _scaffold(tmp_path)
    assert result.exit_code != 0
    assert "already exists" in result.output


def test_new_force_overwrites(tmp_path):
    assert _scaffold(tmp_path).exit_code == 0
    assert _scaffold(tmp_path, "--force").exit_code == 0


@needs_plastex
def test_new_project_web_builds(tmp_path):
    assert _scaffold(tmp_path).exit_code == 0
    result = CliRunner().invoke(
        cli, ["web", "--blueprint", str(tmp_path / "blueprint")]
    )
    assert result.exit_code == 0, result.output
    assert (tmp_path / "blueprint" / "web" / "dep_graph_document.html").exists()
    # The plugin writes agda_decls next to the blueprint sources.
    assert (tmp_path / "blueprint" / "agda_decls").exists()
