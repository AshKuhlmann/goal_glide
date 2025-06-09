from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

from goal_glide.cli import cli
from goal_glide.services import quotes
from goal_glide import config


def test_pomo_stop_prints_quote(
    monkeypatch: pytest.MonkeyPatch, runner: CliRunner, tmp_path: Path
) -> None:
    monkeypatch.setattr(quotes, "get_random_quote", lambda use_online=True: ("Q", "A"))
    env = {"GOAL_GLIDE_DB_DIR": str(tmp_path), "HOME": str(tmp_path)}
    runner.invoke(cli, ["pomo", "start", "--duration", "1"], env=env)
    result = runner.invoke(cli, ["pomo", "stop"], env=env)
    assert "Pomodoro complete" in result.output
    assert "Q" in result.output


def test_quotes_disabled(
    monkeypatch: pytest.MonkeyPatch, runner: CliRunner, tmp_path: Path
) -> None:
    (tmp_path / "config.toml").write_text("quotes_enabled = false", encoding="utf-8")
    monkeypatch.setattr(quotes, "get_random_quote", lambda use_online=True: ("Q", "A"))
    env = {"GOAL_GLIDE_DB_DIR": str(tmp_path), "HOME": str(tmp_path)}
    runner.invoke(cli, ["pomo", "start", "--duration", "1"], env=env)
    result = runner.invoke(cli, ["pomo", "stop"], env=env)
    assert "Pomodoro complete" in result.output
    assert "Q" not in result.output


def test_quote_fallback(
    monkeypatch: pytest.MonkeyPatch, runner: CliRunner, tmp_path: Path
) -> None:
    monkeypatch.setattr(
        quotes.requests,
        "get",
        lambda *a, **k: (_ for _ in ()).throw(quotes.requests.RequestException()),
    )
    monkeypatch.setattr(quotes, "_LOCAL_CACHE", None)
    monkeypatch.setattr(quotes.random, "choice", lambda seq: seq[0])
    env = {"GOAL_GLIDE_DB_DIR": str(tmp_path), "HOME": str(tmp_path)}
    runner.invoke(cli, ["pomo", "start", "--duration", "1"], env=env)
    result = runner.invoke(cli, ["pomo", "stop"], env=env)
    assert "Inspirational quote 1" in result.output


def test_quote_exception_handling(
    monkeypatch: pytest.MonkeyPatch, runner: CliRunner, tmp_path: Path
) -> None:

    def boom(use_online: bool = True) -> tuple[str, str]:
        raise RuntimeError("boom")

    monkeypatch.setattr(quotes, "get_random_quote", boom)
    env = {"GOAL_GLIDE_DB_DIR": str(tmp_path), "HOME": str(tmp_path)}
    runner.invoke(cli, ["pomo", "start", "--duration", "1"], env=env)
    result = runner.invoke(cli, ["pomo", "stop"], env=env)
    assert result.exit_code == 1
    assert "unexpected" in result.output.lower()


def test_quotes_default_enabled(
    monkeypatch: pytest.MonkeyPatch, runner: CliRunner, tmp_path: Path
) -> None:
    env = {"GOAL_GLIDE_DB_DIR": str(tmp_path), "HOME": str(tmp_path)}
    result = runner.invoke(cli, ["config", "quotes"], env=env)
    assert result.exit_code == 0
    assert "Quotes are ON" in result.output


def test_quotes_disabled_no_call(
    monkeypatch: pytest.MonkeyPatch, runner: CliRunner, tmp_path: Path
) -> None:
    (tmp_path / "config.toml").write_text("quotes_enabled = false", encoding="utf-8")
    called: list[bool] = []

    def fake(use_online: bool = True) -> tuple[str, str]:
        called.append(True)
        return ("Q", "A")

    monkeypatch.setattr(quotes, "get_random_quote", fake)
    env = {"GOAL_GLIDE_DB_DIR": str(tmp_path), "HOME": str(tmp_path)}
    runner.invoke(cli, ["pomo", "start", "--duration", "1"], env=env)
    result = runner.invoke(cli, ["pomo", "stop"], env=env)
    assert called == []
    assert "Pomodoro complete" in result.output
    assert "Q" not in result.output