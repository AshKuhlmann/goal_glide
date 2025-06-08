from __future__ import annotations

from datetime import datetime, timedelta
from rich.table import Table

from ..models.goal import Goal


def render_goals(goals: list[Goal]) -> Table:
    table = Table(title="Goals")
    table.add_column("ID")
    table.add_column("Title")
    table.add_column("Priority")
    table.add_column("Created")
    table.add_column("Deadline")
    table.add_column("Archived")
    table.add_column("Tags")
    for g in goals:
        deadline_text = ""
        if g.deadline:
            date_str = g.deadline.date().isoformat()
            now = datetime.utcnow()
            if g.deadline < now:
                deadline_text = f"[red]{date_str}[/]"
            elif g.deadline - now <= timedelta(days=3):
                deadline_text = f"[yellow]{date_str}[/]"
            else:
                deadline_text = date_str
        table.add_row(
            g.id,
            g.title,
            g.priority.value,
            g.created.isoformat(timespec="seconds"),
            deadline_text,
            "yes" if g.archived else "",
            ", ".join(g.tags),
        )
    return table
