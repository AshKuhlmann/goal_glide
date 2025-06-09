from click.testing import CliRunner

from goal_glide import __version__, cli


def test_version_command_outputs_package_version() -> None:
    runner = CliRunner()
    result = runner.invoke(cli.goal, ["version"])
    assert result.exit_code == 0
    assert __version__ in result.output
