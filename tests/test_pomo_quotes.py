from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

from goal_glide import cli
from goal_glide import config as cfg
from goal_glide.services import quotes


@pytest.fixture()
def runner(monkeypatch, tmp_path: Path) -> CliRunner:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("GOAL_GLIDE_DB_DIR", str(tmp_path))
    cfg._CONFIG_PATH = tmp_path / ".goal_glide" / "config.toml"
    cfg._CONFIG_CACHE = None
    return CliRunner()


def test_pomo_stop_prints_quote(
    monkeypatch: pytest.MonkeyPatch, runner: CliRunner
) -> None:
    monkeypatch.setattr(quotes, "get_random_quote", lambda use_online=True: ("Q", "A"))
    monkeypatch.setattr(cli, "get_random_quote", lambda use_online=True: ("Q", "A"))
    runner.invoke(cli.goal, ["pomo", "start", "--duration", "1"])
    result = runner.invoke(cli.goal, ["pomo", "stop"])
    assert "Pomodoro complete" in result.output
    assert "Q" in result.output


def test_quotes_disabled(
    monkeypatch: pytest.MonkeyPatch, runner: CliRunner, tmp_path: Path
) -> None:
    path = tmp_path / ".goal_glide" / "config.toml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("quotes_enabled = false", encoding="utf-8")
    cfg._CONFIG_CACHE = None
    monkeypatch.setattr(quotes, "get_random_quote", lambda use_online=True: ("Q", "A"))
    monkeypatch.setattr(cli, "get_random_quote", lambda use_online=True: ("Q", "A"))
    runner.invoke(cli.goal, ["pomo", "start", "--duration", "1"])
    result = runner.invoke(cli.goal, ["pomo", "stop"])
    assert "Pomodoro complete" in result.output
    assert "Q" not in result.output
