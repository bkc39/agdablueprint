"""Scaffold a new Agda blueprint project from the bundled templates.

This is the Agda counterpart of ``leanblueprint new``: it emits a ready-to-build
blueprint layout (``plastex.cfg``, ``blueprint/src/{web,print,content}.tex``, the
``agdablueprint.sty`` + ``macros/*.tex`` LaTeX layer, a ``latexmkrc`` and a CI
workflow) so a project gets the one-command ``agdablueprint web/pdf/all``
workflow with no manual wiring.

The convention (shared with leanblueprint) is that ``blueprint/`` sits next to
the Agda code at the project root, so the ``.agda-lib`` and ``blueprint/`` are
siblings. The web build writes ``blueprint/agda_decls`` — exactly where
``agdablueprint checkdecls`` looks for it.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

from jinja2 import Template

TEMPLATES_DIR = Path(__file__).parent / "templates"
PROJECT_DIR = TEMPLATES_DIR / "project"
JINJA_SUFFIX = ".jinja"

# Verbatim LaTeX layer copied into blueprint/src/ (not templated).
VERBATIM_MACROS = ("common.tex", "web.tex", "print.tex")


@dataclass
class ProjectMetadata:
    """Values substituted into the project templates."""

    title: str = "Blueprint"
    author: str = ""
    github: str = ""
    home: str = ""
    dochome: str = ""

    def as_context(self) -> dict[str, str]:
        # ``home`` defaults to the GitHub URL when not given separately.
        return {
            "title": self.title,
            "author": self.author,
            "github": self.github,
            "home": self.home or self.github,
            "dochome": self.dochome,
        }


class ProjectExists(RuntimeError):
    """Raised when the destination already contains a blueprint and not forced."""


def scaffold_project(
    dest: str | Path,
    metadata: ProjectMetadata,
    force: bool = False,
) -> Path:
    """Render the project template tree into ``dest`` and return its path."""
    dest = Path(dest)
    blueprint_dir = dest / "blueprint"
    if blueprint_dir.exists() and not force:
        raise ProjectExists(
            f"{blueprint_dir} already exists; pass force=True to overwrite."
        )

    context = metadata.as_context()
    _render_tree(PROJECT_DIR, dest, context)

    # Copy the verbatim LaTeX layer (shared with the pdf build) into the project.
    src_dir = dest / "blueprint" / "src"
    macros_dir = src_dir / "macros"
    macros_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy(
        TEMPLATES_DIR / "agdablueprint.sty", src_dir / "agdablueprint.sty"
    )
    for name in VERBATIM_MACROS:
        shutil.copy(TEMPLATES_DIR / "macros" / name, macros_dir / name)

    return dest


def _render_tree(
    template_root: Path, dest: Path, context: dict[str, str]
) -> None:
    """Mirror ``template_root`` into ``dest``, rendering ``*.jinja`` files.

    A leading ``github/`` path component is remapped to ``.github/`` (the literal
    dotted directory is avoided in the package data tree).
    """
    for path in sorted(template_root.rglob("*")):
        if path.is_dir():
            continue
        rel = path.relative_to(template_root)
        parts = list(rel.parts)
        if parts[0] == "github":
            parts[0] = ".github"
        out = dest.joinpath(*parts)

        if out.suffix == JINJA_SUFFIX:
            out = out.with_suffix("")
            out.parent.mkdir(parents=True, exist_ok=True)
            rendered = Template(path.read_text()).render(**context)
            out.write_text(rendered)
        else:
            out.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(path, out)
