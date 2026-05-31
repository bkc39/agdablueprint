"""Thin wrappers around the ``agda`` binary and Agda project introspection.

Nothing here knows about blueprints; it is the low-level layer used by
:mod:`agdablueprint.checkdecls`.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path


class AgdaNotFound(RuntimeError):
    """Raised when no ``agda`` executable can be located."""


def find_agda(explicit: str | None = None) -> str:
    """Locate the ``agda`` executable.

    Order: an explicit path, the ``AGDA`` environment variable, then ``PATH``.
    """
    for candidate in (explicit, os.environ.get("AGDA"), "agda"):
        if not candidate:
            continue
        resolved = (
            shutil.which(candidate)
            if os.path.basename(candidate) == candidate
            else candidate
        )
        if resolved and Path(resolved).exists():
            return resolved
        which = shutil.which(candidate)
        if which:
            return which
    raise AgdaNotFound(
        "Could not find the 'agda' executable. Install Agda, put it on PATH, "
        "or set the AGDA environment variable."
    )


@dataclass
class AgdaProject:
    """An Agda project rooted at a directory containing an ``.agda-lib`` file."""

    root: Path
    lib_file: Path | None
    include_dirs: list[Path] = field(default_factory=list)

    @classmethod
    def discover(cls, root: str | Path) -> "AgdaProject":
        root = Path(root).resolve()
        lib_file = _find_agda_lib(root)
        if lib_file is not None:
            includes = _parse_includes(lib_file)
        else:
            # No .agda-lib: treat the root itself as the single include dir.
            includes = [root]
        # Always make sure the root is searchable.
        if root not in includes:
            includes.append(root)
        return cls(root=root, lib_file=lib_file, include_dirs=includes)

    def modules(self) -> set[str]:
        """All Agda module names reachable from the include directories."""
        found: set[str] = set()
        for inc in self.include_dirs:
            if not inc.is_dir():
                continue
            for path in inc.rglob("*.agda"):
                if _is_ignored(path, inc):
                    continue
                rel = path.relative_to(inc).with_suffix("")
                found.add(".".join(rel.parts))
        return found


def _find_agda_lib(root: Path) -> Path | None:
    libs = sorted(root.glob("*.agda-lib"))
    return libs[0] if libs else None


def _parse_includes(lib_file: Path) -> list[Path]:
    """Parse the ``include:`` field of an ``.agda-lib`` file.

    The field may span multiple whitespace-separated, possibly multi-line
    entries. Paths are resolved relative to the ``.agda-lib`` directory.
    """
    text = lib_file.read_text()
    base = lib_file.parent
    includes: list[Path] = []
    # Fields are "key: value" with continuation lines indented; we only need
    # `include`. Capture everything after `include:` up to the next top-level key.
    match = re.search(r"(?m)^include\s*:(.*?)(?=^\S+\s*:|\Z)", text, re.DOTALL)
    if match:
        for token in match.group(1).split():
            includes.append((base / token).resolve())
    if not includes:
        includes.append(base.resolve())
    return includes


def _is_ignored(path: Path, include_root: Path) -> bool:
    parts = path.relative_to(include_root).parts
    return any(p == "_build" or p.startswith(".") for p in parts)


def typecheck(
    file: str | Path,
    include_dirs: list[Path],
    agda: str | None = None,
    extra_args: list[str] | None = None,
) -> subprocess.CompletedProcess:
    """Run ``agda`` on ``file`` with the given include directories."""
    exe = find_agda(agda)
    cmd = [exe]
    for inc in include_dirs:
        cmd += ["-i", str(inc)]
    cmd += list(extra_args or [])
    cmd.append(str(file))
    return subprocess.run(cmd, capture_output=True, text=True)
