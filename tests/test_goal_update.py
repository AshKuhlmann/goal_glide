from pathlib import Path

from click.testing import CliRunner

from goal_glide.cli import cli
from goal_glide.models.goal import Priority
from goal_glide.models.storage import Storage


def test_update_title(tmp_path: Path, runner: CliRunner) -> None:
    runner.invoke(cli, ["goal", "add", "old title"])
    gid = Storage(tmp_path).list_goals()[0].id
    result = runner.invoke(cli, ["goal", "update", gid, "--title", "new title"])
    assert result.exit_code == 0
    assert Storage(tmp_path).get_goal(gid).title == "new title"


def test_update_priority(tmp_path: Path, runner: CliRunner) -> None:
    runner.invoke(cli, ["goal", "add", "g"])
    gid = Storage(tmp_path).list_goals()[0].id
    result = runner.invoke(cli, ["goal", "update", gid, "--priority", "high"])
    assert result.exit_code == 0
    assert Storage(tmp_path).get_goal(gid).priority == Priority.high


def test_update_deadline(tmp_path: Path, runner: CliRunner) -> None:
    runner.invoke(cli, ["goal", "add", "g"])
    gid = Storage(tmp_path).list_goals()[0].id
    result = runner.invoke(
        cli,
        ["goal", "update", gid, "--deadline", "2030-01-01"],
    )
    assert result.exit_code == 0
    assert (
        Storage(tmp_path).get_goal(gid).deadline.strftime("%Y-%m-%d")
        == "2030-01-01"
    )
