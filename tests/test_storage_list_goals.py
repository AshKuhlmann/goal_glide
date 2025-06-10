from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
import tempfile

from hypothesis import given, settings, strategies as st

from goal_glide.models.goal import Goal, Priority
from goal_glide.models.storage import Storage


def _goal_strategy(now: datetime) -> st.SearchStrategy[Goal]:
    return st.builds(
        Goal,
        id=st.text(min_size=1, max_size=5),
        title=st.text(min_size=1, max_size=5),
        created=st.datetimes(
            min_value=now - timedelta(days=5),
            max_value=now + timedelta(days=5),
            timezones=st.none(),
        ),
        priority=st.sampled_from(list(Priority)),
        archived=st.booleans(),
        tags=st.lists(st.text(min_size=1, max_size=3), unique=True, max_size=3),
        parent_id=st.none(),
        deadline=st.one_of(
            st.none(),
            st.datetimes(
                min_value=now - timedelta(days=5),
                max_value=now + timedelta(days=5),
                timezones=st.none(),
            ),
        ),
        completed=st.booleans(),
    )


def _ref_filter(
    goals: list[Goal],
    *,
    include_archived: bool,
    only_archived: bool,
    priority: Priority | None,
    tags: list[str] | None,
    due_soon: bool,
    overdue: bool,
    now: datetime,
) -> list[Goal]:
    result = goals
    if only_archived:
        result = [g for g in result if g.archived]
    elif not include_archived:
        result = [g for g in result if not g.archived]
    if priority is not None:
        result = [g for g in result if g.priority == priority]
    if tags:
        result = [g for g in result if set(tags).issubset(set(g.tags))]
    if due_soon or overdue:
        window = timedelta(days=3)
        filtered: list[Goal] = []
        for g in result:
            if g.deadline is None:
                continue
            if overdue and g.deadline < now:
                filtered.append(g)
            elif due_soon and now <= g.deadline <= now + window:
                filtered.append(g)
        result = filtered
    return result


def _filters_strategy() -> st.SearchStrategy[dict[str, object]]:
    return st.fixed_dictionaries(
        {
            "include_archived": st.booleans(),
            "only_archived": st.booleans(),
            "priority": st.one_of(st.none(), st.sampled_from(list(Priority))),
            "tags": st.one_of(
                st.none(),
                st.lists(st.text(min_size=1, max_size=3), unique=True, max_size=2),
            ),
            "due_soon": st.booleans(),
            "overdue": st.booleans(),
        }
    )


@given(
    goals=st.lists(
        st.deferred(lambda: _goal_strategy(datetime.utcnow())),
        unique_by=lambda g: g.id,
        min_size=0,
        max_size=10,
    ),
    filters=_filters_strategy(),
)
@settings(max_examples=25, deadline=None)
def test_property_list_goals(goals: list[Goal], filters: dict[str, object]) -> None:
    with tempfile.TemporaryDirectory() as d:
        storage = Storage(Path(d) / "db.json")
        for g in goals:
            storage.add_goal(g)

    fixed_now = datetime.utcnow()
    import goal_glide.models.storage as storage_mod
    orig_dt = storage_mod.datetime

    class FixedDateTime(datetime):
        @classmethod
        def utcnow(cls) -> datetime:
            return fixed_now

    storage_mod.datetime = FixedDateTime
    try:
        result_ids = {g.id for g in storage.list_goals(**filters)}
    finally:
        storage_mod.datetime = orig_dt

    expected_ids = {g.id for g in _ref_filter(goals, now=fixed_now, **filters)}
    assert result_ids == expected_ids
