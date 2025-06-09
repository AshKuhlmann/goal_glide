from __future__ import annotations

from pathlib import Path
import logging
import builtins
import sys
import types

import pytest
from click.testing import CliRunner

from goal_glide import cli
from goal_glide import config as cfg
from goal_glide.services import notify, reminder


@pytest.fixture(autouse=True)
def _cfg_path(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    cfg._CONFIG_PATH = tmp_path / ".goal_glide" / "config.toml"


def test_enable_disable_updates_config(runner: CliRunner) -> None:
    runner.invoke(cli.goal, ["reminder", "enable"])
    assert cfg.reminders_enabled() is True
    runner.invoke(cli.goal, ["reminder", "disable"])
    assert cfg.reminders_enabled() is False


def test_config_command_updates_values(runner: CliRunner) -> None:
    runner.invoke(cli.goal, ["reminder", "config", "--break", "10", "--interval", "15"])
    assert cfg.reminder_break() == 10
    assert cfg.reminder_interval() == 15


@pytest.mark.parametrize("val", [0, -5, 200])
def test_invalid_break_value_errors(val: int, runner: CliRunner) -> None:
    result = runner.invoke(cli.goal, ["reminder", "config", "--break", str(val)])
    assert result.exit_code != 0
    assert "break must be between 1 and 120" in result.output


@pytest.mark.parametrize("val", [0, -5, 200])
def test_invalid_interval_value_errors(val: int, runner: CliRunner) -> None:
    result = runner.invoke(cli.goal, ["reminder", "config", "--interval", str(val)])
    assert result.exit_code != 0
    assert "interval must be between 1 and 120" in result.output


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


def test_schedule_after_stop_creates_scheduler(monkeypatch: pytest.MonkeyPatch) -> None:
    created: list[reminder.BackgroundScheduler] = []
    started: list[bool] = []

    class FakeScheduler:
        def __init__(self, daemon: bool = False) -> None:
            created.append(self)  # type: ignore[arg-type]
            self.jobs: list[dict] = []

        def start(self) -> None:
            started.append(True)

        def remove_all_jobs(self, jobstore: str | None = None) -> None:
            self.jobs.clear()

        def add_job(
            self,
            func,
            _trigger,
            **kwargs,
        ) -> None:  # type: ignore[no-untyped-def]
            self.jobs.append(kwargs)

    monkeypatch.setattr(reminder, "BackgroundScheduler", FakeScheduler)
    monkeypatch.setattr(reminder, "_sched", None)
    monkeypatch.setattr(reminder, "reminders_enabled", lambda: True)

    reminder.schedule_after_stop()

    assert len(created) == 1
    assert started == [True]
    sched = reminder._sched
    assert sched is not None
    assert [job["id"] for job in sched.jobs] == ["break_end", "next_pomo"]


def test_reminder_status_output(runner: CliRunner) -> None:
    result = runner.invoke(cli.goal, ["reminder", "status"])
    assert result.exit_code == 0
    assert "Enabled: False | Break: 5m | Interval: 30m" in result.output

    runner.invoke(cli.goal, ["reminder", "enable"])
    runner.invoke(
        cli.goal,
        ["reminder", "config", "--break", "11", "--interval", "22"],
    )
    result = runner.invoke(cli.goal, ["reminder", "status"])
    assert result.exit_code == 0
    assert "Enabled: True | Break: 11m | Interval: 22m" in result.output


def test_unknown_os_logs_info(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setattr(notify.platform, "system", lambda: "UnknownOS")
    caplog.set_level(logging.INFO)
    notify.push("msg")
    assert any("No notifier for OS" in rec.message for rec in caplog.records)


def test_notifier_failure_logs_warning(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    def fail(_: str) -> None:
        raise RuntimeError("nope")

    monkeypatch.setitem(notify._OS_NOTIFIERS, "Darwin", fail)
    monkeypatch.setattr(notify.platform, "system", lambda: "Darwin")
    caplog.set_level(logging.WARNING)
    notify.push("boom")
    assert any("Notification failed" in rec.message for rec in caplog.records)


def test_missing_notifier_prints_hint(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(notify.platform, "system", lambda: "UnknownOS")
    notify.push("msg")
    captured = capsys.readouterr()
    assert "terminal-notifier" in captured.out


def test_failed_notifier_prints_hint(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def fail(_: str) -> None:
        raise RuntimeError("boom")

    monkeypatch.setitem(notify._OS_NOTIFIERS, "Linux", fail)
    monkeypatch.setattr(notify.platform, "system", lambda: "Linux")
    notify.push("oops")
    captured = capsys.readouterr()
    assert "notify2" in captured.out or "notify-send" in captured.out


def test_linux_notify_uses_notify2(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple] = []

    class FakeNotification:
        def __init__(self, title: str, message: str) -> None:
            calls.append(("Notification", title, message))

        def show(self) -> None:
            calls.append(("show",))

    fake_notify2 = types.SimpleNamespace(
        init=lambda name: calls.append(("init", name)),
        Notification=FakeNotification,
    )

    monkeypatch.setitem(sys.modules, "notify2", fake_notify2)
    monkeypatch.setattr(
        notify.subprocess,
        "run",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("subprocess used")),
    )

    notify._linux_notify("hi")

    assert calls == [
        ("init", "GoalGlide"),
        ("Notification", "Goal Glide", "hi"),
        ("show",),
    ]


def test_linux_notify_uses_notify_send(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delitem(sys.modules, "notify2", raising=False)

    orig_import = builtins.__import__

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "notify2":
            raise ModuleNotFoundError
        return orig_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    calls: list[list[str]] = []

    def fake_run(cmd: list[str], check: bool = False) -> None:
        calls.append(cmd)

    monkeypatch.setattr(notify.subprocess, "run", fake_run)

    notify._linux_notify("hey")

    assert calls == [["notify-send", "Goal Glide", "hey"]]


def test_linux_notify_fallback_on_error(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeNotification:
        def __init__(self, title: str, message: str) -> None:
            pass

        def show(self) -> None:
            raise RuntimeError("boom")

    fake_notify2 = types.SimpleNamespace(
        init=lambda name: None,
        Notification=FakeNotification,
    )

    monkeypatch.setitem(sys.modules, "notify2", fake_notify2)

    calls: list[list[str]] = []

    def fake_run(cmd: list[str], check: bool = False) -> None:
        calls.append(cmd)

    monkeypatch.setattr(notify.subprocess, "run", fake_run)

    notify._linux_notify("msg")

    assert calls == [["notify-send", "Goal Glide", "msg"]]


def test_mac_notify_invokes_terminal_notifier(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[list[str]] = []

    def fake_run(cmd: list[str], check: bool = False) -> None:
        calls.append(cmd)

    monkeypatch.setattr(notify.subprocess, "run", fake_run)

    notify._mac_notify("yo")

    assert calls == [["terminal-notifier", "-message", "yo"]]


def test_win_notify_invokes_toast(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, str, bool]] = []

    class FakeToastNotifier:
        def show_toast(self, title: str, message: str, threaded: bool = False) -> None:
            calls.append((title, message, threaded))

    fake_win10toast = types.SimpleNamespace(ToastNotifier=FakeToastNotifier)
    monkeypatch.setitem(sys.modules, "win10toast", fake_win10toast)

    notify._win_notify("hi")

    assert calls == [("Goal Glide", "hi", True)]


def test_scheduler_singleton(monkeypatch: pytest.MonkeyPatch) -> None:
    start_calls: list[str] = []

    class FakeScheduler:
        def __init__(self, daemon: bool = False) -> None:
            self.started = 0

        def start(self) -> None:
            self.started += 1
            start_calls.append("start")

    monkeypatch.setattr(reminder, "BackgroundScheduler", FakeScheduler)
    monkeypatch.setattr(reminder, "_sched", None)

    first = reminder._scheduler()
    second = reminder._scheduler()

    assert first is second
    assert len(start_calls) == 1


def test_cancel_all_calls_remove_all_jobs(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    class FakeScheduler:
        def remove_all_jobs(self) -> None:
            calls.append("removed")

    monkeypatch.setattr(reminder, "_sched", FakeScheduler())

    reminder.cancel_all()

    assert calls == ["removed"]


def test_cancel_all_no_scheduler(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(reminder, "_sched", None)

    reminder.cancel_all()

    assert reminder._sched is None
