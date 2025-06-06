from __future__ import annotations

import uuid
from pathlib import Path
from datetime import datetime
import os

import click
from rich.console import Console

from .models.goal import Goal, Priority
from .models.storage import Storage
from .exceptions import (
    GoalAlreadyArchivedError,
    GoalNotArchivedError,
    GoalNotFoundError,
)
from .services.render import render_goals


def get_storage() -> Storage:
    db_dir = os.environ.get("GOAL_GLIDE_DB_DIR")
    return Storage(Path(db_dir) if db_dir else None)


console = Console()


@click.group()
def goal() -> None:
    """Goal management CLI."""


@goal.command("add")
@click.argument("title")
@click.option(
    "-p",
    "--priority",
    type=click.Choice([e.value for e in Priority]),
    default=Priority.medium.value,
    show_default=True,
    help="Goal priority (low, medium, high)",
)
def add_goal(title: str, priority: str) -> None:
    """Add a new goal."""
    title = title.strip()
    if not title:
        console.print("[red]Title cannot be empty.[/red]")
        raise SystemExit(1)

    storage = get_storage()
    if storage.find_by_title(title):
        console.print("[yellow]Warning: goal with this title already exists.[/yellow]")

    prio = Priority(priority)
    g = Goal(
        id=str(uuid.uuid4()),
        title=title,
        created=datetime.utcnow(),
        priority=prio,
    )
    storage.add_goal(g)
    console.print(f":check_mark: Added goal {g.title} ({g.id})")


@goal.command("remove")
@click.argument("goal_id")
def remove_goal_cmd(goal_id: str) -> None:
    """Permanently remove a goal."""
    storage = get_storage()
    if click.confirm(f"Remove goal {goal_id}?"):
        try:
            storage.remove_goal(goal_id)
            console.print(f"[green]Removed[/green] {goal_id}")
        except GoalNotFoundError as exc:
            console.print(f"[red]{exc}[/red]")
            raise SystemExit(1)


@goal.command("archive")
@click.argument("goal_id")
def archive_goal_cmd(goal_id: str) -> None:
    """Hide a goal from normal listings."""
    storage = get_storage()
    try:
        storage.archive_goal(goal_id)
        console.print(f":package: Goal {goal_id} archived")
    except (GoalNotFoundError, GoalAlreadyArchivedError) as exc:
        console.print(f"[red]{exc}[/red]")
        raise SystemExit(1)


@goal.command("restore")
@click.argument("goal_id")
def restore_goal_cmd(goal_id: str) -> None:
    """Bring a goal back into the active list."""
    storage = get_storage()
    try:
        storage.restore_goal(goal_id)
        console.print(f":package: Goal {goal_id} restored")
    except (GoalNotFoundError, GoalNotArchivedError) as exc:
        console.print(f"[red]{exc}[/red]")
        raise SystemExit(1)


@goal.command("list")
@click.option("--archived", is_flag=True, help="Show only archived goals")
@click.option(
    "--all", "show_all", is_flag=True, help="Show both active and archived goals"
)
@click.option(
    "--priority",
    type=click.Choice([e.value for e in Priority]),
    help="Filter by priority",
)
def list_goals(archived: bool, show_all: bool, priority: str | None) -> None:
    """List goals with optional filtering."""
    storage = get_storage()
    goals = storage.list_goals(
        include_archived=show_all,
        only_archived=archived,
        priority=Priority(priority) if priority else None,
    )

    prio_order = {Priority.high: 0, Priority.medium: 1, Priority.low: 2}
    goals.sort(key=lambda g: (g.archived, prio_order[g.priority], g.created))

    table = render_goals(goals)
    console.print(table)


if __name__ == "__main__":
    goal()
