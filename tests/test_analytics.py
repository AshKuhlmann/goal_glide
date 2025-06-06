from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path

from goal_glide.models.session import PomodoroSession
from goal_glide.models.storage import Storage
from goal_glide.services import analytics


def make_session(goal_id: str, start_dt: datetime, dur_sec: int) -> PomodoroSession:
    return PomodoroSession(
        id="x", goal_id=goal_id, start=start_dt, duration_sec=dur_sec
    )


def seed(storage: Storage, sessions: list[PomodoroSession]) -> None:
    for s in sessions:
        storage.add_session(s)


def test_total_time_by_goal_simple(tmp_path: Path) -> None:
    storage = Storage(tmp_path)
    seed(
        storage,
        [
            make_session("g1", datetime.now(), 60),
            make_session("g1", datetime.now(), 30),
            make_session("g2", datetime.now(), 20),
        ],
    )
    totals = analytics.total_time_by_goal(storage)
    assert totals["g1"] == 90
    assert totals["g2"] == 20


def test_weekly_histogram_exact_bounds(tmp_path: Path) -> None:
    today = date(2023, 5, 15)  # Monday
    storage = Storage(tmp_path)
    seed(
        storage,
        [
            make_session("g", datetime(2023, 5, 15, 8), 60),
            make_session("g", datetime(2023, 5, 21, 9), 30),
        ],
    )
    hist = analytics.weekly_histogram(storage, today)
    assert hist[today] == 60
    assert hist[today + timedelta(days=6)] == 30


def test_current_streak_zero(tmp_path: Path) -> None:
    storage = Storage(tmp_path)
    assert analytics.current_streak(storage, date(2023, 1, 1)) == 0


def test_current_streak_nonzero(tmp_path: Path) -> None:
    storage = Storage(tmp_path)
    seed(
        storage,
        [
            make_session("g", datetime(2023, 6, 1, 8), 10),
            make_session("g", datetime(2023, 6, 2, 8), 10),
        ],
    )
    assert analytics.current_streak(storage, date(2023, 6, 2)) == 2
