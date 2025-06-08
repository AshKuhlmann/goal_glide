from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

from goal_glide import cli
from goal_glide import config as cfg
from goal_glide.services import notify, reminder


@pytest.fixture()
def runner(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> CliRunner:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("GOAL_GLIDE_DB_DIR", str(tmp_path))
    cfg._CONFIG_PATH = tmp_path / ".goal_glide" / "config.toml"
    cfg._CONFIG_CACHE = None
    return CliRunner()


def test_enable_disable_updates_config(runner: CliRunner) -> None:
    runner.invoke(cli.goal, ["reminder", "enable"])
    assert cfg.reminders_enabled() is True
    runner.invoke(cli.goal, ["reminder", "disable"])
    assert cfg.reminders_enabled() is False


def test_config_command_updates_values(runner: CliRunner) -> None:
    runner.invoke(cli.goal, ["reminder", "config", "--break", "10", "--interval", "15"])
    assert cfg.reminder_break() == 10
    assert cfg.reminder_interval() == 15


def test_invalid_break_value_errors(runner: CliRunner) -> None:
    result = runner.invoke(cli.goal, ["reminder", "config", "--break", "200"])
    assert result.exit_code != 0


def test_notification_backend_selection(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: list[str] = []

    def fake(msg: str) -> None:
        captured.append(msg)

    monkeypatch.setattr(notify, "_mac_notify", fake)
    monkeypatch.setattr(notify, "_linux_notify", fake)
    monkeypatch.setattr(notify, "_win_notify", fake)
    monkeypatch.setitem(notify._OS_NOTIFIERS, "Darwin", fake)
    monkeypatch.setitem(notify._OS_NOTIFIERS, "Linux", fake)
    monkeypatch.setitem(notify._OS_NOTIFIERS, "Windows", fake)

    for osname in ["Darwin", "Linux", "Windows"]:
        captured.clear()
        monkeypatch.setattr(notify.platform, "system", lambda: osname)
        notify.push("hi")
        assert captured == ["hi"]


def test_schedule_after_stop_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(reminder, "_sched", None)
    monkeypatch.setattr(cfg, "reminders_enabled", lambda: False)
    reminder.schedule_after_stop()
    assert reminder._sched is None


def test_reminder_status_output(runner: CliRunner) -> None:
    runner.invoke(cli.goal, ["reminder", "enable"])
    runner.invoke(
        cli.goal,
        ["reminder", "config", "--break", "11", "--interval", "22"],
    )
    result = runner.invoke(cli.goal, ["reminder", "status"])
    assert result.exit_code == 0
    assert "Enabled: True | Break: 11m | Interval: 22m" in result.output
