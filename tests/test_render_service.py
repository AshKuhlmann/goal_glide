from datetime import datetime, timedelta

from goal_glide.models.goal import Goal, Priority
from goal_glide.services.render import render_goals


def test_render_goals_row_count() -> None:
    goals = [
        Goal(
            id="1",
            title="A",
            created=datetime.utcnow(),
            priority=Priority.low,
            completed=True,
        ),
        Goal(
            id="2",
            title="B",
            created=datetime.utcnow(),
            archived=True,
            deadline=datetime.utcnow(),
        ),
    ]
    table = render_goals(goals)
    assert len(table.rows) == len(goals)
    assert table.columns[0].header == "ID"
    headers = [col.header for col in table.columns]
    assert "Deadline" in headers and "Completed" in headers


def test_render_goals_deadline_coloring() -> None:
    now = datetime.utcnow()
    past = now - timedelta(days=1)
    near = now + timedelta(days=2)
    future = now + timedelta(days=5)
    goals = [
        Goal(id="1", title="past", created=now, deadline=past),
        Goal(id="2", title="near", created=now, deadline=near),
        Goal(id="3", title="future", created=now, deadline=future),
    ]
    table = render_goals(goals)
    deadlines = table.columns[4]._cells
    assert deadlines[0] == f"[red]{past.date().isoformat()}[/]"
    assert deadlines[1] == f"[yellow]{near.date().isoformat()}[/]"
    assert deadlines[2] == future.date().isoformat()
