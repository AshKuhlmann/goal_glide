from click.testing import CliRunner
from pathlib import Path

import pytest

from goal_glide import config as cfg

from goal_glide.cli import cli


@pytest.fixture()
def quotes_runner(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> CliRunner:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("GOAL_GLIDE_DB_DIR", str(tmp_path))
    cfg._CONFIG_PATH = tmp_path / ".goal_glide" / "config.toml"
    cfg._CONFIG_CACHE = None
    return CliRunner()


def test_add_list_remove(tmp_path):
    runner = CliRunner()

    # add goal
    result = runner.invoke(
        cli, ["add", "Test Goal"], env={"GOAL_GLIDE_DB_DIR": str(tmp_path)}
    )
    assert result.exit_code == 0

    # list
    result = runner.invoke(cli, ["list"], env={"GOAL_GLIDE_DB_DIR": str(tmp_path)})
    assert "Test Goal" in result.output

    # remove
    # get id from list output
    lines = [line for line in result.output.splitlines() if "Test Goal" in line]
    goal_id = lines[0].split()[0]
    result = runner.invoke(
        cli,
        ["remove", goal_id],
        input="y\n",
        env={"GOAL_GLIDE_DB_DIR": str(tmp_path)},
    )
    assert result.exit_code == 0


def test_quotes_disable_enable(quotes_runner: CliRunner) -> None:
    result = quotes_runner.invoke(cli, ["config", "quotes", "--disable"])
    assert result.exit_code == 0
    assert "Quotes are OFF" in result.output
    assert cfg.quotes_enabled() is False

    result = quotes_runner.invoke(cli, ["config", "quotes", "--enable"])
    assert result.exit_code == 0
    assert "Quotes are ON" in result.output
    assert cfg.quotes_enabled() is True
