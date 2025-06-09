from __future__ import annotations

import uuid
from datetime import datetime
from typing import cast
import click
from rich.tree import Tree
from rich.table import Table

from .common import AppContext, handle_exceptions, console
from ..models.goal import Goal, Priority
from ..models.storage import Storage
from ..services.render import render_goals
from ..utils.tag import validate_tag


@click.group("goal")
def goal_cmds() -> None:
    """Goal management commands (add, remove, list, etc.)."""
    pass


@goal_cmds.command("add")
@click.argument("title")
@click.option(
    "-p",
    "--priority",
    type=click.Choice([e.value for e in Priority]),
    default=Priority.medium.value,
    show_default=True,
    help="Goal priority (low, medium, high)",
)
@click.option(
    "--deadline",
    type=click.DateTime(formats=["%Y-%m-%d"]),
    help="Deadline in YYYY-MM-DD format",
)
@click.option("--parent", "parent_id", help="Parent goal ID")
@click.pass_context
def add_goal(
    ctx: click.Context,
    title: str,
    priority: str,
    deadline: datetime | None,
    parent_id: str | None,
) -> None:
    """Adds a new goal to the database."""
    title = title.strip()
    if not title:
        console.print("[red]Title cannot be empty.[/red]")
        raise SystemExit(1)

    obj = cast(AppContext, ctx.obj)
    storage: Storage = obj["storage"]
    if storage.find_by_title(title):
        console.print("[yellow]Warning: goal with this title already exists.[/yellow]")

    if parent_id is not None:
        storage.get_goal(parent_id)  # validate exists

    prio = Priority(priority)
    g = Goal(
        id=str(uuid.uuid4()),
        title=title,
        created=datetime.utcnow(),
        priority=prio,
        deadline=deadline,
        parent_id=parent_id,
    )
    storage.add_goal(g)
    console.print(f":check_mark: Added goal {g.title} ({g.id})")


@goal_cmds.command("remove")
@click.argument("goal_id")
@handle_exceptions
@click.pass_context
def remove_goal_cmd(ctx: click.Context, goal_id: str) -> None:
    """Permanently remove a goal."""
    obj = cast(AppContext, ctx.obj)
    storage: Storage = obj["storage"]
    if click.confirm(f"Remove goal {goal_id}?"):
        storage.remove_goal(goal_id)
        console.print(f"[green]Removed[/green] {goal_id}")


@goal_cmds.command("archive")
@click.argument("goal_id")
@handle_exceptions
@click.pass_context
def archive_goal_cmd(ctx: click.Context, goal_id: str) -> None:
    """Hide a goal from normal listings."""
    obj = cast(AppContext, ctx.obj)
    storage: Storage = obj["storage"]
    storage.archive_goal(goal_id)
    console.print(f":package: Goal {goal_id} archived")


@goal_cmds.command("restore")
@click.argument("goal_id")
@handle_exceptions
@click.pass_context
def restore_goal_cmd(ctx: click.Context, goal_id: str) -> None:
    """Bring a goal back into the active list."""
    obj = cast(AppContext, ctx.obj)
    storage: Storage = obj["storage"]
    storage.restore_goal(goal_id)
    console.print(f":package: Goal {goal_id} restored")


@goal_cmds.command("complete")
@click.argument("goal_id")
@handle_exceptions
@click.pass_context
def complete_goal_cmd(ctx: click.Context, goal_id: str) -> None:
    """Mark a goal as completed."""
    obj = cast(AppContext, ctx.obj)
    storage: Storage = obj["storage"]
    storage.complete_goal(goal_id)
    console.print(f"[green]Goal {goal_id} completed[/green]")


@goal_cmds.command("reopen")
@click.argument("goal_id")
@handle_exceptions
@click.pass_context
def reopen_goal_cmd(ctx: click.Context, goal_id: str) -> None:
    """Mark a completed goal as not done."""
    obj = cast(AppContext, ctx.obj)
    storage: Storage = obj["storage"]
    storage.reopen_goal(goal_id)
    console.print(f"Goal {goal_id} reopened")


@goal_cmds.command("update")
@click.argument("goal_id")
@click.option("--title", help="New goal title")
@click.option(
    "--priority",
    type=click.Choice([e.value for e in Priority]),
    help="Goal priority (low, medium, high)",
)
@click.option(
    "--deadline",
    type=click.DateTime(formats=["%Y-%m-%d"]),
    help="Deadline in YYYY-MM-DD format",
)
@handle_exceptions
@click.pass_context
def update_goal_cmd(
    ctx: click.Context,
    goal_id: str,
    title: str | None,
    priority: str | None,
    deadline: datetime | None,
) -> None:
    obj = cast(AppContext, ctx.obj)
    storage: Storage = obj["storage"]
    goal = storage.get_goal(goal_id)

    new_title = goal.title
    if title is not None:
        title = title.strip()
        if not title:
            console.print("[red]Title cannot be empty.[/red]")
            raise SystemExit(1)
        new_title = title

    new_priority = goal.priority if priority is None else Priority(priority)
    new_deadline = goal.deadline if deadline is None else deadline

    updated = Goal(
        id=goal.id,
        title=new_title,
        created=goal.created,
        priority=new_priority,
        archived=goal.archived,
        tags=goal.tags,
        parent_id=goal.parent_id,
        deadline=new_deadline,
    )
    storage.update_goal(updated)
    console.print(f":pencil: Updated goal {updated.id}")


