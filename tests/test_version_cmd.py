from click.testing import CliRunner

from goal_glide import __version__; from goal_glide.cli import cli


def test_version_command_outputs_package_version() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["version"])
    assert result.exit_code == 0
    assert __version__ in result.output
