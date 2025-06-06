from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

from goal_glide import cli
from goal_glide import config as cfg
from goal_glide.services import notify, reminder


class FakeScheduler:
    def __init__(self) -> None:
        self.jobs: list[tuple[callable, tuple, dict]] = []

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
    cfg._CONFIG_PATH = tmp_path / ".goal_glide" / "config.toml"
    cfg._CONFIG_CACHE = None
    monkeypatch.setattr(reminder, "_sched", FakeScheduler())
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
    assert len(sched.jobs) == 2
    for func, args, _ in sched.jobs:
        func(*args)
    assert any("Pomodoro" in m or "Break" in m for m in messages)
