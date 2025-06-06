import click
from click.testing import CliRunner

from goal_glide.cli import handle_exceptions
from goal_glide.exceptions import GoalNotFoundError


def _make_fake_command(exc):
    @click.command()
    @handle_exceptions
    def cmd():
        raise exc

    return cmd


def test_domain_exception_caught():
    runner = CliRunner()
    result = runner.invoke(_make_fake_command(GoalNotFoundError("bad id")))
    assert result.exit_code == 1
    assert "Error:" in result.output


def test_unexpected_exception_caught():
    runner = CliRunner()
    result = runner.invoke(_make_fake_command(ValueError("boom")))
    assert result.exit_code == 1
    assert "unexpected" in result.output.lower()
