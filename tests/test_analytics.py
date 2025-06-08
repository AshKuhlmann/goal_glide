from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path
import tempfile

from hypothesis import given, settings, strategies as st
import pytest

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


def test_empty_storage(tmp_path: Path) -> None:
    storage = Storage(tmp_path)
    start = date(2023, 1, 2)
    assert analytics.total_time_by_goal(storage) == {}
    assert analytics.weekly_histogram(storage, start) == {
        start + timedelta(days=i): 0 for i in range(7)
    }
    assert analytics.current_streak(storage, start) == 0


def test_total_time_by_goal_ignores_invalid(tmp_path: Path) -> None:
    storage = Storage(tmp_path)
    sessions = [
        PomodoroSession(
            id="1",
            goal_id="g",
            start=datetime(2023, 1, 1, 8),
            duration_sec=0,
        ),
        PomodoroSession(
            id="2",
            goal_id=None,
            start=datetime(2023, 1, 1, 9),
            duration_sec=60,
        ),
        PomodoroSession(
            id="3",
            goal_id="g",
            start=datetime(2023, 1, 1, 10),
            duration_sec=None,  # type: ignore[arg-type]
        ),
        PomodoroSession(
            id="4",
            goal_id="g",
            start=datetime(2023, 1, 1, 11),
            duration_sec=30,
        ),
    ]
    seed(storage, sessions)
    totals = analytics.total_time_by_goal(storage)
    # only the last session should count
    assert totals == {"g": 30}


def test_weekly_histogram_varied(tmp_path: Path) -> None:
    week_start = date(2023, 5, 15)  # Monday
    storage = Storage(tmp_path)
    sessions = [
        make_session("g", datetime(2023, 5, 15, 8), 10),
        make_session("g", datetime(2023, 5, 15, 9), 20),
        make_session("g", datetime(2023, 5, 17, 12), 15),
        make_session("g", datetime(2023, 5, 22, 8), 50),  # outside window
        make_session("g", datetime(2023, 5, 14, 23), 40),  # outside window
        make_session("g", datetime(2023, 5, 18, 8), 0),  # zero duration
    ]
    seed(storage, sessions)
    hist = analytics.weekly_histogram(storage, week_start)
    assert hist[week_start] == 30
    assert hist[week_start + timedelta(days=2)] == 15
    assert all(
        hist[d] == 0
        for d in hist
        if d not in {week_start, week_start + timedelta(days=2)}
    )


def test_current_streak_with_gaps_and_future(tmp_path: Path) -> None:
    today = date(2023, 6, 5)
    storage = Storage(tmp_path)
    sessions = [
        make_session("g", datetime(2023, 6, 5, 8), 25),
        make_session("g", datetime(2023, 6, 5, 9), 30),  # multiple same day
        make_session("g", datetime(2023, 6, 4, 8), 20),
        make_session("g", datetime(2023, 6, 2, 8), 20),  # gap on 6/3 breaks streak
        # future session should not matter
        make_session("g", datetime(2023, 6, 7, 8), 20),
    ]
    seed(storage, sessions)
    assert analytics.current_streak(storage, today) == 2


def test_average_focus_per_day_simple(tmp_path: Path) -> None:
    storage = Storage(tmp_path)
    sessions = [
        make_session("g", datetime(2023, 6, 1, 8), 60),
        make_session("g", datetime(2023, 6, 2, 8), 120),
    ]
    seed(storage, sessions)
    avg = analytics.average_focus_per_day(storage)
    assert avg == 90


def test_most_productive_day_simple(tmp_path: Path) -> None:
    storage = Storage(tmp_path)
    sessions = [
        make_session("g", datetime(2023, 6, 1, 8), 60),  # Thu
        make_session("g", datetime(2023, 6, 2, 8), 120),  # Fri
        make_session("g", datetime(2023, 6, 9, 8), 180),  # Fri
    ]
    seed(storage, sessions)
    assert analytics.most_productive_day(storage) == "Friday"


def test_longest_streak_simple(tmp_path: Path) -> None:
    storage = Storage(tmp_path)
    sessions = [
        make_session("g", datetime(2023, 6, 1, 8), 30),
        make_session("g", datetime(2023, 6, 2, 8), 30),
        make_session("g", datetime(2023, 6, 4, 8), 30),
        make_session("g", datetime(2023, 6, 5, 8), 30),
        make_session("g", datetime(2023, 6, 6, 8), 30),
    ]
    seed(storage, sessions)
    assert analytics.longest_streak(storage) == 3


# Property-based tests -----------------------------------------------------


def _ref_total_time(sessions: list[PomodoroSession]) -> dict[str, int]:
    acc: dict[str, int] = {}
    for s in sessions:
        if s.duration_sec and s.goal_id is not None:
            acc[s.goal_id] = acc.get(s.goal_id, 0) + s.duration_sec
    return acc


def _ref_histogram(sessions: list[PomodoroSession], start: date) -> dict[date, int]:
    buckets = {start + timedelta(days=i): 0 for i in range(7)}
    for s in sessions:
        if not s.duration_sec:
            continue
        day = s.start.date()
        if start <= day <= start + timedelta(days=6):
            buckets[day] += s.duration_sec
    return buckets


def _ref_streak(sessions: list[PomodoroSession], today: date) -> int:
    days = {s.start.date() for s in sessions}
    streak = 0
    cursor = today
    while cursor in days:
        streak += 1
        cursor -= timedelta(days=1)
    return streak


