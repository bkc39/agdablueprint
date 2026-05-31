"""Command-line interface for agdablueprint.

Wires up the ``click`` command group and the user-facing workflow: ``new``
scaffolds a project, ``web``/``pdf``/``serve`` build and preview the blueprint,
``checkdecls`` verifies ``\\agda{...}`` declarations against the Agda project, and
``all`` runs pdf + web + checkdecls in one shot.
"""

import shutil
import subprocess
import sys
from pathlib import Path

import click

from agdablueprint import __version__


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.version_option(__version__, prog_name="agdablueprint")
def cli() -> None:
    """Blueprint-style coordination tooling for Agda formalization projects."""


@cli.command()
def version() -> None:
    """Print the agdablueprint version."""
    click.echo(__version__)


@cli.command()
@click.option(
    "--project",
    "project_root",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=".",
    help="Root of the Agda project (directory containing the .agda-lib). "
    "Defaults to the current directory.",
)
@click.option(
    "--decls",
    "decls_file",
    type=click.Path(path_type=Path),
    default=None,
    help="File listing the declaration names to check (one per line). Defaults "
    "to the 'agda_decls' file written by the web build.",
)
@click.option("--agda", default=None, help="Path to the agda executable.")
@click.argument("names", nargs=-1)
def checkdecls(project_root, decls_file, agda, names) -> None:
    """Verify that every \\agda{...} declaration exists in the Agda project.

    Declaration names come from NAMES if given, otherwise from the --decls file
    (default: the 'agda_decls' file produced by `agdablueprint web`).
    """
    from agdablueprint.agda import AgdaNotFound
    from agdablueprint.checkdecls import check_declarations, read_agda_decls

    to_check = list(names)
    if not to_check:
        candidate = decls_file or _default_decls_file(project_root)
        if candidate is None or not candidate.exists():
            raise click.UsageError(
                "No declaration names given and no agda_decls file found. "
                "Run `agdablueprint web` first, pass --decls, or list names."
            )
        to_check = read_agda_decls(candidate)

    if not to_check:
        click.echo("No declarations to check.")
        return

    try:
        result = check_declarations(to_check, project_root, agda=agda)
    except AgdaNotFound as exc:
        raise click.ClickException(str(exc))

    if not _report_check_result(result):
        raise SystemExit(1)


def _report_check_result(result) -> bool:
    """Print a CheckResult and return whether it passed."""
    for name in result.present:
        click.echo(f"  {click.style('ok', fg='green')}  {name}")
    for name in result.missing:
        click.echo(f"  {click.style('MISSING', fg='red')}  {name}")
    for err in result.errors:
        click.echo(click.style("agda error:\n", fg="red") + err)

    if result.ok:
        click.echo(
            click.style(
                f"All {len(result.present)} declarations found.", fg="green"
            )
        )
        return True
    summary = f"{len(result.present)} present, {len(result.missing)} missing"
    click.echo(
        click.style(f"checkdecls failed: {summary}.", fg="red"), err=True
    )
    return False


