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
def reminder_runner(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, runner: CliRunner
) -> tuple[CliRunner, list[str], dict[str, str]]:
    import importlib
    importlib.reload(pomodoro)
    importlib.reload(reminder)
    env = {"GOAL_GLIDE_DB_DIR": str(tmp_path), "HOME": str(tmp_path)}
    monkeypatch.setattr(reminder, "_sched", FakeScheduler())

    class FakeDT(datetime):
        @classmethod
        def now(cls) -> datetime:  # type: ignore[override]
            return FIXED_NOW

    monkeypatch.setattr(reminder, "datetime", FakeDT)
    messages: list[str] = []
    monkeypatch.setattr(notify, "push", lambda m: messages.append(m))
    monkeypatch.setattr(reminder, "push", lambda m: messages.append(m))
    return runner, messages, env


def test_flow_schedules_jobs(reminder_runner) -> None:
    cli_runner, messages, env = reminder_runner
    cli_runner.invoke(cli.goal, ["reminder", "enable"], env=env)
    gid = cli_runner.invoke(cli.goal, ["add", "g"])
    gid = gid.output.split()[-1].strip("()")
    cli_runner.invoke(cli.goal, ["pomo", "start", "--duration", "1"], env=env)
    result = cli_runner.invoke(cli.goal, ["pomo", "stop"], env=env)
    assert "reminders scheduled" in result.output
    sched = reminder._sched
    assert sched is not None
    assert len(sched.jobs) == 2  # type: ignore[attr-defined]
    for func, args, _ in sched.jobs:  # type: ignore[attr-defined]
        func(*args)
    assert any("Pomodoro" in m or "Break" in m for m in messages)


def test_flow_uses_config_and_clears_existing_jobs(reminder_runner) -> None:
    cli_runner, _, env = reminder_runner
    cli_runner.invoke(cli.goal, ["reminder", "enable"], env=env)
    cli_runner.invoke(
        cli.goal,
        ["reminder", "config", "--break", "2", "--interval", "7"],
        env=env,
    )
    reminder.schedule_after_stop(Path(env["GOAL_GLIDE_DB_DIR"]) / "config.toml")
    reminder.schedule_after_stop(Path(env["GOAL_GLIDE_DB_DIR"]) / "config.toml")
    sched = reminder._sched
    assert sched is not None
    assert len(sched.jobs) == 2  # type: ignore[attr-defined]
    first_kwargs = sched.jobs[0][2]  # type: ignore[attr-defined]
    second_kwargs = sched.jobs[1][2]  # type: ignore[attr-defined]
    assert first_kwargs["run_date"] == FIXED_NOW + timedelta(minutes=2)
    assert second_kwargs["minutes"] == 7


def test_cancel_all_runs_on_new_session(reminder_runner, monkeypatch, tmp_path) -> None:
    cli_runner, _, env = reminder_runner
    sched = reminder._sched
    assert sched is not None
    # pre-populate fake scheduler with dummy jobs
    sched.add_job(lambda: None, "interval")  # type: ignore[attr-defined]
    sched.add_job(lambda: None, "interval")  # type: ignore[attr-defined]
    assert len(sched.jobs) == 2  # type: ignore[attr-defined]

    pomodoro.start_session(1, session_path=Path(env["GOAL_GLIDE_DB_DIR"]) / "session.json", config_path=Path(env["GOAL_GLIDE_DB_DIR"]) / "config.toml")

    assert sched.jobs == []  # type: ignore[attr-defined]


@given(
    break_min=st.integers(min_value=1, max_value=120),
    interval_min=st.integers(min_value=1, max_value=120),
)
@settings(max_examples=10, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_schedule_after_stop_randomized(
    reminder_runner, monkeypatch, break_min: int, interval_min: int
) -> None:
    """`schedule_after_stop` uses config values when scheduling."""
    _, _, env = reminder_runner
    monkeypatch.setattr(reminder, "reminders_enabled", lambda path: True)
    monkeypatch.setattr(reminder, "reminder_break", lambda path: break_min)
    monkeypatch.setattr(reminder, "reminder_interval", lambda path: interval_min)

    reminder.schedule_after_stop(Path(env["GOAL_GLIDE_DB_DIR"]) / "config.toml")

    sched = reminder._sched
    assert sched is not None
    assert len(sched.jobs) == 2  # type: ignore[attr-defined]
    first_kwargs = sched.jobs[0][2]  # type: ignore[attr-defined]
    second_kwargs = sched.jobs[1][2]  # type: ignore[attr-defined]
    assert first_kwargs["run_date"] == FIXED_NOW + timedelta(minutes=break_min)
    assert second_kwargs["minutes"] == interval_min
