"""CLI tests for `agdablueprint checkdecls` against the fixture project."""

import shutil
from pathlib import Path

import pytest
from click.testing import CliRunner

from agdablueprint.cli import cli

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE = REPO_ROOT / "tests" / "fixtures" / "agda-project"

needs_agda = pytest.mark.skipif(
    shutil.which("agda") is None, reason="requires the agda executable on PATH"
)


@needs_agda
def test_checkdecls_names_present():
    result = CliRunner().invoke(
        cli,
        ["checkdecls", "--project", str(FIXTURE), "Blueprint.Demo.zero-even"],
    )
    assert result.exit_code == 0, result.output
    assert "All 1 declarations found." in result.output


@needs_agda
def test_checkdecls_names_missing_exit_1():
    result = CliRunner().invoke(
        cli,
        ["checkdecls", "--project", str(FIXTURE), "Blueprint.Demo.nope"],
    )
    assert result.exit_code == 1
    assert "MISSING" in result.output


@needs_agda
def test_checkdecls_reads_decls_file(tmp_path):
    decls = tmp_path / "agda_decls"
    decls.write_text("Blueprint.Demo.Even\nBlueprint.Demo.zero-even\n")
    result = CliRunner().invoke(
        cli,
        ["checkdecls", "--project", str(FIXTURE), "--decls", str(decls)],
    )
    assert result.exit_code == 0, result.output


def test_checkdecls_no_names_errors(tmp_path):
    # No names and no agda_decls file -> usage error (no agda needed).
    result = CliRunner().invoke(cli, ["checkdecls", "--project", str(tmp_path)])
    assert result.exit_code != 0
    assert "No declaration names" in result.output
