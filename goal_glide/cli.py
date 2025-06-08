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

from .config import load_config, save_config
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
from .services.analytics import (
    current_streak,
    total_time_by_goal,
    date_histogram,
)
from .services.pomodoro import (
    load_active_session,
    pause_session,
    resume_session,
    start_session,
    stop_session,
)
from .models.session import PomodoroSession
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


def _print_completion(session: PomodoroSession, config: dict) -> None:
    console.print(f"Pomodoro complete ✅ ({_fmt(session.duration_sec)})")
    if config.get("quotes_enabled", True):
        quote, author = get_random_quote()
        console.print(
            f"[cyan italic]“{quote}”[/]\n— [bold]{author}[/]", justify="center"
        )


@click.group()
@click.pass_context
def goal(ctx: click.Context) -> None:
    """Goal management CLI."""
    ctx.obj = {
        "storage": get_storage(),
        "config": load_config(),
    }


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
@click.pass_context
def add_goal(ctx: click.Context, title: str, priority: str) -> None:
    """Add a new goal."""
    title = title.strip()
    if not title:
        console.print("[red]Title cannot be empty.[/red]")
        raise SystemExit(1)

    obj = cast(dict, ctx.obj)
    storage: Storage = obj["storage"]
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
@click.pass_context
def remove_goal_cmd(ctx: click.Context, goal_id: str) -> None:
    """Permanently remove a goal."""
    obj = cast(dict, ctx.obj)
    storage: Storage = obj["storage"]
    if click.confirm(f"Remove goal {goal_id}?"):
        storage.remove_goal(goal_id)
        console.print(f"[green]Removed[/green] {goal_id}")


@goal.command("archive")
@click.argument("goal_id")
@handle_exceptions
@click.pass_context
def archive_goal_cmd(ctx: click.Context, goal_id: str) -> None:
    """Hide a goal from normal listings."""
    obj = cast(dict, ctx.obj)
    storage: Storage = obj["storage"]
    storage.archive_goal(goal_id)
    console.print(f":package: Goal {goal_id} archived")


@goal.command("restore")
@click.argument("goal_id")
@handle_exceptions
@click.pass_context
def restore_goal_cmd(ctx: click.Context, goal_id: str) -> None:
    """Bring a goal back into the active list."""
    obj = cast(dict, ctx.obj)
    storage: Storage = obj["storage"]
    storage.restore_goal(goal_id)
    console.print(f":package: Goal {goal_id} restored")


@goal.command("update")
@click.argument("goal_id")
@click.option("--title", help="New goal title")
@click.option(
    "--priority",
    type=click.Choice([e.value for e in Priority]),
    help="Goal priority (low, medium, high)",
)
@handle_exceptions
@click.pass_context
def update_goal_cmd(
    ctx: click.Context, goal_id: str, title: str | None, priority: str | None
) -> None:
    """Modify goal attributes."""
    obj = cast(dict, ctx.obj)
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

    updated = Goal(
        id=goal.id,
        title=new_title,
        created=goal.created,
        priority=new_priority,
        archived=goal.archived,
        tags=goal.tags,
        parent_id=goal.parent_id,
    )
    storage.update_goal(updated)
    console.print(f":pencil: Updated goal {updated.id}")


@goal.group("tag")
def tag() -> None:
    """Tag management."""
    pass


@tag.command("add")
@click.argument("goal_id")
@click.argument("tags", nargs=-1, required=True)
@handle_exceptions
@click.pass_context
def tag_add(ctx: click.Context, goal_id: str, tags: tuple[str, ...]) -> None:
    """Add one or more tags to a goal."""
    obj = cast(dict, ctx.obj)
    storage: Storage = obj["storage"]
    validated = [validate_tag(t) for t in tags]
    goal = storage.add_tags(goal_id, validated)
    console.print(f"Tags for {goal.id}: {', '.join(goal.tags)}")


@tag.command("rm")
@click.argument("goal_id")
@click.argument("tag")
@handle_exceptions
@click.pass_context
def tag_rm(ctx: click.Context, goal_id: str, tag: str) -> None:
    """Remove a tag from a goal."""
    obj = cast(dict, ctx.obj)
    storage: Storage = obj["storage"]
    validated = validate_tag(tag)
    before = storage.get_goal(goal_id)
    updated = storage.remove_tag(goal_id, validated)
    if validated not in before.tags:
        console.print(f"[yellow]Tag '{validated}' not present[/yellow]")
    console.print(f"Tags for {updated.id}: {', '.join(updated.tags)}")


