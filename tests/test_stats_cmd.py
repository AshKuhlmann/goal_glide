from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path

import pytest
from click.testing import CliRunner

from goal_glide import cli
from goal_glide.models.session import PomodoroSession
from goal_glide.models.storage import Storage


@pytest.fixture()
def runner(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> CliRunner:
    monkeypatch.setenv("GOAL_GLIDE_DB_DIR", str(tmp_path))
    return CliRunner()


def make_session(day: date, dur: int = 3600, goal_id: str = "g") -> PomodoroSession:
    return PomodoroSession(
        id=f"{goal_id}-{day}",
        goal_id=goal_id,
        start=datetime.combine(day, datetime.min.time()),
        duration_sec=dur,
    )


def test_stats_week_output_has_7_bars(
    runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    storage = Storage(tmp_path)
    start = date(2023, 6, 5)  # Monday
    for i in range(7):
        storage.add_session(make_session(start + timedelta(days=i)))

    class FakeDT(datetime):
        @classmethod
        def now(cls) -> datetime:
            return datetime(2023, 6, 11)

    monkeypatch.setattr(cli, "datetime", FakeDT)
    result = runner.invoke(
        cli.goal, ["stats"], env={"GOAL_GLIDE_DB_DIR": str(tmp_path)}
    )
    lines = [line for line in result.output.splitlines() if "[" in line]
    assert len(lines) == 7


def test_stats_month_output_has_4_bars(
    runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    storage = Storage(tmp_path)
    start = date(2023, 4, 3)  # first Monday of April
    for i in range(28):
        storage.add_session(make_session(start + timedelta(days=i)))

    class FakeDT(datetime):
        @classmethod
        def now(cls) -> datetime:
            return datetime(2023, 5, 31)

    monkeypatch.setattr(cli, "datetime", FakeDT)
    result = runner.invoke(
        cli.goal, ["stats", "--month"], env={"GOAL_GLIDE_DB_DIR": str(tmp_path)}
    )
    lines = [line for line in result.output.splitlines() if "[" in line]
    assert len(lines) == 4


def test_stats_goals_table_shows_top5(
    runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    storage = Storage(tmp_path)
    for i in range(6):
        storage.add_session(
            make_session(date(2023, 6, 1), dur=3600 * (i + 1), goal_id=f"g{i}")
        )

    class FakeDT(datetime):
        @classmethod
        def now(cls) -> datetime:
            return datetime(2023, 6, 2)

    monkeypatch.setattr(cli, "datetime", FakeDT)
    result = runner.invoke(
        cli.goal, ["stats", "--goals"], env={"GOAL_GLIDE_DB_DIR": str(tmp_path)}
    )
    assert result.exit_code == 0
    assert "Top Goals" in result.output
    rows = [line for line in result.output.splitlines() if "|" in line]
    assert len(rows) == 6  # header + 5 rows


def test_stats_empty_db_graceful(
    runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    class FakeDT(datetime):
        @classmethod
        def now(cls) -> datetime:
            return datetime(2023, 6, 1)

    monkeypatch.setattr(cli, "datetime", FakeDT)
    result = runner.invoke(
        cli.goal, ["stats"], env={"GOAL_GLIDE_DB_DIR": str(tmp_path)}
    )
    assert result.exit_code == 0
    assert "No session data" in result.output
