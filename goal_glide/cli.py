from __future__ import annotations

import os
import uuid
from datetime import datetime
from pathlib import Path

import click

from rich.console import Console
from rich.table import Table

from .config import load_config, quotes_enabled, save_config
from .exceptions import (
    GoalAlreadyArchivedError,
    GoalNotArchivedError,
    GoalNotFoundError,
)
from .models.goal import Goal, Priority
from .models.storage import Storage
from .models.thought import Thought
from .services.pomodoro import PomodoroSession, start_session, stop_session
from .services.quotes import get_random_quote
from .services.render import render_goals
from .utils.timefmt import natural_delta


def get_storage() -> Storage:
    db_dir = os.environ.get("GOAL_GLIDE_DB_DIR")
    return Storage(Path(db_dir) if db_dir else None)


console = Console()


def _fmt(seconds: int) -> str:
    mins = int(seconds // 60)
    return f"{mins}m"


def _print_completion(session: PomodoroSession) -> None:
    console.print(f"Pomodoro complete ✅ ({_fmt(session.duration_sec)})")
    if quotes_enabled():
        quote, author = get_random_quote()
        console.print(
            f"[cyan italic]“{quote}”[/]\n— [bold]{author}[/]", justify="center"
        )


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


cli = goal


@click.group(help="Manage pomodoro sessions.")
def pomo() -> None:
    pass


@pomo.command("start")
@click.option("--duration", type=int, default=25, show_default=True, help="Minutes")
def start_pomo(duration: int) -> None:
    start_session(duration)
    console.print(f"Started pomodoro for {duration}m")


@pomo.command("stop")
def stop_pomo() -> None:
    try:
        session = stop_session()
    except RuntimeError as exc:
        console.print(f"[red]{exc}[/red]")
        raise SystemExit(1)
    _print_completion(session)


goal.add_command(pomo)


@click.group()
def config() -> None:
    """Configuration commands."""


@config.command("quotes")
@click.option("--enable/--disable", default=None, help="Toggle motivational quotes")
def cfg_quotes(enable: bool | None) -> None:
    cfg = load_config()
    if enable is not None:
        cfg["quotes_enabled"] = enable
        save_config(cfg)
    console.print(f"Quotes are {'ON' if cfg.get('quotes_enabled', True) else 'OFF'}")


goal.add_command(config)


@click.group(help="Capture and review quick reflections.")
def thought() -> None:
    pass


goal.add_command(thought)


@thought.command("jot")
@click.argument("message", required=False)
@click.option("-g", "--goal", "goal_id", help="Attach note to a goal ID")
def jot_thought(message: str | None, goal_id: str | None) -> None:
    """Record a short thought or reflection."""
    storage = get_storage()

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
        try:
            goal_obj = storage.get_goal(goal_id)
        except GoalNotFoundError as exc:
            raise click.ClickException(str(exc)) from exc
        if goal_obj.archived:
            raise click.ClickException("Goal is archived")

    thought_obj = Thought.new(text, goal_id)
    storage.add_thought(thought_obj)
    console.print(":thought_balloon: noted")


@thought.command("list")
@click.option("-g", "--goal", "goal_id", help="Filter by goal ID")
@click.option("--limit", type=int, default=10, show_default=True, help="Max rows")
def list_thoughts_cmd(goal_id: str | None, limit: int) -> None:
    """Display recent thoughts."""
    storage = get_storage()
    thoughts = storage.list_thoughts(goal_id=goal_id, limit=limit, newest_first=True)

    table = Table(title="Thoughts")
    table.add_column("When")
    table.add_column("Goal")
    table.add_column("Thought")

    for th in thoughts:
        when = natural_delta(th.timestamp)
        goal_title = ""
        if th.goal_id:
            try:
                goal_title = storage.get_goal(th.goal_id).title
            except GoalNotFoundError:
                goal_title = th.goal_id
        table.add_row(when, goal_title, th.text)

    console.print(table)


if __name__ == "__main__":
    cli()