@cli.command()
@click.option(
    "--dest",
    type=click.Path(file_okay=False, path_type=Path),
    default=".",
    help="Directory to scaffold the project into. Defaults to the current "
    "directory.",
)
@click.option("--title", default=None, help="Blueprint title.")
@click.option("--author", default=None, help="Author name.")
@click.option("--github", default=None, help="Project GitHub URL.")
@click.option(
    "--dochome",
    default=None,
    help="Base URL of the generated Agda HTML docs (agda --html output).",
)
@click.option(
    "--defaults",
    "-y",
    is_flag=True,
    help="Use defaults for everything not given as a flag (no prompts).",
)
@click.option(
    "--force", is_flag=True, help="Overwrite an existing blueprint/ directory."
)
def new(dest, title, author, github, dochome, defaults, force) -> None:
    """Scaffold a new Agda blueprint project from the bundled templates."""
    from agdablueprint.scaffold import (
        ProjectExists,
        ProjectMetadata,
        scaffold_project,
    )

    if not defaults:
        if title is None:
            title = click.prompt("Project title", default="Blueprint")
        if author is None:
            author = click.prompt("Author", default="", show_default=False)
        if github is None:
            github = click.prompt("GitHub URL", default="", show_default=False)
        if dochome is None:
            dochome = click.prompt(
                "Agda HTML docs URL", default="", show_default=False
            )

    metadata = ProjectMetadata(
        title=title or "Blueprint",
        author=author or "",
        github=github or "",
        dochome=dochome or "",
    )
    try:
        scaffold_project(dest, metadata, force=force)
    except ProjectExists as exc:
        raise click.ClickException(str(exc))

    dest = Path(dest)
    click.echo(
        click.style("Scaffolded blueprint project at ", fg="green") + str(dest)
    )
    click.echo("Next steps:")
    click.echo("  - write your exposition in blueprint/src/content.tex")
    click.echo("  - `agdablueprint web` to build the dependency graph")
    click.echo("  - `agdablueprint all` to build + checkdecls")


@cli.command()
@click.option(
    "--blueprint",
    "blueprint_dir",
    type=click.Path(file_okay=False, path_type=Path),
    default="blueprint",
    show_default=True,
    help="Blueprint directory (contains src/web.tex).",
)
@click.option(
    "--dir",
    "out_dir",
    type=click.Path(file_okay=False, path_type=Path),
    default=None,
    help="HTML output directory. Defaults to <blueprint>/web.",
)
def web(blueprint_dir, out_dir) -> None:
    """Build the HTML dependency graph with plasTeX."""
    out_dir = _build_web(blueprint_dir, out_dir)
    click.echo(
        click.style("Web blueprint built at ", fg="green") + str(out_dir)
    )


@cli.command()
@click.option(
    "--blueprint",
    "blueprint_dir",
    type=click.Path(file_okay=False, path_type=Path),
    default="blueprint",
    show_default=True,
    help="Blueprint directory (contains src/print.tex).",
)
@click.option(
    "--dir",
    "out_dir",
    type=click.Path(file_okay=False, path_type=Path),
    default=None,
    help="PDF output directory. Defaults to <blueprint>/print.",
)
def pdf(blueprint_dir, out_dir) -> None:
    """Build the PDF blueprint with latexmk (or pdflatex)."""
    pdf_path = _build_pdf(blueprint_dir, out_dir)
    click.echo(click.style("PDF built at ", fg="green") + str(pdf_path))


@cli.command()
@click.option(
    "--blueprint",
    "blueprint_dir",
    type=click.Path(file_okay=False, path_type=Path),
    default="blueprint",
    show_default=True,
)
@click.option(
    "--dir",
    "web_dir",
    type=click.Path(file_okay=False, path_type=Path),
    default=None,
    help="Directory to serve. Defaults to <blueprint>/web.",
)
@click.option(
    "--port", default=8000, show_default=True, help="Port to serve on."
)
def serve(blueprint_dir, web_dir, port) -> None:
    """Serve the built web blueprint over HTTP."""
    web_dir = web_dir or (blueprint_dir / "web")
    if not web_dir.is_dir():
        raise click.ClickException(
            f"No web output at {web_dir}. Run `agdablueprint web` first."
        )
    click.echo(
        f"Serving {web_dir} at http://localhost:{port}/ (Ctrl-C to stop)"
    )
    try:
        subprocess.run(
            [
                sys.executable,
                "-m",
                "http.server",
                str(port),
                "--directory",
                str(web_dir),
            ]
        )
    except KeyboardInterrupt:
        pass


