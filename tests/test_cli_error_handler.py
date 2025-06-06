import click
from click.testing import CliRunner

from goal_glide.cli import handle_exceptions
from goal_glide.exceptions import GoalNotFoundError


def _fake_cmd(exc):
    @click.command()
    @handle_exceptions
    def _cmd():
        raise exc

    return _cmd


def test_expected_error():
    r = CliRunner().invoke(_fake_cmd(GoalNotFoundError("bad id")))
    assert r.exit_code == 1
    assert "Error:" in r.output


def test_unexpected_error():
    r = CliRunner().invoke(_fake_cmd(RuntimeError("boom")))
    assert r.exit_code == 1
    assert "Error:" in r.output


def test_really_unexpected_error():
    r = CliRunner().invoke(_fake_cmd(ZeroDivisionError("oops")))
    assert r.exit_code == 1
    assert "unexpected" in r.output.lower()
