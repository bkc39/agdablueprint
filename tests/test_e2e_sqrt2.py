"""Opt-in smoke test: run `checkdecls` against a real external Agda project.

This is the stretch goal from issue #3 — point agdablueprint at a realistic,
multi-file, stdlib-backed development cloned from GitHub. It is **disabled by
default** (network + heavy) and is never part of the standard CI run.

The default target is Shinji Kono's `automaton-in-agda`, whose `src/root2.agda`
proves that no rational squares to a prime (`root-prime-irrational1`) — i.e. √2
(and every √prime) is irrational. It has a real `.agda-lib`
(`depend: standard-library-2.3`, matching the dev shell's stdlib), so it
exercises exactly the library-`depend:` resolution path the synthetic fixture
cannot.

Enable it by setting ``AGDABLUEPRINT_E2E_SQRT2=1``. Everything is configurable:

* ``AGDABLUEPRINT_E2E_SQRT2_REPO``  — git URL to clone.
* ``AGDABLUEPRINT_E2E_SQRT2_DECLS`` — space-separated declaration names that must
  resolve (default: the √2-irrationality theorem).

If the clone fails (no network, repo moved) the test skips rather than failing.
"""

import os
import shutil
import subprocess
from pathlib import Path

import pytest

from agdablueprint.agda import AgdaProject
from agdablueprint.checkdecls import check_declarations

REPO_URL = os.environ.get(
    "AGDABLUEPRINT_E2E_SQRT2_REPO",
    "https://github.com/shinji-kono/automaton-in-agda",
)
REAL_DECLS = os.environ.get(
    "AGDABLUEPRINT_E2E_SQRT2_DECLS",
    "root2.root-prime-irrational1",
).split()

pytestmark = [
    pytest.mark.skipif(
        os.environ.get("AGDABLUEPRINT_E2E_SQRT2") != "1",
        reason="opt-in; set AGDABLUEPRINT_E2E_SQRT2=1 to run",
    ),
    pytest.mark.skipif(
        shutil.which("agda") is None or shutil.which("git") is None,
        reason="requires agda and git on PATH",
    ),
]


def _clone(dest: Path) -> Path:
    proc = subprocess.run(
        ["git", "clone", "--depth", "1", REPO_URL, str(dest)],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        pytest.skip(f"could not clone {REPO_URL}:\n{proc.stderr}")
    return dest


def test_checkdecls_against_external_sqrt2_proof(tmp_path):
    repo = _clone(tmp_path / "repo")

    # Use the directory containing the project's .agda-lib as the root.
    libs = list(repo.rglob("*.agda-lib"))
    project_root = libs[0].parent if libs else repo

    # The real √2-irrationality declaration(s) must resolve, while a valid but
    # non-existent name in the same module must be reported missing — proving
    # checkdecls type-checked the real, stdlib-backed module that defines them.
    module = REAL_DECLS[0].rsplit(".", 1)[0]
    fake = (
        f"{module}.agdablueprintAbsentDecl"  # no double underscore: valid Agda
    )

    result = check_declarations([*REAL_DECLS, fake], project_root)
    assert not result.errors, result.errors
    for decl in REAL_DECLS:
        assert decl in result.present, f"{decl} did not resolve"
    assert fake in result.missing