@tag.command("list")
@click.pass_context
def tag_list(ctx: click.Context) -> None:
    """List all tags with goal counts."""
    obj = cast(dict, ctx.obj)
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
@click.pass_context
def list_goals(
    ctx: click.Context,
    archived: bool,
    show_all: bool,
    priority: str | None,
    tags: tuple[str, ...],
) -> None:
    """List goals with optional filtering."""
    obj = cast(dict, ctx.obj)
    storage: Storage = obj["storage"]
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
@click.option("-g", "--goal", "goal_id", help="Associate with goal ID")
@handle_exceptions
def start_pomo(duration: int, goal_id: str | None) -> None:
    start_session(duration, goal_id)
    console.print(f"Started pomodoro for {duration}m")


@pomo.command("stop")
@handle_exceptions
@click.pass_context
def stop_pomo(ctx: click.Context) -> None:
    session = stop_session()
    obj = cast(dict, ctx.obj)
    storage: Storage = obj["storage"]
    storage.add_session(
        PomodoroSession.new(session.goal_id, session.start, session.duration_sec)
    )
    _print_completion(session, obj["config"])


@pomo.command("pause")
@handle_exceptions
def pause_pomo() -> None:
    pause_session()
    console.print("Session paused")


@pomo.command("resume")
@handle_exceptions
def resume_pomo() -> None:
    resume_session()
    console.print("Session resumed")


@pomo.command("status")
@handle_exceptions
def status_pomo() -> None:
    """Show the remaining time for the current session."""
    session = load_active_session()
    if session is None:
        console.print("No active session")
        return
    elapsed = session.elapsed_sec
    if not session.paused and session.last_start is not None:
        elapsed += int((datetime.now() - session.last_start).total_seconds())
    remaining = max(session.duration_sec - elapsed, 0)
    console.print(f"Elapsed {_fmt(elapsed)} | Remaining {_fmt(remaining)}")


goal.add_command(pomo)


@goal.group(name="reminder", help="Configure desktop break reminders.")
def reminder_cli() -> None:
    pass


@reminder_cli.command("enable")
@handle_exceptions
@click.pass_context
def reminder_enable(ctx: click.Context) -> None:
    obj = cast(dict, ctx.obj)
    cfg = obj["config"]
    cfg["reminders_enabled"] = True
    save_config(cfg)
    console.print("Reminders ON")


@reminder_cli.command("disable")
@handle_exceptions
@click.pass_context
def reminder_disable(ctx: click.Context) -> None:
    obj = cast(dict, ctx.obj)
    cfg = obj["config"]
    cfg["reminders_enabled"] = False
    save_config(cfg)
    console.print("Reminders OFF")


