"""Integration test: render the minimal example with the agdablueprint plugin.

This drives the real ``plastex`` CLI and therefore needs the graph toolchain
(``plastex`` and graphviz's ``dot``/``tred``). It is skipped when those are not
on PATH — e.g. in the sealed ``nix build`` check phase — and runs fully in the
dev shell / CI (``nix develop --command pytest``).
"""

import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = REPO_ROOT / "examples" / "minimal" / "blueprint.tex"

pytestmark = pytest.mark.skipif(
    shutil.which("plastex") is None or shutil.which("dot") is None,
    reason="requires plastex and graphviz (dot/tred) on PATH",
)


def test_minimal_example_renders(tmp_path):
    work = tmp_path / "work"
    work.mkdir()
    shutil.copy(EXAMPLE, work / "blueprint.tex")

    result = subprocess.run(
        ["plastex", "--plugins=agdablueprint", "--dir=out", "blueprint.tex"],
        cwd=work,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr

    # The dependency graph page was produced...
    graph = work / "out" / "dep_graph_document.html"
    assert graph.exists()
    graph_html = graph.read_text()
    for node in ("def:even", "lem:zero-even", "thm:sum-even"):
        assert node in graph_html
    # ...with status-based coloring (an \agdaok statement is green).
    assert "green" in graph_html

    # The agda_decls file (checkdecls input) lists every \agda{...} name.
    decls_file = work.parent / "agda_decls"
    assert decls_file.exists()
    decls = decls_file.read_text().split()
    assert "Data.Nat.Even" in decls
    assert "Data.Nat.Even.zero-even" in decls
