import pytest
from click.testing import CliRunner
from pathlib import Path
from goal_glide.cli import cli
from goal_glide.models.storage import Storage


@pytest.fixture()
def runner(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> CliRunner:
    monkeypatch.setenv("GOAL_GLIDE_DB_DIR", str(tmp_path))
    return CliRunner()


def test_complete_and_reopen(tmp_path: Path, runner: CliRunner) -> None:
    runner.invoke(cli, ["goal", "add", "g"], env={"GOAL_GLIDE_DB_DIR": str(tmp_path)})
    gid = Storage(tmp_path).list_goals()[0].id
    result = runner.invoke(
        cli, ["goal", "complete", gid], env={"GOAL_GLIDE_DB_DIR": str(tmp_path)}
    )
    assert result.exit_code == 0
    assert Storage(tmp_path).get_goal(gid).completed is True
    result = runner.invoke(
        cli, ["goal", "reopen", gid], env={"GOAL_GLIDE_DB_DIR": str(tmp_path)}
    )
    assert result.exit_code == 0
    assert Storage(tmp_path).get_goal(gid).completed is False