@cli.command(name="all")
@click.option(
    "--blueprint",
    "blueprint_dir",
    type=click.Path(file_okay=False, path_type=Path),
    default="blueprint",
    show_default=True,
)
@click.option(
    "--project",
    "project_root",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    default=".",
    help="Root of the Agda project (directory containing the .agda-lib).",
)
@click.option("--agda", default=None, help="Path to the agda executable.")
def all_(blueprint_dir, project_root, agda) -> None:
    """Build the PDF and web blueprints, then verify the Agda declarations."""
    from agdablueprint.agda import AgdaNotFound
    from agdablueprint.checkdecls import check_declarations, read_agda_decls

    _build_pdf(blueprint_dir, None)
    _build_web(blueprint_dir, None)

    decls_file = blueprint_dir / "agda_decls"
    names = read_agda_decls(decls_file) if decls_file.exists() else []
    if not names:
        click.echo("No \\agda{...} declarations to check.")
        return
    try:
        result = check_declarations(names, project_root, agda=agda)
    except AgdaNotFound as exc:
        raise click.ClickException(str(exc))
    if not _report_check_result(result):
        raise SystemExit(1)


def _require_tool(name: str) -> str:
    """Locate a build tool on PATH or raise a friendly click error."""
    path = shutil.which(name)
    if path is None:
        raise click.ClickException(
            f"Could not find '{name}' on PATH. Install it (the Nix dev shell "
            f"provides it) and try again."
        )
    return path


def _build_web(blueprint_dir: Path, out_dir: Path | None) -> Path:
    """Run plasTeX on blueprint/src/web.tex and return the output directory.

    plasTeX writes the ``agda_decls`` file (checkdecls' input) to the parent of
    its working directory, so it is run from ``blueprint/src`` to land the file
    at ``blueprint/agda_decls``.
    """
    src_dir = (blueprint_dir / "src").resolve()
    src = src_dir / "web.tex"
    if not src.exists():
        raise click.ClickException(
            f"No web.tex found at {src}. Run `agdablueprint new` first?"
        )
    plastex = _require_tool("plastex")
    out_dir = (out_dir or (blueprint_dir / "web")).resolve()

    cmd = [plastex, "--plugins=agdablueprint", f"--dir={out_dir}"]
    config = (blueprint_dir.parent / "plastex.cfg").resolve()
    if config.exists():
        cmd += ["--config", str(config)]
    cmd.append("web.tex")

    proc = subprocess.run(cmd, cwd=src_dir, capture_output=True, text=True)
    if proc.returncode != 0:
        raise click.ClickException(
            "plasTeX web build failed:\n" + proc.stdout + proc.stderr
        )
    return out_dir


def _build_pdf(blueprint_dir: Path, out_dir: Path | None) -> Path:
    """Build blueprint/src/print.tex to PDF and return the PDF path."""
    src_dir = (blueprint_dir / "src").resolve()
    src = src_dir / "print.tex"
    if not src.exists():
        raise click.ClickException(
            f"No print.tex found at {src}. Run `agdablueprint new` first?"
        )
    out_dir = (out_dir or (blueprint_dir / "print")).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    latexmk = shutil.which("latexmk")
    if latexmk is not None:
        cmd = [
            latexmk,
            "-pdf",
            "-interaction=nonstopmode",
            f"-outdir={out_dir}",
            "print.tex",
        ]
    else:
        pdflatex = _require_tool("pdflatex")
        cmd = [
            pdflatex,
            "-interaction=nonstopmode",
            f"-output-directory={out_dir}",
            "print.tex",
        ]

    proc = subprocess.run(cmd, cwd=src_dir, capture_output=True, text=True)
    pdf_path = out_dir / "print.pdf"
    if proc.returncode != 0 or not pdf_path.exists():
        raise click.ClickException(
            "PDF build failed:\n" + proc.stdout + proc.stderr
        )
    return pdf_path


def _default_decls_file(project_root: Path) -> Path | None:
    """Look for an agda_decls file near the project.

    The web build writes it next to the blueprint sources; check the project
    root and a sibling 'blueprint' directory.
    """
    for candidate in (
        project_root / "agda_decls",
        project_root / "blueprint" / "agda_decls",
    ):
        if candidate.exists():
            return candidate
    return None


if __name__ == "__main__":
    cli()
