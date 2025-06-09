from __future__ import annotations

from typing import cast

import click
from rich.table import Table

from .common import AppContext, handle_exceptions, console
from ..models.storage import Storage
from ..utils.tag import validate_tag


@click.group("tag")
@click.pass_context
def tag_cmds(ctx: click.Context) -> None:
    """Tag management."""
    if ctx.obj is None:
        from ..config import load_config
        from .common import get_storage

        ctx.obj = cast(AppContext, {"storage": get_storage(), "config": load_config()})


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
