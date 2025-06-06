from __future__ import annotations

from rich.table import Table

from ..models.goal import Goal


def render_goals(goals: list[Goal]) -> Table:
    table = Table(title="Goals")
    table.add_column("ID")
    table.add_column("Title")
    table.add_column("Priority")
    table.add_column("Created")
    table.add_column("Archived")
    table.add_column("Tags")
    for g in goals:
        table.add_row(
            g.id,
            g.title,
            g.priority.value,
            g.created.isoformat(timespec="seconds"),
            "yes" if g.archived else "",
            ", ".join(g.tags),
        )
    return table
