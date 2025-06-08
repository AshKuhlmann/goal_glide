from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from typing import Dict

from ..models.session import PomodoroSession
from ..models.storage import Storage

__all__ = [
    "total_time_by_goal",
    "weekly_histogram",
    "current_streak",
    "date_histogram",
]


def _all_sessions(storage: Storage) -> list[PomodoroSession]:
    return storage.list_sessions()


def total_time_by_goal(
    storage: Storage, start: date | None = None, end: date | None = None
) -> Dict[str, int]:
    acc: Dict[str, int] = defaultdict(int)
    for s in _all_sessions(storage):
        if s.duration_sec and s.goal_id is not None:
            day = s.start.date()
            if start and day < start:
                continue
            if end and day > end:
                continue
            acc[s.goal_id] += s.duration_sec
    return dict(acc)


def date_histogram(storage: Storage, start: date, end: date) -> Dict[date, int]:
    buckets: Dict[date, int] = {
        start + timedelta(days=i): 0 for i in range((end - start).days + 1)
    }
    for s in _all_sessions(storage):
        if not s.duration_sec:
            continue
        bucket_day = s.start.date()
        if start <= bucket_day <= end:
            buckets[bucket_day] += s.duration_sec
    return buckets


def weekly_histogram(storage: Storage, start: date) -> Dict[date, int]:
    return date_histogram(storage, start, start + timedelta(days=6))


def current_streak(storage: Storage, today: date | None = None) -> int:
    today = today or date.today()
    days = {s.start.date() for s in _all_sessions(storage)}
    streak = 0
    cursor = today
    while cursor in days:
        streak += 1
        cursor -= timedelta(days=1)
    return streak
