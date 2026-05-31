"""Tests for the Agda declaration checker, run against tests/fixtures/agda-project."""

import shutil
from pathlib import Path

import pytest

from agdablueprint.agda import AgdaProject
from agdablueprint.checkdecls import check_declarations, read_agda_decls

REPO_ROOT = Path(__file__).resolve().parents[1]
FIXTURE = REPO_ROOT / "tests" / "fixtures" / "agda-project"

needs_agda = pytest.mark.skipif(
    shutil.which("agda") is None, reason="requires the agda executable on PATH"
)


def test_project_discovery_finds_modules():
    project = AgdaProject.discover(FIXTURE)
    assert project.lib_file is not None
    assert "Blueprint.Demo" in project.modules()


def test_read_agda_decls(tmp_path):
    f = tmp_path / "agda_decls"
    f.write_text("A.b\nA.c\nA.b\n\n")
    assert read_agda_decls(f) == ["A.b", "A.c"]


@needs_agda
def test_all_present():
    result = check_declarations(
        ["Blueprint.Demo.Even", "Blueprint.Demo.zero-even", "Blueprint.Demo.even-zero"],
        FIXTURE,
    )
    assert result.ok, (result.missing, result.errors)
    assert set(result.present) == {
        "Blueprint.Demo.Even",
        "Blueprint.Demo.zero-even",
        "Blueprint.Demo.even-zero",
    }


@needs_agda
def test_detects_multiple_missing():
    result = check_declarations(
        [
            "Blueprint.Demo.zero-even",
            "Blueprint.Demo.sum-even",  # missing
            "Blueprint.Demo.Even",
            "Blueprint.Demo.totally-missing",  # missing
        ],
        FIXTURE,
    )
    assert not result.ok
    assert set(result.missing) == {
        "Blueprint.Demo.sum-even",
        "Blueprint.Demo.totally-missing",
    }
    assert "Blueprint.Demo.zero-even" in result.present
    assert "Blueprint.Demo.Even" in result.present
    assert not result.errors


@needs_agda
def test_empty_is_ok():
    assert check_declarations([], FIXTURE).ok
