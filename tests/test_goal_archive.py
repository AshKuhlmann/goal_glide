from __future__ import annotations

import sys
from pathlib import Path as _Path

sys.path.insert(0, str(_Path(__file__).resolve().parents[1]))

from pathlib import Path

import pytest
from click.testing import CliRunner

from goal_glide.cli import goal
from goal_glide.models.goal import Priority
from goal_glide.models.storage import Storage


@pytest.fixture()
def runner(monkeypatch, tmp_path: Path) -> CliRunner:
    monkeypatch.setenv("GOAL_GLIDE_DB_DIR", str(tmp_path))
    return CliRunner()


def test_add_with_priority(tmp_path: Path, runner: CliRunner) -> None:
    result = runner.invoke(goal, ["add", "Test goal", "-p", "high"])
    assert result.exit_code == 0
    storage = Storage(tmp_path)
    goals = storage.list_goals()
    assert goals[0].priority == Priority.high


def test_archive_sets_flag(tmp_path: Path, runner: CliRunner) -> None:
    result = runner.invoke(goal, ["add", "Test goal"])
    assert result.exit_code == 0
    goal_id = Storage(tmp_path).list_goals()[0].id
    result = runner.invoke(goal, ["archive", goal_id])
    assert result.exit_code == 0
    assert Storage(tmp_path).get_goal(goal_id).archived is True


def test_restore_unsets_flag(tmp_path: Path, runner: CliRunner) -> None:
    result = runner.invoke(goal, ["add", "Test goal"])
    gid = Storage(tmp_path).list_goals()[0].id
    runner.invoke(goal, ["archive", gid])
    result = runner.invoke(goal, ["restore", gid])
    assert result.exit_code == 0
    assert Storage(tmp_path).get_goal(gid).archived is False


def test_list_filters_priority_and_archived(tmp_path: Path, runner: CliRunner) -> None:
    runner.invoke(goal, ["add", "g1", "-p", "low"])
    runner.invoke(goal, ["add", "g2", "-p", "high"])
    gid = [g for g in Storage(tmp_path).list_goals() if g.priority == Priority.low][
        0
    ].id
    runner.invoke(goal, ["archive", gid])
    result = runner.invoke(goal, ["list", "--priority", "high"])
    assert "g2" in result.output
    assert "g1" not in result.output
    result = runner.invoke(goal, ["list", "--archived"])
    assert "g1" in result.output
    assert "g2" not in result.output


def test_errors_on_double_archive(tmp_path: Path, runner: CliRunner) -> None:
    runner.invoke(goal, ["add", "g1"])
    storage = Storage(tmp_path)
    gid = storage.list_goals()[0].id
    runner.invoke(goal, ["archive", gid])
    result = runner.invoke(goal, ["archive", gid])
    assert result.exit_code != 0
    assert "already archived" in result.output
