from click.testing import CliRunner
from pathlib import Path
from goal_glide.cli import cli
from goal_glide.models.storage import Storage


def test_complete_and_reopen(tmp_path: Path, runner: CliRunner) -> None:
    db_path = tmp_path / "db.json"
    runner.invoke(cli, ["goal", "add", "g"])
    gid = Storage(db_path).list_goals()[0].id
    result = runner.invoke(cli, ["goal", "complete", gid])
    assert result.exit_code == 0
    assert Storage(db_path).get_goal(gid).completed is True
    result = runner.invoke(cli, ["goal", "reopen", gid])
    assert result.exit_code == 0
    assert Storage(db_path).get_goal(gid).completed is False