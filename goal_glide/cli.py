from __future__ import annotations

import functools
import os
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable, ParamSpec, TypeVar, cast

import click

from rich.bar import Bar
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
from tinydb import Query

from .config import load_config, quotes_enabled, save_config
from .exceptions import (
    GoalAlreadyArchivedError,
    GoalNotArchivedError,
    GoalNotFoundError,
    InvalidTagError,
)
from .models.goal import Goal, Priority
from .models.storage import Storage
from .models.thought import Thought
from .services import report
from .services.analytics import current_streak, total_time_by_goal, weekly_histogram
from .services.pomodoro import PomodoroSession, start_session, stop_session
from .services.quotes import get_random_quote
from .services.render import render_goals
from .utils.format import format_duration
from .utils.tag import validate_tag
from .utils.timefmt import natural_delta

console = Console()

P = ParamSpec("P")
R = TypeVar("R")


# ── Centralised exception handler ────────────────────────────────────────────
def handle_exceptions(func: Callable[P, R]) -> Callable[P, R]:
    """Catch domain errors uniformly and exit status 1."""

    @functools.wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        try:
            return func(*args, **kwargs)
        except (
            GoalNotFoundError,
            GoalAlreadyArchivedError,
            GoalNotArchivedError,
            InvalidTagError,
            click.ClickException,
            RuntimeError,  # e.g. stop_pomo with no session
            ValueError,  # e.g. reminder_config validation
        ) as exc:
            console.print(f"[bold red]Error:[/bold red] {exc}")
            raise SystemExit(1)
        except Exception as exc:
            console.print(f"[bold red]An unexpected error occurred:[/bold red] {exc}")
            raise SystemExit(1)

    return wrapper


def get_storage() -> Storage:
    db_dir = os.environ.get("GOAL_GLIDE_DB_DIR")
    return Storage(Path(db_dir) if db_dir else None)


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
@handle_exceptions
def remove_goal_cmd(goal_id: str) -> None:
    """Permanently remove a goal."""
    storage = get_storage()
    if click.confirm(f"Remove goal {goal_id}?"):
        storage.remove_goal(goal_id)
        console.print(f"[green]Removed[/green] {goal_id}")


@goal.command("archive")
@click.argument("goal_id")
@handle_exceptions
def archive_goal_cmd(goal_id: str) -> None:
    """Hide a goal from normal listings."""
    storage = get_storage()
    storage.archive_goal(goal_id)
    console.print(f":package: Goal {goal_id} archived")


@goal.command("restore")
@click.argument("goal_id")
@handle_exceptions
def restore_goal_cmd(goal_id: str) -> None:
    """Bring a goal back into the active list."""
    storage = get_storage()
    storage.restore_goal(goal_id)
    console.print(f":package: Goal {goal_id} restored")


@goal.group("tag")
def tag() -> None:
    """Tag management."""
    pass


@tag.command("add")
@click.argument("goal_id")
@click.argument("tags", nargs=-1, required=True)
@handle_exceptions
def tag_add(goal_id: str, tags: tuple[str, ...]) -> None:
    """Add one or more tags to a goal."""
    storage = get_storage()
    validated = [validate_tag(t) for t in tags]
    goal = storage.add_tags(goal_id, validated)
    console.print(f"Tags for {goal.id}: {', '.join(goal.tags)}")


