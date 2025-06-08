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
    "average_focus_per_day",
    "most_productive_day",
    "longest_streak",
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

    goals = {g.id: g for g in storage.list_goals(include_archived=True)}
    for gid, total in list(acc.items()):
        g = goals.get(gid)
        while g and g.parent_id:
            acc[g.parent_id] += total
            g = goals.get(g.parent_id)

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


def average_focus_per_day(
    storage: Storage, start: date | None = None, end: date | None = None
) -> float:
    """Return the average focused seconds per day in the given date range."""
    sessions = _all_sessions(storage)
    if not sessions:
        return 0.0

    all_days = [s.start.date() for s in sessions]
    start = start or min(all_days)
    end = end or max(all_days)
    if start > end:
        return 0.0

    hist = date_histogram(storage, start, end)
    total = sum(hist.values())
    return total / len(hist) if hist else 0.0


def most_productive_day(
    storage: Storage, start: date | None = None, end: date | None = None
) -> str | None:
    """Return the weekday name with the highest focus time."""
    sessions = _all_sessions(storage)
    if not sessions:
        return None

    all_days = [s.start.date() for s in sessions]
    start = start or min(all_days)
    end = end or max(all_days)

    totals: dict[str, int] = defaultdict(int)
    for s in sessions:
        if not s.duration_sec:
            continue
        day = s.start.date()
        if start <= day <= end:
            totals[day.strftime("%A")] += s.duration_sec
    if not totals:
        return None
    return max(totals.items(), key=lambda t: t[1])[0]


def longest_streak(storage: Storage) -> int:
    """Return the longest streak of consecutive days with at least one session."""
    days = sorted({s.start.date() for s in _all_sessions(storage)})
    if not days:
        return 0

    longest = 1
    current = 1
    for prev, curr in zip(days, days[1:]):
        if (curr - prev).days == 1:
            current += 1
        else:
            longest = max(longest, current)
            current = 1
    longest = max(longest, current)
    return longest