@reminder_cli.command("config")
@click.option("--break", "break_", type=int, help="Break length minutes (1-120)")
@click.option("--interval", type=int, help="Interval minutes (1-120)")
@handle_exceptions
@click.pass_context
def reminder_config(
    ctx: click.Context, break_: int | None, interval: int | None
) -> None:
    obj = cast(dict, ctx.obj)
    cfg = obj["config"]
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
@click.pass_context
def reminder_status(ctx: click.Context) -> None:
    obj = cast(dict, ctx.obj)
    cfg = obj["config"]
    enabled = cfg.get("reminders_enabled", False)
    break_min = cfg.get("reminder_break_min", 5)
    interval_min = cfg.get("reminder_interval_min", 30)
    console.print(
        f"Enabled: {enabled} | Break: {break_min}m | Interval: {interval_min}m"
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
@click.pass_context
def cfg_quotes(ctx: click.Context, enable: bool | None) -> None:
    obj = cast(dict, ctx.obj)
    cfg = obj["config"]
    if enable is not None:
        cfg["quotes_enabled"] = enable
        save_config(cfg)
    console.print(f"Quotes are {'ON' if cfg.get('quotes_enabled', True) else 'OFF'}")


@config.command("show")
@click.pass_context
def cfg_show(ctx: click.Context) -> None:
    """Show current configuration."""
    obj = cast(dict, ctx.obj)
    cfg = obj["config"]
    table = Table(title="Config")
    table.add_column("Key")
    table.add_column("Value")
    for key, value in cfg.items():
        table.add_row(key, str(value))
    console.print(table)


goal.add_command(config)


@click.group(help="Capture and review quick reflections.")
@click.pass_context
def thought(ctx: click.Context) -> None:
    if ctx.obj is None:
        ctx.obj = {
            "storage": get_storage(),
            "config": load_config(),
        }


goal.add_command(thought)


@thought.command("jot")
@click.argument("message", required=False)
@click.option("-g", "--goal", "goal_id", help="Attach note to a goal ID")
@handle_exceptions
@click.pass_context
def jot_thought(ctx: click.Context, message: str | None, goal_id: str | None) -> None:
    """Record a short thought or reflection."""
    obj = cast(dict, ctx.obj)
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


@thought.command("list")
@click.option("-g", "--goal", "goal_id", help="Filter by goal ID")
@click.option("--limit", type=int, default=10, show_default=True, help="Max rows")
@handle_exceptions
@click.pass_context
def list_thoughts_cmd(ctx: click.Context, goal_id: str | None, limit: int) -> None:
    """Display recent thoughts."""
    obj = cast(dict, ctx.obj)
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


@thought.command("rm")
@click.argument("thought_id")
@handle_exceptions
@click.pass_context
def remove_thought_cmd(ctx: click.Context, thought_id: str) -> None:
    """Delete a thought."""
    obj = cast(dict, ctx.obj)
    storage: Storage = obj["storage"]
    if storage.remove_thought(thought_id):
        console.print(f"[green]Removed[/green] {thought_id}")
    else:
        console.print(f"[yellow]Thought {thought_id} not found[/yellow]")


@goal.command("stats")
@click.option("--month", is_flag=True, help="Show last calendar month")
@click.option("--goals", "show_goals", is_flag=True, help="Breakdown by top goals")
@click.option(
    "--from",
    "start_date",
    type=click.DateTime(formats=["%Y-%m-%d"]),
    help="Start date YYYY-MM-DD",
)
@click.option(
    "--to",
    "end_date",
    type=click.DateTime(formats=["%Y-%m-%d"]),
    help="End date YYYY-MM-DD",
)
@click.pass_context
def stats_cmd(
    ctx: click.Context,
    month: bool,
    show_goals: bool,
    start_date: datetime | None,
    end_date: datetime | None,
) -> None:
    """Visualise focus stats and streaks."""
    obj = cast(dict, ctx.obj)
    storage: Storage = obj["storage"]
    today = datetime.now().date()

    def _color(seconds: int) -> str:
        if seconds >= 7200:
            return "green"
        if seconds >= 3600:
            return "yellow"
        return "red"

    if (start_date is not None) ^ (end_date is not None):
        raise click.UsageError("Specify both --from and --to")

    bars: list[Bar] = []
    if start_date and end_date:
        start = start_date.date()
        end = end_date.date()
        if start > end:
            raise click.UsageError("--from must not be after --to")
        hist = date_histogram(storage, start, end)
        for day, total in sorted(hist.items()):
            label = day.strftime("%m-%d")
            bars.append(Bar(total, label=label, max=7200, color=_color(total)))
    elif month:
        first = today.replace(day=1)
        last_month_end = first - timedelta(days=1)
        start = last_month_end.replace(day=1)
        end = last_month_end
        for i in range(4):
            week_start = start + timedelta(days=i * 7)
            hist = date_histogram(storage, week_start, week_start + timedelta(days=6))
            total = sum(hist.values())
            bars.append(Bar(total, label=f"W{i+1}", max=7 * 7200, color=_color(total)))
    else:
        start = today - timedelta(days=today.weekday())
        end = start + timedelta(days=6)
        hist = date_histogram(storage, start, end)
        for day, total in sorted(hist.items()):
            label = day.strftime("%a")
            bars.append(Bar(total, label=label, max=7200, color=_color(total)))

    if not any(b.value for b in bars):
        console.print("No session data yet.")
        raise SystemExit(0)

    for bar in bars:
        console.print(bar)

    streak = current_streak(storage, end)
    console.print(f"\N{FIRE}  Current streak: {streak} days")

    if show_goals:
        totals = total_time_by_goal(storage, start, end)
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
@click.option(
    "--from",
    "start_date",
    type=click.DateTime(formats=["%Y-%m-%d"]),
    help="Start date YYYY-MM-DD",
)
@click.option(
    "--to",
    "end_date",
    type=click.DateTime(formats=["%Y-%m-%d"]),
    help="End date YYYY-MM-DD",
)
@click.pass_context
def report_make(
    ctx: click.Context,
    range_week: bool,
    range_month: bool,
    range_all: bool,
    fmt: str,
    out_path: Path | None,
    start_date: datetime | None,
    end_date: datetime | None,
) -> None:
    """Create a report."""
    flags = [range_week, range_month, range_all]
    if sum(flags) > 1:
        raise click.UsageError("Choose only one of --week/--month/--all")
    if (start_date is not None) ^ (end_date is not None):
        raise click.UsageError("Specify both --from and --to")
    if (start_date or end_date) and any(flags):
        raise click.UsageError("--from/--to cannot be combined with range flags")
    range_ = (
        "week"
        if range_week
        else "month" if range_month else "all" if range_all else "week"
    )
    obj = cast(dict, ctx.obj)
    storage: Storage = obj["storage"]
    start = start_date.date() if start_date else None
    end = end_date.date() if end_date else None
    with Progress(
        SpinnerColumn(), TextColumn("[progress.description]{task.description}")
    ) as prog:
        prog.add_task(description="Building report…", total=None)
        path = report.build_report(
            storage,
            cast(report.Range, range_),
            cast(report.Fmt, fmt),
            out_path,
            start,
            end,
        )
    console.print(f":page_facing_up:  Report saved to [bold]{path}[/]")


if __name__ == "__main__":
    cli()