@goal_cmds.group("tag")
def tag_cmds() -> None:
    """Tag management."""
    pass


@tag_cmds.command("add")
@click.argument("goal_id")
@click.argument("tags", nargs=-1, required=True)
@handle_exceptions
@click.pass_context
def tag_add(ctx: click.Context, goal_id: str, tags: tuple[str, ...]) -> None:
    """Add one or more tags to a goal."""
    obj = cast(AppContext, ctx.obj)
    storage: Storage = obj["storage"]
    validated = [validate_tag(t) for t in tags]
    goal = storage.add_tags(goal_id, validated)
    console.print(f"Tags for {goal.id}: {', '.join(goal.tags)}")


@tag_cmds.command("rm")
@click.argument("goal_id")
@click.argument("tag")
@handle_exceptions
@click.pass_context
def tag_rm(ctx: click.Context, goal_id: str, tag: str) -> None:
    """Remove a tag from a goal."""
    obj = cast(AppContext, ctx.obj)
    storage: Storage = obj["storage"]
    validated = validate_tag(tag)
    before = storage.get_goal(goal_id)
    updated = storage.remove_tag(goal_id, validated)
    if validated not in before.tags:
        console.print(f"[yellow]Tag '{validated}' not present[/yellow]")
    console.print(f"Tags for {updated.id}: {', '.join(updated.tags)}")


@tag_cmds.command("list")
@click.pass_context
def tag_list(ctx: click.Context) -> None:
    """List all tags with goal counts."""
    obj = cast(AppContext, ctx.obj)
    storage: Storage = obj["storage"]
    tags = storage.list_all_tags()
    if not tags:
        console.print("No tags.")
        return
    table = Table(title="Tags")
    table.add_column("Tag")
    table.add_column("Goals")
    for name, count in sorted(tags.items()):
        table.add_row(name, str(count))
    console.print(table)


@goal_cmds.command("list")
@click.option("--archived", is_flag=True, help="Show only archived goals")
@click.option(
    "--all",
    "show_all",
    is_flag=True,
    help="Show both active and archived goals",
)
@click.option(
    "--priority",
    type=click.Choice([e.value for e in Priority]),
    help="Filter by priority",
)
@click.option("--tag", "tags", multiple=True, help="Filter goals by tag (AND logic)")
@click.option("--due-soon", is_flag=True, help="Goals due in the next 3 days")
@click.option("--overdue", is_flag=True, help="Goals past their deadline")
@click.pass_context
def list_goals(
    ctx: click.Context,
    archived: bool,
    show_all: bool,
    priority: str | None,
    tags: tuple[str, ...],
    due_soon: bool,
    overdue: bool,
) -> None:
    obj = cast(AppContext, ctx.obj)
    storage: Storage = obj["storage"]
    goals = storage.list_goals(
        include_archived=show_all,
        only_archived=archived,
        priority=Priority(priority) if priority else None,
        tags=list(tags) if tags else None,
        due_soon=due_soon,
        overdue=overdue,
    )

    prio_order = {Priority.high: 0, Priority.medium: 1, Priority.low: 2}
    goals.sort(key=lambda g: (g.archived, prio_order[g.priority], g.created))

    table = render_goals(goals)
    console.print(table)


@goal_cmds.command("tree")
@click.pass_context
def goal_tree(ctx: click.Context) -> None:
    """Display goals in a tree view."""
    obj = cast(AppContext, ctx.obj)
    storage: Storage = obj["storage"]
    goals = storage.list_goals()

    children: dict[str, list[Goal]] = {}
    roots: list[Goal] = []
    for g in goals:
        if g.parent_id:
            children.setdefault(g.parent_id, []).append(g)
        else:
            roots.append(g)
    for lst in children.values():
        lst.sort(key=lambda g: g.created)
    roots.sort(key=lambda g: g.created)

    tree = Tree("Goals")

    def add_nodes(node: Tree, goal: Goal) -> None:
        title = f"[green]{goal.title}[/]" if goal.completed else goal.title
        branch = node.add(f"{title} ({goal.id})")
        for child in children.get(goal.id, []):
            add_nodes(branch, child)

    for g in roots:
        add_nodes(tree, g)

    console.print(tree)
