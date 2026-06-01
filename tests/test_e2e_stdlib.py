"""End-to-end test against the committed agda-stdlib-backed example.

Unlike the synthetic fixture (which imports nothing), ``examples/stdlib``
``depend:``s on the standard library, so this exercises the paths the fixture
cannot: web + pdf builds and ``checkdecls`` resolving real stdlib imports and
flagging an intentionally-missing declaration.

The whole module is skipped unless the full toolchain is present — agda *with
the standard library*, plasTeX, graphviz (``dot``), and (for the pdf build)
``latexmk`` — so a sealed ``nix build`` check phase or a bare ``pytest`` without
the dev shell still passes. CI runs it in the stdlib-aware dev shell.
"""

import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest
from click.testing import CliRunner

from agdablueprint.cli import cli

REPO_ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = REPO_ROOT / "examples" / "stdlib"


def _has_agda_stdlib() -> bool:
    """True if agda is on PATH and can resolve a `depend: standard-library`."""
    if shutil.which("agda") is None:
        return False
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        (d / "probe.agda-lib").write_text(
            "name: probe\ninclude: .\ndepend: standard-library\n"
        )
        (d / "Probe.agda").write_text("module Probe where\nimport Data.Nat\n")
        proc = subprocess.run(
            ["agda", "Probe.agda"], cwd=d, capture_output=True, text=True
        )
        return proc.returncode == 0


HAS_STDLIB = _has_agda_stdlib()

needs_toolchain = pytest.mark.skipif(
    not HAS_STDLIB
    or shutil.which("plastex") is None
    or shutil.which("dot") is None,
    reason="requires agda+standard-library, plastex and graphviz on PATH",
)
needs_latexmk = pytest.mark.skipif(
    shutil.which("latexmk") is None and shutil.which("pdflatex") is None,
    reason="requires latexmk/pdflatex (texlive) on PATH",
)


@pytest.fixture
def project(tmp_path):
    """A writable copy of the example so builds don't touch the source tree."""
    dest = tmp_path / "stdlib"
    shutil.copytree(EXAMPLE, dest)
    return dest


@needs_toolchain
def test_web_build_writes_graph_and_decls(project):
    bp = project / "blueprint"
    result = CliRunner().invoke(cli, ["web", "--blueprint", str(bp)])
    assert result.exit_code == 0, result.output

    graph = bp / "web" / "dep_graph_document.html"
    assert graph.exists()
    html = graph.read_text()
    for node in (
        "def:double",
        "thm:double-zero",
        "thm:plus-comm",
        "thm:triple",
    ):
        assert node in html, f"{node} missing from graph"
    # \agdaok / \stdlibok statements are colored.
    assert "green" in html

    # The web build writes agda_decls (checkdecls' input) next to the sources.
    decls = (bp / "agda_decls").read_text().split()
    assert "Sum.double" in decls
    assert "Data.Nat._+_" in decls


@needs_toolchain
@needs_latexmk
def test_pdf_build_produces_pdf(project):
    bp = project / "blueprint"
    result = CliRunner().invoke(cli, ["pdf", "--blueprint", str(bp)])
    assert result.exit_code == 0, result.output
    assert (bp / "print" / "print.pdf").exists()


@needs_toolchain
def test_checkdecls_flags_missing_decl(project):
    bp = project / "blueprint"
    # Produce agda_decls first.
    assert (
        CliRunner().invoke(cli, ["web", "--blueprint", str(bp)]).exit_code == 0
    )

    result = CliRunner().invoke(
        cli,
        [
            "checkdecls",
            "--project",
            str(project),
            "--decls",
            str(bp / "agda_decls"),
        ],
    )
    # The intentionally-missing decl makes the run fail with a non-zero exit.
    assert result.exit_code == 1, result.output
    assert "MISSING" in result.output
    assert "Sum.triple" in result.output
    # ...while the real project + stdlib declarations resolve.
    assert "Sum.double" in result.output
    assert "Data.Nat._+_" in result.output
