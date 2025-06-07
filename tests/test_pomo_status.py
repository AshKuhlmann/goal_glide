from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

from goal_glide import cli
from goal_glide import config as cfg


@pytest.fixture()
def runner(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> CliRunner:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("GOAL_GLIDE_DB_DIR", str(tmp_path))
    cfg._CONFIG_PATH = tmp_path / ".goal_glide" / "config.toml"
    cfg._CONFIG_CACHE = None
    return CliRunner()


def test_status_shows_time(monkeypatch: pytest.MonkeyPatch, runner: CliRunner) -> None:
    runner.invoke(cli.goal, ["pomo", "start", "--duration", "2"])
    result = runner.invoke(cli.goal, ["pomo", "status"])
    assert "remaining" in result.output.lower()
    assert "2m" in result.output
    runner.invoke(cli.goal, ["pomo", "stop"])


def test_status_no_session(runner: CliRunner) -> None:
    result = runner.invoke(cli.goal, ["pomo", "status"])
    assert "no active session" in result.output.lower()