@tag.command("rm")
@click.argument("goal_id")
@click.argument("tag")
@handle_exceptions
def tag_rm(goal_id: str, tag: str) -> None:
    """Remove a tag from a goal."""
    storage = get_storage()
    validated = validate_tag(tag)
    before = storage.get_goal(goal_id)
    updated = storage.remove_tag(goal_id, validated)
    if validated not in before.tags:
        console.print(f"[yellow]Tag '{validated}' not present[/yellow]")
    console.print(f"Tags for {updated.id}: {', '.join(updated.tags)}")


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
@click.option("--tag", "tags", multiple=True, help="Filter goals by tag (AND logic)")
def list_goals(
    archived: bool, show_all: bool, priority: str | None, tags: tuple[str, ...]
) -> None:
    """List goals with optional filtering."""
    storage = get_storage()
    goals = storage.list_goals(
        include_archived=show_all,
        only_archived=archived,
        priority=Priority(priority) if priority else None,
        tags=list(tags) if tags else None,
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
@handle_exceptions
def start_pomo(duration: int) -> None:
    start_session(duration)
    console.print(f"Started pomodoro for {duration}m")


@pomo.command("stop")
@handle_exceptions
def stop_pomo() -> None:
    session = stop_session()
    _print_completion(session)


goal.add_command(pomo)


@goal.group(name="reminder", help="Configure desktop break reminders.")
def reminder_cli() -> None:
    pass


@reminder_cli.command("enable")
@handle_exceptions
def reminder_enable() -> None:
    cfg = load_config()
    cfg["reminders_enabled"] = True
    save_config(cfg)
    console.print("Reminders ON")


@reminder_cli.command("disable")
@handle_exceptions
def reminder_disable() -> None:
    cfg = load_config()
    cfg["reminders_enabled"] = False
    save_config(cfg)
    console.print("Reminders OFF")


@reminder_cli.command("config")
@click.option("--break", "break_", type=int, help="Break length minutes (1-120)")
@click.option("--interval", type=int, help="Interval minutes (1-120)")
@handle_exceptions
def reminder_config(break_: int | None, interval: int | None) -> None:
    cfg = load_config()
    if break_ is not None:
        if not 1 <= break_ <= 120:
            raise ValueError("break must be between 1 and 120")
        cfg["reminder_break_min"] = break_
    if interval is not None:
        if not 1 <= interval <= 120:
            raise ValueError("interval must be between 1 and 120")
        cfg["reminder_interval_min"] = interval
    save_config(cfg)
    console.print(
        f"Break {cfg['reminder_break_min']}m, Interval {cfg['reminder_interval_min']}m"
    )


@reminder_cli.command("status")
def reminder_status() -> None:
    cfg = load_config()
    console.print(
        "Enabled: "
        f"{cfg.get('reminders_enabled', False)} | "
        f"Break: {cfg.get('reminder_break_min', 5)}m | "
        f"Interval: {cfg.get('reminder_interval_min', 30)}m"
    )


goal.add_command(reminder_cli)


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
@handle_exceptions
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
        goal_obj = storage.get_goal(goal_id)
        if goal_obj.archived:
            raise click.ClickException("Goal is archived")

    thought_obj = Thought.new(text, goal_id)
    storage.add_thought(thought_obj)
    console.print(":thought_balloon: noted")


@thought.command("list")
@click.option("-g", "--goal", "goal_id", help="Filter by goal ID")
@click.option("--limit", type=int, default=10, show_default=True, help="Max rows")
@handle_exceptions
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
            if storage.table.contains(Query().id == th.goal_id):
                goal_title = storage.get_goal(th.goal_id).title
            else:
                goal_title = th.goal_id
        table.add_row(when, goal_title, th.text)

    console.print(table)


@goal.command("stats")
@click.option("--month", is_flag=True, help="Show last calendar month")
@click.option("--goals", "show_goals", is_flag=True, help="Breakdown by top goals")
def stats_cmd(month: bool, show_goals: bool) -> None:
    """Visualise focus stats and streaks."""
    storage = get_storage()
    today = datetime.now().date()

    def _color(seconds: int) -> str:
        if seconds >= 7200:
            return "green"
        if seconds >= 3600:
            return "yellow"
        return "red"

    bars: list[Bar] = []
    if month:
        first = today.replace(day=1)
        last_month_end = first - timedelta(days=1)
        start = last_month_end.replace(day=1)
        for i in range(4):
            week_start = start + timedelta(days=i * 7)
            hist = weekly_histogram(storage, week_start)
            total = sum(hist.values())
            bars.append(Bar(total, label=f"W{i+1}", max=7 * 7200, color=_color(total)))
    else:
        start = today - timedelta(days=today.weekday())
        hist = weekly_histogram(storage, start)
        for day, total in sorted(hist.items()):
            label = day.strftime("%a")
            bars.append(Bar(total, label=label, max=7200, color=_color(total)))

    if not any(b.value for b in bars):
        console.print("No session data yet.")
        raise SystemExit(0)

    for bar in bars:
        console.print(bar)

    streak = current_streak(storage, today)
    console.print(f"\N{FIRE}  Current streak: {streak} days")

    if show_goals:
        totals = total_time_by_goal(storage)
        if not totals:
            console.print("No session data yet.")
            return
        table = Table(title="Top Goals")
        table.add_column("Goal")
        table.add_column("Time")
        ranked = sorted(totals.items(), key=lambda t: t[1], reverse=True)[:5]
        for gid, sec in ranked:
            if storage.table.contains(Query().id == gid):
                title = storage.get_goal(gid).title
            else:
                title = gid
            table.add_row(title, format_duration(sec))
        console.print(table)


@goal.group(name="report")
def report_group() -> None:
    """Generate progress reports."""
    pass


@report_group.command("make")
@click.option("--week", "range_week", is_flag=True, help="Last week")
@click.option("--month", "range_month", is_flag=True, help="Last month")
@click.option("--all", "range_all", is_flag=True, help="All time")
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["html", "md", "csv"]),
    default="html",
    show_default=True,
)
@click.option("--out", "out_path", type=Path, help="Output file path")
def report_make(
    range_week: bool,
    range_month: bool,
    range_all: bool,
    fmt: str,
    out_path: Path | None,
) -> None:
    """Create a report."""
    flags = [range_week, range_month, range_all]
    if sum(flags) > 1:
        raise click.UsageError("Choose only one of --week/--month/--all")
    range_ = (
        "week"
        if range_week
        else "month" if range_month else "all" if range_all else "week"
    )
    storage = get_storage()
    with Progress(
        SpinnerColumn(), TextColumn("[progress.description]{task.description}")
    ) as prog:
        prog.add_task(description="Building report…", total=None)
        path = report.build_report(
            storage,
            cast(report.Range, range_),
            cast(report.Fmt, fmt),
            out_path,
        )
    console.print(f":page_facing_up:  Report saved to [bold]{path}[/]")


if __name__ == "__main__":
    cli()
