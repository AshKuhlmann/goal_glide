from __future__ import annotations

from typing import cast
from datetime import datetime

import click
from rich.table import Table
from tinydb import Query

from .common import AppContext, handle_exceptions, console
from ..models.storage import Storage
from ..models.thought import Thought
from ..utils.timefmt import natural_delta


@click.group("thought", help="Capture and review quick reflections.")
@click.pass_context
def thought_cmds(ctx: click.Context) -> None:
    if ctx.obj is None:
        from ..config import load_config
        from .common import get_storage

        ctx.obj = cast(AppContext, {"storage": get_storage(), "config": load_config()})


@thought_cmds.command("jot")
@click.argument("message", required=False)
@click.option("-g", "--goal", "goal_id", help="Attach note to a goal ID")
@handle_exceptions
@click.pass_context
def jot_thought(ctx: click.Context, message: str | None, goal_id: str | None) -> None:
    """Record a short thought or reflection."""
    obj = cast(AppContext, ctx.obj)
    storage: Storage = obj["storage"]

    if message is None:
        message = click.edit()
        if message is not None:
            message = message.rstrip()

    text = message.strip() if message else ""
    if not text:
        raise click.ClickException("Thought cannot be empty")
    if len(text) > 500:
        raise click.ClickException("Thought must be 500 characters or less")

    if goal_id:
        goal_obj = storage.get_goal(goal_id)
        if goal_obj.archived:
            raise click.ClickException("Goal is archived")

    thought_obj = Thought.new(text, goal_id)
    storage.add_thought(thought_obj)
    console.print(":thought_balloon: noted")


@thought_cmds.command("list")
@click.option("-g", "--goal", "goal_id", help="Filter by goal ID")
@click.option("--limit", type=int, default=10, show_default=True, help="Max rows")
@handle_exceptions
@click.pass_context
def list_thoughts_cmd(ctx: click.Context, goal_id: str | None, limit: int) -> None:
    """Display recent thoughts."""
    obj = cast(AppContext, ctx.obj)
    storage: Storage = obj["storage"]
    thoughts = storage.list_thoughts(goal_id=goal_id, limit=limit, newest_first=True)

    table = Table(title="Thoughts")
    table.add_column("ID")
    table.add_column("When")
    table.add_column("Goal")
    table.add_column("Thought")

    for th in thoughts:
        when = natural_delta(th.timestamp)
        goal_title = ""
        if th.goal_id:
            if storage.table.contains(Query().id == th.goal_id):
                goal_title = storage.get_goal(th.goal_id).title
            else:
                goal_title = th.goal_id
        table.add_row(th.id, when, goal_title, th.text)

    console.print(table)


@thought_cmds.command("rm")
@click.argument("thought_id")
@handle_exceptions
@click.pass_context
def remove_thought_cmd(ctx: click.Context, thought_id: str) -> None:
    """Delete a thought."""
    obj = cast(AppContext, ctx.obj)
    storage: Storage = obj["storage"]
    if storage.remove_thought(thought_id):
        console.print(f"[green]Removed[/green] {thought_id}")
    else:
        console.print(f"[yellow]Thought {thought_id} not found[/yellow]")
