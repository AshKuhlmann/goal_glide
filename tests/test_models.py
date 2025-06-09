from datetime import datetime
from dataclasses import FrozenInstanceError
import pytest

from goal_glide.models.goal import Goal, Priority
from goal_glide.models.session import PomodoroSession
from goal_glide.models import session as session_module
from uuid import UUID
from goal_glide.models.thought import Thought
from goal_glide.models import thought as thought_module


def test_goal_defaults() -> None:
    g = Goal(id="1", title="t", created=datetime.utcnow())
    assert g.priority == Priority.medium
    assert g.archived is False
    assert g.tags == []
    assert g.parent_id is None
    assert g.deadline is None
    assert g.completed is False


def test_goal_nondefaults() -> None:
    g = Goal(
        id="1",
        title="t",
        created=datetime.utcnow(),
        priority=Priority.high,
        archived=True,
        tags=["a"],
        parent_id="p",
        deadline=datetime(2030, 1, 1),
        completed=True,
    )
    assert g.priority == Priority.high
    assert g.archived is True
    assert "a" in g.tags
    assert g.parent_id == "p"
    assert g.deadline == datetime(2030, 1, 1)
    assert g.completed is True


def test_session_new_generates_id() -> None:
    s = PomodoroSession.new("g", datetime.utcnow(), 60)
    assert s.goal_id == "g"
    assert s.duration_sec == 60
    assert isinstance(s.id, str) and len(s.id) > 0


def test_session_new_unique_ids(monkeypatch: pytest.MonkeyPatch) -> None:
    seq = iter(
        [
            UUID("11111111-1111-1111-1111-111111111111"),
            UUID("22222222-2222-2222-2222-222222222222"),
        ]
    )
    monkeypatch.setattr(session_module, "uuid4", lambda: next(seq))
    s1 = PomodoroSession.new("g", datetime.utcnow(), 60)
    s2 = PomodoroSession.new("g", datetime.utcnow(), 60)
    assert s1.id != s2.id


def test_session_new_without_goal_generates_id() -> None:
    s = PomodoroSession.new(None, datetime.utcnow(), 60)
    assert s.goal_id is None
    assert isinstance(s.id, str) and len(s.id) > 0


def test_thought_new_trims() -> None:
    t = Thought.new(" text ", None)
    assert t.text == "text"
    assert t.goal_id is None


def test_goal_tags_are_isolated() -> None:
    g1 = Goal(id="1", title="t1", created=datetime.utcnow())
    g2 = Goal(id="2", title="t2", created=datetime.utcnow())

    g1.tags.append("a")

    assert g1.tags == ["a"]
    assert g2.tags == []


def test_goal_is_frozen() -> None:
    g = Goal(id="1", title="t", created=datetime.utcnow())
    with pytest.raises(FrozenInstanceError):
        g.title = "new title"  # type: ignore[misc]


def test_goal_parent_relationship() -> None:
    parent = Goal(id="p", title="parent", created=datetime.utcnow())
    child = Goal(id="c", title="child", created=datetime.utcnow(), parent_id="p")
    assert child.parent_id == parent.id


def test_thought_new_timestamp_and_text(monkeypatch: pytest.MonkeyPatch) -> None:
    fixed = datetime(2024, 1, 1, 12, 0, 0)

    class FakeDT(datetime):
        @classmethod
        def now(cls) -> datetime:  # type: ignore[override]
            return fixed

    monkeypatch.setattr(thought_module, "datetime", FakeDT)

    t = Thought.new("  hello world  ", "g")
    assert t.timestamp == fixed
    assert t.text == "hello world"
    assert t.goal_id == "g"


def test_thought_new_unique_ids(monkeypatch: pytest.MonkeyPatch) -> None:
    seq = iter(
        [
            UUID("33333333-3333-3333-3333-333333333333"),
            UUID("44444444-4444-4444-4444-444444444444"),
        ]
    )
    monkeypatch.setattr(thought_module, "uuid4", lambda: next(seq))
    t1 = Thought.new("a", None)
    t2 = Thought.new("b", None)
    assert t1.id != t2.id
