from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

from goal_glide.cli import goal
from goal_glide.models.storage import Storage


@pytest.fixture()
def runner(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> CliRunner:
    monkeypatch.setenv("GOAL_GLIDE_DB_DIR", str(tmp_path))
    return CliRunner()


def test_add_single_tag(tmp_path: Path, runner: CliRunner) -> None:
    runner.invoke(goal, ["add", "g"])
    gid = Storage(tmp_path).list_goals()[0].id
    result = runner.invoke(goal, ["tag", "add", gid, "writing"])
    assert result.exit_code == 0
    assert "writing" in result.output
    assert Storage(tmp_path).get_goal(gid).tags == ["writing"]


def test_add_duplicate_tag_no_dupe(tmp_path: Path, runner: CliRunner) -> None:
    runner.invoke(goal, ["add", "g"])
    gid = Storage(tmp_path).list_goals()[0].id
    runner.invoke(goal, ["tag", "add", gid, "health"])
    result = runner.invoke(goal, ["tag", "add", gid, "health"])
    assert result.exit_code == 0
    assert Storage(tmp_path).get_goal(gid).tags == ["health"]


def test_add_invalid_tag_fails(tmp_path: Path, runner: CliRunner) -> None:
    runner.invoke(goal, ["add", "g"])
    gid = Storage(tmp_path).list_goals()[0].id
    result = runner.invoke(goal, ["tag", "add", gid, "BadTag!"])
    assert result.exit_code != 0
    assert not Storage(tmp_path).get_goal(gid).tags


def test_remove_tag(tmp_path: Path, runner: CliRunner) -> None:
    runner.invoke(goal, ["add", "g"])
    gid = Storage(tmp_path).list_goals()[0].id
    runner.invoke(goal, ["tag", "add", gid, "a", "b"])
    result = runner.invoke(goal, ["tag", "rm", gid, "a"])
    assert result.exit_code == 0
    assert Storage(tmp_path).get_goal(gid).tags == ["b"]


def test_remove_nonexistent_tag_warns(tmp_path: Path, runner: CliRunner) -> None:
    runner.invoke(goal, ["add", "g"])
    gid = Storage(tmp_path).list_goals()[0].id
    result = runner.invoke(goal, ["tag", "rm", gid, "none"])
    assert result.exit_code == 0
    assert "not present" in result.output


def test_list_filter_single_tag(tmp_path: Path, runner: CliRunner) -> None:
    runner.invoke(goal, ["add", "g1"])
    runner.invoke(goal, ["add", "g2"])
    goals = Storage(tmp_path).list_goals()
    runner.invoke(goal, ["tag", "add", goals[0].id, "work"])
    runner.invoke(goal, ["tag", "add", goals[1].id, "play"])
    result = runner.invoke(goal, ["list", "--tag", "work"])
    assert "g1" in result.output and "g2" not in result.output


def test_list_filter_multiple_tags_and_logic(tmp_path: Path, runner: CliRunner) -> None:
    runner.invoke(goal, ["add", "g1"])
    gid = Storage(tmp_path).list_goals()[0].id
    runner.invoke(goal, ["tag", "add", gid, "a", "b"])
    runner.invoke(goal, ["add", "g2"])
    gid2 = Storage(tmp_path).list_goals()[1].id
    runner.invoke(goal, ["tag", "add", gid2, "a"])
    result = runner.invoke(goal, ["list", "--tag", "a", "--tag", "b"])
    assert "g1" in result.output and "g2" not in result.output
