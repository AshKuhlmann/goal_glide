import random

import click
from click.testing import CliRunner

import pytest

from goal_glide.cli import handle_exceptions
from goal_glide.exceptions import (
    GoalAlreadyArchivedError,
    GoalNotArchivedError,
    GoalNotFoundError,
    InvalidTagError,
)


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


@pytest.mark.parametrize(
    "exc",
    [ZeroDivisionError("oops"), MemoryError("oom")],
)
def test_really_unexpected_error(exc):
    r = CliRunner().invoke(_fake_cmd(exc))
    assert r.exit_code == 1
    assert "unexpected" in r.output.lower()


@pytest.mark.parametrize(
    "exc",
    [
        GoalAlreadyArchivedError("a"),
        GoalNotArchivedError("b"),
        InvalidTagError("c"),
        click.ClickException("bad"),
        RuntimeError("boom"),
        ValueError("val"),
    ],
)
def test_all_expected_errors(exc):
    r = CliRunner().invoke(_fake_cmd(exc))
    assert r.exit_code == 1
    assert "Error:" in r.output


def test_system_exit_passthrough():
    @click.command()
    @handle_exceptions
    def _cmd():
        raise SystemExit(3)

    r = CliRunner().invoke(_cmd)
    assert r.exit_code == 3
    assert r.output == ""


def test_success_and_metadata_preserved():
    @handle_exceptions
    def sample():
        """doc string"""
        return 42

    assert sample.__name__ == "sample"
    assert sample.__doc__ == "doc string"
    assert sample() == 42


def test_assertion_error_unexpected():
    r = CliRunner().invoke(_fake_cmd(AssertionError("oops")))
    assert r.exit_code == 1
    assert "unexpected" in r.output.lower()


def test_random_expected_error():
    random.seed(0)
    exc_cls = random.choice(
        [
            GoalNotFoundError,
            GoalAlreadyArchivedError,
            GoalNotArchivedError,
            InvalidTagError,
            click.ClickException,
            RuntimeError,
            ValueError,
        ]
    )
    r = CliRunner().invoke(_fake_cmd(exc_cls("x")))
    assert r.exit_code == 1
    assert "Error:" in r.output


def test_click_bad_parameter_error():
    r = CliRunner().invoke(_fake_cmd(click.BadParameter("oops")))
    assert r.exit_code == 1
    assert "Error:" in r.output


@pytest.mark.parametrize("exc", [KeyboardInterrupt()])
def test_keyboard_interrupt_unexpected(exc):
    r = CliRunner().invoke(_fake_cmd(exc))
    assert r.exit_code == 1
    assert "aborted" in r.output.lower()
