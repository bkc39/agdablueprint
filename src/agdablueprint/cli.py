"""Command-line interface for agdablueprint.

Phase 1 stub: wires up the ``click`` command group and the ``version`` command
so the ``agdablueprint`` entry point is functional. The ``new``, ``pdf``,
``web``, ``checkdecls``, ``serve``, and ``all`` subcommands are implemented in
later phases.
"""

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

    for name in result.present:
        click.echo(f"  {click.style('ok', fg='green')}  {name}")
    for name in result.missing:
        click.echo(f"  {click.style('MISSING', fg='red')}  {name}")
    for err in result.errors:
        click.echo(click.style("agda error:\n", fg="red") + err)

    summary = f"{len(result.present)} present, {len(result.missing)} missing"
    if result.ok:
        click.echo(
            click.style(
                f"All {len(result.present)} declarations found.", fg="green"
            )
        )
    else:
        click.echo(
            click.style(f"checkdecls failed: {summary}.", fg="red"), err=True
        )
        raise SystemExit(1)


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
