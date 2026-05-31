"""Phase 1 smoke tests: the package imports and the CLI entry point works."""

from click.testing import CliRunner

import agdablueprint
from agdablueprint.cli import cli


def test_version_attribute():
    assert isinstance(agdablueprint.__version__, str)
    assert agdablueprint.__version__


def test_plugin_processoptions_importable():
    # plasTeX loads `\usepackage{agdablueprint}` from this package module and
    # calls its ProcessOptions.
    from agdablueprint.Packages import agdablueprint as pkg

    assert callable(pkg.ProcessOptions)
    # The Agda macro classes must be present so plasTeX's importMacros registers
    # them as LaTeX commands.
    for macro in ("agda", "agdaok", "agdanotready", "stdlibok", "notready"):
        assert hasattr(pkg, macro)


def test_cli_version_command():
    result = CliRunner().invoke(cli, ["version"])
    assert result.exit_code == 0
    assert agdablueprint.__version__ in result.output
