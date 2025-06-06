from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

import pytest
from click.testing import CliRunner

from goal_glide import cli
from goal_glide.models.goal import Goal
from goal_glide.models.session import PomodoroSession
from goal_glide.models.storage import Storage
from goal_glide.services import report


@pytest.fixture()
def runner(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> CliRunner:
    monkeypatch.setenv("GOAL_GLIDE_DB_DIR", str(tmp_path))
    return CliRunner()


class FakeDate(date):
    @classmethod
    def today(cls) -> date:  # type: ignore[override]
        return date(2023, 6, 14)


def seed(storage: Storage) -> None:
    storage.add_goal(Goal(id="g", title="A", created=datetime.now()))
    start = datetime.combine(FakeDate.today(), datetime.min.time())
    storage.add_session(
        PomodoroSession(id="s", goal_id="g", start=start, duration_sec=600)
    )


def test_cli_creates_html(
    tmp_path: Path, runner: CliRunner, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(report, "date", FakeDate)
    storage = Storage(tmp_path)
    seed(storage)
    out = tmp_path / "rep.html"
    result = runner.invoke(
        cli.goal,
        ["report", "make", "--out", str(out)],
        env={"GOAL_GLIDE_DB_DIR": str(tmp_path)},
    )
    assert result.exit_code == 0
    assert out.exists()
    assert "Report saved to" in result.output


def test_cli_flag_collision(runner: CliRunner) -> None:
    result = runner.invoke(cli.goal, ["report", "make", "--week", "--month"])
    assert result.exit_code != 0
    assert "only one" in result.output
