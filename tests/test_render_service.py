from datetime import datetime

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
