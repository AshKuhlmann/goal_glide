from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner

from goal_glide.cli import cli
from goal_glide.models.storage import Storage


def test_add_single_tag(tmp_path: Path, runner: CliRunner) -> None:
    runner.invoke(cli, ["goal", "add", "g"])
    gid = Storage(tmp_path).list_goals()[0].id
    result = runner.invoke(cli, ["tag", "add", gid, "writing"])
    assert result.exit_code == 0
    assert "writing" in result.output
    assert Storage(tmp_path).get_goal(gid).tags == ["writing"]


def test_add_duplicate_tag_no_dupe(tmp_path: Path, runner: CliRunner) -> None:
    runner.invoke(cli, ["goal", "add", "g"])
    gid = Storage(tmp_path).list_goals()[0].id
    runner.invoke(cli, ["tag", "add", gid, "health"])
    result = runner.invoke(cli, ["tag", "add", gid, "health"])
    assert result.exit_code == 0
    assert Storage(tmp_path).get_goal(gid).tags == ["health"]


def test_add_invalid_tag_fails(tmp_path: Path, runner: CliRunner) -> None:
    runner.invoke(cli, ["goal", "add", "g"])
    gid = Storage(tmp_path).list_goals()[0].id
    result = runner.invoke(cli, ["tag", "add", gid, "BadTag!"])
    assert result.exit_code != 0
    assert not Storage(tmp_path).get_goal(gid).tags


def test_remove_tag(tmp_path: Path, runner: CliRunner) -> None:
    runner.invoke(cli, ["goal", "add", "g"])
    gid = Storage(tmp_path).list_goals()[0].id
    runner.invoke(cli, ["tag", "add", gid, "a", "b"])
    result = runner.invoke(cli, ["tag", "rm", gid, "a"])
    assert result.exit_code == 0
    assert Storage(tmp_path).get_goal(gid).tags == ["b"]


def test_remove_nonexistent_tag_warns(tmp_path: Path, runner: CliRunner) -> None:
    runner.invoke(cli, ["goal", "add", "g"])
    gid = Storage(tmp_path).list_goals()[0].id
    result = runner.invoke(cli, ["tag", "rm", gid, "none"])
    assert result.exit_code == 0
    assert "not present" in result.output


def test_list_filter_single_tag(tmp_path: Path, runner: CliRunner) -> None:
    runner.invoke(cli, ["goal", "add", "g1"])
    runner.invoke(cli, ["goal", "add", "g2"])
    goals = Storage(tmp_path).list_goals()
    runner.invoke(cli, ["tag", "add", goals[0].id, "work"])
    runner.invoke(cli, ["tag", "add", goals[1].id, "play"])
    result = runner.invoke(cli, ["goal", "list", "--tag", "work"])
    assert "g1" in result.output and "g2" not in result.output


def test_list_filter_multiple_tags_and_logic(tmp_path: Path, runner: CliRunner) -> None:
    runner.invoke(cli, ["goal", "add", "g1"])
    gid = Storage(tmp_path).list_goals()[0].id
    runner.invoke(cli, ["tag", "add", gid, "a", "b"])
    runner.invoke(cli, ["goal", "add", "g2"])
    gid2 = Storage(tmp_path).list_goals()[1].id
    runner.invoke(cli, ["tag", "add", gid2, "a"])
    result = runner.invoke(cli, ["goal", "list", "--tag", "a", "--tag", "b"])
    assert "g1" in result.output and "g2" not in result.output


def test_tag_list_counts(tmp_path: Path, runner: CliRunner) -> None:
    runner.invoke(cli, ["goal", "add", "g1"])
    runner.invoke(cli, ["goal", "add", "g2"])
    goals = Storage(tmp_path).list_goals()
    runner.invoke(cli, ["tag", "add", goals[0].id, "work", "fun"])
    runner.invoke(cli, ["tag", "add", goals[1].id, "work"])
    result = runner.invoke(cli, ["tag", "list"])
    assert result.exit_code == 0
    rows = [line for line in result.output.splitlines() if "│" in line]
    assert any("work" in r and "2" in r for r in rows)
    assert any("fun" in r and "1" in r for r in rows)
