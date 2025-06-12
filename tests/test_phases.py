from pathlib import Path
from click.testing import CliRunner

from goal_glide.cli import goal
from goal_glide.models.storage import Storage


def test_add_phase(tmp_path: Path, runner: CliRunner) -> None:
    runner.invoke(goal, ["add", "g"])
    gid = Storage(tmp_path / "db.json").list_goals()[0].id
    result = runner.invoke(goal, ["phase", "add", gid, "plan"])
    assert result.exit_code == 0
    assert "plan" in result.output
    assert Storage(tmp_path / "db.json").get_goal(gid).phases == ["plan"]


def test_remove_phase(tmp_path: Path, runner: CliRunner) -> None:
    runner.invoke(goal, ["add", "g"])
    gid = Storage(tmp_path / "db.json").list_goals()[0].id
    runner.invoke(goal, ["phase", "add", gid, "a", "b"])
    result = runner.invoke(goal, ["phase", "rm", gid, "a"])
    assert result.exit_code == 0
    assert Storage(tmp_path / "db.json").get_goal(gid).phases == ["b"]


def test_remove_nonexistent_phase_warns(tmp_path: Path, runner: CliRunner) -> None:
    runner.invoke(goal, ["add", "g"])
    gid = Storage(tmp_path / "db.json").list_goals()[0].id
    result = runner.invoke(goal, ["phase", "rm", gid, "none"])
    assert result.exit_code == 0
    assert "not present" in result.output
