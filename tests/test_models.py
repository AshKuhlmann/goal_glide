from datetime import datetime

from goal_glide.models.goal import Goal, Priority
from goal_glide.models.session import PomodoroSession
from goal_glide.models.thought import Thought


def test_goal_defaults() -> None:
    g = Goal(id="1", title="t", created=datetime.utcnow())
    assert g.priority == Priority.medium
    assert g.archived is False
    assert g.tags == []


def test_session_new_generates_id() -> None:
    s = PomodoroSession.new("g", datetime.utcnow(), 60)
    assert s.goal_id == "g"
    assert s.duration_sec == 60
    assert isinstance(s.id, str) and len(s.id) > 0


def test_thought_new_trims() -> None:
    t = Thought.new(" text ", None)
    assert t.text == "text"
    assert t.goal_id is None
