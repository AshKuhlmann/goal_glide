from datetime import datetime
from dataclasses import FrozenInstanceError
import pytest

from goal_glide.models.goal import Goal, Priority
from goal_glide.models.session import PomodoroSession
from goal_glide.models import session as session_module
from uuid import UUID
from goal_glide.models.thought import Thought


def test_goal_defaults() -> None:
    g = Goal(id="1", title="t", created=datetime.utcnow())
    assert g.priority == Priority.medium
    assert g.archived is False
    assert g.tags == []


def test_goal_nondefaults() -> None:
    g = Goal(
        id="1",
        title="t",
        created=datetime.utcnow(),
        priority=Priority.high,
        archived=True,
        tags=["a"],
    )
    assert g.priority == Priority.high
    assert g.archived is True
    assert "a" in g.tags


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