def _ref_average_focus(sessions: list[PomodoroSession]) -> float:
    if not sessions:
        return 0.0
    days = [s.start.date() for s in sessions]
    start = min(days)
    end = max(days)
    buckets = {start + timedelta(days=i): 0 for i in range((end - start).days + 1)}
    for s in sessions:
        if not s.duration_sec:
            continue
        buckets[s.start.date()] += s.duration_sec
    return sum(buckets.values()) / len(buckets)


def _ref_most_productive_day(sessions: list[PomodoroSession]) -> str | None:
    totals: dict[str, int] = {}
    for s in sessions:
        if not s.duration_sec:
            continue
        day = s.start.strftime("%A")
        totals[day] = totals.get(day, 0) + s.duration_sec
    if not totals:
        return None
    return max(totals.items(), key=lambda t: t[1])[0]


def _ref_longest_streak(sessions: list[PomodoroSession]) -> int:
    days = sorted({s.start.date() for s in sessions})
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
    return max(longest, current)


@given(
    st.lists(
        st.builds(
            PomodoroSession,
            id=st.text(min_size=1, max_size=3),
            goal_id=st.one_of(st.none(), st.text(min_size=1, max_size=2)),
            start=st.datetimes(
                min_value=datetime(2023, 1, 1),
                max_value=datetime(2023, 12, 31),
            ),
            duration_sec=st.one_of(
                st.integers(min_value=0, max_value=3600),
                st.just(None),
            ),
        )
    )
)
@settings(max_examples=25)
def test_property_total_time(sessions: list[PomodoroSession]) -> None:
    with tempfile.TemporaryDirectory() as d:
        storage = Storage(Path(d))
        seed(storage, sessions)
        assert analytics.total_time_by_goal(storage) == _ref_total_time(sessions)


@given(
    st.lists(
        st.builds(
            PomodoroSession,
            id=st.text(min_size=1, max_size=3),
            goal_id=st.text(min_size=1, max_size=2),
            start=st.datetimes(
                min_value=datetime(2023, 1, 1),
                max_value=datetime(2023, 12, 31),
            ),
            duration_sec=st.one_of(
                st.integers(min_value=0, max_value=3600),
                st.just(None),
            ),
        )
    ),
    st.dates(min_value=date(2023, 1, 1), max_value=date(2023, 12, 25)),
)
@settings(max_examples=25)
def test_property_weekly_histogram(
    sessions: list[PomodoroSession], start: date
) -> None:
    with tempfile.TemporaryDirectory() as d:
        storage = Storage(Path(d))
        seed(storage, sessions)
        assert analytics.weekly_histogram(storage, start) == _ref_histogram(
            sessions, start
        )


@given(
    st.lists(
        st.builds(
            PomodoroSession,
            id=st.text(min_size=1, max_size=3),
            goal_id=st.text(min_size=1, max_size=2),
            start=st.datetimes(
                min_value=datetime(2023, 1, 1),
                max_value=datetime(2023, 12, 31),
            ),
            duration_sec=st.one_of(
                st.integers(min_value=0, max_value=3600),
                st.just(None),
            ),
        )
    ),
    st.dates(min_value=date(2023, 1, 1), max_value=date(2023, 12, 31)),
)
@settings(max_examples=25)
def test_property_current_streak(sessions: list[PomodoroSession], today: date) -> None:
    with tempfile.TemporaryDirectory() as d:
        storage = Storage(Path(d))
        seed(storage, sessions)
        assert analytics.current_streak(storage, today) == _ref_streak(sessions, today)


@given(
    st.lists(
        st.builds(
            PomodoroSession,
            id=st.text(min_size=1, max_size=3),
            goal_id=st.text(min_size=1, max_size=2),
            start=st.datetimes(
                min_value=datetime(2023, 1, 1),
                max_value=datetime(2023, 12, 31),
            ),
            duration_sec=st.one_of(
                st.integers(min_value=0, max_value=3600),
                st.just(None),
            ),
        )
    )
)
@settings(max_examples=25)
def test_property_average_focus_per_day(sessions: list[PomodoroSession]) -> None:
    with tempfile.TemporaryDirectory() as d:
        storage = Storage(Path(d))
        seed(storage, sessions)
        assert analytics.average_focus_per_day(storage) == pytest.approx(
            _ref_average_focus(sessions)
        )


@given(
    st.lists(
        st.builds(
            PomodoroSession,
            id=st.text(min_size=1, max_size=3),
            goal_id=st.text(min_size=1, max_size=2),
            start=st.datetimes(
                min_value=datetime(2023, 1, 1),
                max_value=datetime(2023, 12, 31),
            ),
            duration_sec=st.one_of(
                st.integers(min_value=0, max_value=3600),
                st.just(None),
            ),
        )
    )
)
@settings(max_examples=25)
def test_property_most_productive_day(sessions: list[PomodoroSession]) -> None:
    with tempfile.TemporaryDirectory() as d:
        storage = Storage(Path(d))
        seed(storage, sessions)
        assert analytics.most_productive_day(storage) == _ref_most_productive_day(
            sessions
        )


@given(
    st.lists(
        st.builds(
            PomodoroSession,
            id=st.text(min_size=1, max_size=3),
            goal_id=st.text(min_size=1, max_size=2),
            start=st.datetimes(
                min_value=datetime(2023, 1, 1),
                max_value=datetime(2023, 12, 31),
            ),
            duration_sec=st.one_of(
                st.integers(min_value=0, max_value=3600),
                st.just(None),
            ),
        )
    )
)
@settings(max_examples=25)
def test_property_longest_streak(sessions: list[PomodoroSession]) -> None:
    with tempfile.TemporaryDirectory() as d:
        storage = Storage(Path(d))
        seed(storage, sessions)
        assert analytics.longest_streak(storage) == _ref_longest_streak(sessions)
