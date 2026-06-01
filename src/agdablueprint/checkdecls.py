"""Verify that the Agda declarations referenced in a blueprint exist.

This is the Agda counterpart of leanblueprint's ``checkdecls``. Given the list
of fully-qualified names collected from ``\\agda{...}`` macros (written by the
plasTeX plugin to an ``agda_decls`` file), it generates a small Agda "checker"
module that imports the relevant project modules and references each name, then
type-checks it. Names Agda reports as ``[NotInScope]`` are missing.

Because Agda aborts at the first scope error, missing names are discovered
iteratively: run the checker, peel off the reported missing name, and re-run.
In the common case where every name resolves, this is a single Agda invocation.
"""

from __future__ import annotations

import re
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from agdablueprint.agda import AgdaProject, split_module, typecheck

CHECKER_MODULE = "_agdablueprint_checkdecls"

# Agda prints `when scope checking <FQN>` for an out-of-scope reference.
_NOT_IN_SCOPE_RE = re.compile(r"^when scope checking (\S+)\s*$", re.MULTILINE)


@dataclass
class CheckResult:
    present: list[str] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.missing and not self.errors


def read_agda_decls(path: str | Path) -> list[str]:
    """Read declaration names from an ``agda_decls`` file (one per line)."""
    text = Path(path).read_text()
    seen: dict[str, None] = {}
    for line in text.splitlines():
        name = line.strip()
        if name:
            seen.setdefault(name, None)
    return list(seen)


def _module_for(fqn: str, project_modules: set[str]) -> str:
    """Pick the module to ``import`` so that ``fqn`` can be referenced."""
    return split_module(fqn, project_modules)[0]


def _render_checker(names: list[str], project_modules: set[str]) -> str:
    modules = sorted({_module_for(n, project_modules) for n in names})
    lines = [f"module {CHECKER_MODULE} where", ""]
    lines += [f"import {m}" for m in modules]
    lines.append("")
    for i, name in enumerate(names):
        lines.append(f"_c{i} = {name}")
    return "\n".join(lines) + "\n"


def check_declarations(
    names: list[str],
    project_root: str | Path,
    agda: str | None = None,
) -> CheckResult:
    """Check that every name in ``names`` resolves in the Agda project."""
    result = CheckResult()
    names = [n for n in dict.fromkeys(names) if n]  # dedupe, drop blanks
    if not names:
        return result

    project = AgdaProject.discover(project_root)
    project_modules = project.modules()

    with tempfile.TemporaryDirectory() as tmp:
        tmpdir = Path(tmp)
        checker = tmpdir / f"{CHECKER_MODULE}.agda"
        # The checker's own directory must be an include dir so its module name
        # matches its path; project modules resolve through the project includes.
        includes = [tmpdir, *project.include_dirs]

        remaining = list(names)
        # Worst case: one Agda run per missing name, plus a final clean run.
        for _ in range(len(names) + 1):
            checker.write_text(_render_checker(remaining, project_modules))
            # Run from the project root so Agda finds the project's `.agda-lib`
            # and applies its `depend:` libraries (e.g. agda-stdlib); resolution
            # is keyed off the working directory, not the checker's location.
            proc = typecheck(checker, includes, agda=agda, cwd=project.root)
            if proc.returncode == 0:
                break
            output = proc.stdout + proc.stderr
            missing_now = [
                n for n in _NOT_IN_SCOPE_RE.findall(output) if n in remaining
            ]
            if not missing_now:
                # A non-scope error (e.g. the project does not type-check, or a
                # module could not be found). Surface it rather than guessing.
                result.errors.append(output.strip())
                # Everything still unproven is indeterminate; report as errors.
                return result
            for n in missing_now:
                result.missing.append(n)
                remaining.remove(n)
            if not remaining:
                break

    result.present = [n for n in names if n not in result.missing]
    return result
