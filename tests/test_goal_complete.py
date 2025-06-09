from click.testing import CliRunner
from pathlib import Path
from goal_glide.cli import goal
from goal_glide.models.storage import Storage


def test_complete_and_reopen(tmp_path: Path, runner: CliRunner) -> None:
    runner.invoke(goal, ["add", "g"])
    gid = Storage(tmp_path).list_goals()[0].id
    result = runner.invoke(goal, ["complete", gid])
    assert result.exit_code == 0
    assert Storage(tmp_path).get_goal(gid).completed is True
    result = runner.invoke(goal, ["reopen", gid])
    assert result.exit_code == 0
    assert Storage(tmp_path).get_goal(gid).completed is False
