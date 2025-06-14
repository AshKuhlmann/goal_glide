from __future__ import annotations

import sys
from pathlib import Path as _Path

sys.path.insert(0, str(_Path(__file__).resolve().parents[1]))

from pathlib import Path

from click.testing import CliRunner

from goal_glide.cli import goal
from goal_glide.models.goal import Priority
from goal_glide.models.storage import Storage


def test_add_with_priority(tmp_path: Path, runner: CliRunner) -> None:
    result = runner.invoke(goal, ["add", "Test goal", "-p", "high"])
    assert result.exit_code == 0
    storage = Storage(tmp_path / "db.json")
    goals = storage.list_goals()
    assert goals[0].priority == Priority.high


def test_add_with_deadline(tmp_path: Path, runner: CliRunner) -> None:
    runner.invoke(goal, ["add", "Test goal", "--deadline", "2030-01-01"])
    storage = Storage(tmp_path / "db.json")
    goals = storage.list_goals()
    assert goals[0].deadline.strftime("%Y-%m-%d") == "2030-01-01"


def test_archive_sets_flag(tmp_path: Path, runner: CliRunner) -> None:
    result = runner.invoke(goal, ["add", "Test goal"])
    assert result.exit_code == 0
    goal_id = Storage(tmp_path / "db.json").list_goals()[0].id
    result = runner.invoke(goal, ["archive", goal_id])
    assert result.exit_code == 0
    assert Storage(tmp_path / "db.json").get_goal(goal_id).archived is True


def test_restore_unsets_flag(tmp_path: Path, runner: CliRunner) -> None:
    result = runner.invoke(goal, ["add", "Test goal"])
    gid = Storage(tmp_path / "db.json").list_goals()[0].id
    runner.invoke(goal, ["archive", gid])
    result = runner.invoke(goal, ["restore", gid])
    assert result.exit_code == 0
    assert Storage(tmp_path / "db.json").get_goal(gid).archived is False


def test_list_filters_priority_and_archived(tmp_path: Path, runner: CliRunner) -> None:
    runner.invoke(goal, ["add", "g1", "-p", "low"])
    runner.invoke(goal, ["add", "g2", "-p", "high"])
    gid = [
        g
        for g in Storage(tmp_path / "db.json").list_goals()
        if g.priority == Priority.low
    ][0].id
    runner.invoke(goal, ["archive", gid])
    result = runner.invoke(goal, ["list", "--priority", "high"])
    assert "g2" in result.output
    assert "g1" not in result.output
    result = runner.invoke(goal, ["list", "--archived"])
    assert "g1" in result.output
    assert "g2" not in result.output


def test_errors_on_double_archive(tmp_path: Path, runner: CliRunner) -> None:
    runner.invoke(goal, ["add", "g1"])
    storage = Storage(tmp_path / "db.json")
    gid = storage.list_goals()[0].id
    runner.invoke(goal, ["archive", gid])
    result = runner.invoke(goal, ["archive", gid])
    assert result.exit_code != 0
    assert "already archived" in result.output


def test_archive_restore_keeps_tags(tmp_path: Path, runner: CliRunner) -> None:
    runner.invoke(goal, ["add", "g"])
    gid = Storage(tmp_path / "db.json").list_goals()[0].id
    runner.invoke(goal, ["tag", "add", gid, "a", "b"])
    runner.invoke(goal, ["archive", gid])
    assert Storage(tmp_path / "db.json").get_goal(gid).tags == ["a", "b"]
    runner.invoke(goal, ["restore", gid])
    assert Storage(tmp_path / "db.json").get_goal(gid).tags == ["a", "b"]


def test_archive_nonexistent_id(runner: CliRunner) -> None:
    result = runner.invoke(goal, ["archive", "bad-id"])
    assert result.exit_code == 1
    assert "not found" in result.output


def test_restore_nonexistent_id(runner: CliRunner) -> None:
    result = runner.invoke(goal, ["restore", "bad-id"])
    assert result.exit_code == 1
    assert "not found" in result.output


def test_restore_not_archived(tmp_path: Path, runner: CliRunner) -> None:
    runner.invoke(goal, ["add", "g"])
    gid = Storage(tmp_path / "db.json").list_goals()[0].id
    result = runner.invoke(goal, ["restore", gid])
    assert result.exit_code == 1
    assert "not archived" in result.output


def test_list_all_includes_archived(tmp_path: Path, runner: CliRunner) -> None:
    runner.invoke(goal, ["add", "g1"])
    gid1 = Storage(tmp_path / "db.json").list_goals()[0].id
    runner.invoke(goal, ["archive", gid1])
    runner.invoke(goal, ["add", "g2"])
    result = runner.invoke(goal, ["list"])
    assert "g2" in result.output and "g1" not in result.output
    result = runner.invoke(goal, ["list", "--all"])
    assert "g1" in result.output and "g2" in result.output


def test_list_archived_priority_filter(tmp_path: Path, runner: CliRunner) -> None:
    runner.invoke(goal, ["add", "a", "-p", "low"])
    runner.invoke(goal, ["add", "b", "-p", "high"])
    runner.invoke(goal, ["add", "c", "-p", "low"])
    goals = Storage(tmp_path / "db.json").list_goals()
    for g in goals:
        runner.invoke(goal, ["archive", g.id])
    result = runner.invoke(goal, ["list", "--archived", "--priority", "high"])
    assert "b" in result.output
    assert "| a |" not in result.output
    assert "| c |" not in result.output


def test_list_shows_completed(tmp_path: Path, runner: CliRunner) -> None:
    runner.invoke(goal, ["add", "g"])
    gid = Storage(tmp_path / "db.json").list_goals()[0].id
    runner.invoke(goal, ["complete", gid])
    result = runner.invoke(goal, ["list"])
    assert "Comple" in result.output
