from __future__ import annotations

from pathlib import Path
from datetime import datetime, timedelta

import pytest
from click.testing import CliRunner

from goal_glide import cli
from goal_glide import config as cfg
from goal_glide.services import notify, reminder, pomodoro
from hypothesis import HealthCheck, given, settings, strategies as st
from typing import Callable

FIXED_NOW = datetime(2024, 1, 1, 12, 0, 0)


class FakeScheduler:
    def __init__(self) -> None:
        self.jobs: list[tuple[Callable, tuple, dict]] = []

    def add_job(self, func, _trigger, **kwargs) -> None:
        self.jobs.append((func, kwargs.get("args", ()), kwargs))

    def remove_all_jobs(self, jobstore: str | None = None) -> None:
        self.jobs.clear()


@pytest.fixture()
def runner(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> tuple[CliRunner, list[str]]:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("GOAL_GLIDE_DB_DIR", str(tmp_path))
    monkeypatch.setenv("GOAL_GLIDE_SESSION_FILE", str(tmp_path / "session.json"))
    import importlib
    importlib.reload(pomodoro)
    importlib.reload(reminder)
    cfg._CONFIG_PATH = tmp_path / ".goal_glide" / "config.toml"
    monkeypatch.setattr(reminder, "_sched", FakeScheduler())

    class FakeDT(datetime):
        @classmethod
        def now(cls) -> datetime:  # type: ignore[override]
            return FIXED_NOW

    monkeypatch.setattr(reminder, "datetime", FakeDT)
    messages: list[str] = []
    monkeypatch.setattr(notify, "push", lambda m: messages.append(m))
    monkeypatch.setattr(reminder, "push", lambda m: messages.append(m))
    return CliRunner(), messages


def test_flow_schedules_jobs(runner) -> None:
    cli_runner, messages = runner
    cli_runner.invoke(cli.goal, ["reminder", "enable"])
    gid = cli_runner.invoke(cli.goal, ["add", "g"])
    gid = gid.output.split()[-1].strip("()")
    cli_runner.invoke(cli.goal, ["pomo", "start", "--duration", "1"])
    result = cli_runner.invoke(cli.goal, ["pomo", "stop"])
    assert "reminders scheduled" in result.output
    sched = reminder._sched
    assert sched is not None
    assert len(sched.jobs) == 2  # type: ignore[attr-defined]
    for func, args, _ in sched.jobs:  # type: ignore[attr-defined]
        func(*args)
    assert any("Pomodoro" in m or "Break" in m for m in messages)


def test_flow_uses_config_and_clears_existing_jobs(runner) -> None:
    cli_runner, _ = runner
    cli_runner.invoke(cli.goal, ["reminder", "enable"])
    cli_runner.invoke(
        cli.goal,
        ["reminder", "config", "--break", "2", "--interval", "7"],
    )
    reminder.schedule_after_stop()
    reminder.schedule_after_stop()
    sched = reminder._sched
    assert sched is not None
    assert len(sched.jobs) == 2  # type: ignore[attr-defined]
    first_kwargs = sched.jobs[0][2]  # type: ignore[attr-defined]
    second_kwargs = sched.jobs[1][2]  # type: ignore[attr-defined]
    assert first_kwargs["run_date"] == FIXED_NOW + timedelta(minutes=2)
    assert second_kwargs["minutes"] == 7


def test_cancel_all_runs_on_new_session(runner, monkeypatch, tmp_path) -> None:
    cli_runner, _ = runner
    sched = reminder._sched
    assert sched is not None
    # pre-populate fake scheduler with dummy jobs
    sched.add_job(lambda: None, "interval")  # type: ignore[attr-defined]
    sched.add_job(lambda: None, "interval")  # type: ignore[attr-defined]
    assert len(sched.jobs) == 2  # type: ignore[attr-defined]

    pomodoro.start_session(1)

    assert sched.jobs == []  # type: ignore[attr-defined]


@given(
    break_min=st.integers(min_value=1, max_value=120),
    interval_min=st.integers(min_value=1, max_value=120),
)
@settings(max_examples=10, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_schedule_after_stop_randomized(
    runner, monkeypatch, break_min: int, interval_min: int
) -> None:
    """`schedule_after_stop` uses config values when scheduling."""
    _, _ = runner
    monkeypatch.setattr(reminder, "reminders_enabled", lambda: True)
    monkeypatch.setattr(reminder, "reminder_break", lambda: break_min)
    monkeypatch.setattr(reminder, "reminder_interval", lambda: interval_min)

    reminder.schedule_after_stop()

    sched = reminder._sched
    assert sched is not None
    assert len(sched.jobs) == 2  # type: ignore[attr-defined]
    first_kwargs = sched.jobs[0][2]  # type: ignore[attr-defined]
    second_kwargs = sched.jobs[1][2]  # type: ignore[attr-defined]
    assert first_kwargs["run_date"] == FIXED_NOW + timedelta(minutes=break_min)
    assert second_kwargs["minutes"] == interval_min
