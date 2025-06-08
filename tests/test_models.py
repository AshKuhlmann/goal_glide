from datetime import datetime

from goal_glide.models.goal import Goal, Priority
from goal_glide.models.session import PomodoroSession
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
