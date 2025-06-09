from __future__ import annotations

from datetime import datetime, timedelta
from typing import cast

import click
from rich.bar import Bar
from rich.table import Table
from tinydb import Query

from .common import AppContext, console
from ..services.analytics import (
    current_streak,
    total_time_by_goal,
    date_histogram,
    most_productive_day,
    longest_streak,
)
from ..utils.format import format_duration, format_duration_long
from ..models.storage import Storage


@click.command("stats")
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
def stats_cmds(
    ctx: click.Context,
    month: bool,
    show_goals: bool,
    start_date: datetime | None,
    end_date: datetime | None,
) -> None:
    """Visualise focus stats and streaks."""
    obj = cast(AppContext, ctx.obj)
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

    bars: list[tuple[str, Bar]] = []
    if start_date and end_date:
        start = start_date.date()
        end = end_date.date()
        if start > end:
            raise click.UsageError("--from must not be after --to")
        hist = date_histogram(storage, start, end)
        for day, total in sorted(hist.items()):
            label = day.strftime("%m-%d")
            bars.append((label, Bar(7200, 0, total, color=_color(total))))
    elif month:
        first = today.replace(day=1)
        last_month_end = first - timedelta(days=1)
        start = last_month_end.replace(day=1)
        end = last_month_end
        for i in range(4):
            week_start = start + timedelta(days=i * 7)
            hist = date_histogram(storage, week_start, week_start + timedelta(days=6))
            total = sum(hist.values())
            bars.append((f"W{i+1}", Bar(7 * 7200, 0, total, color=_color(total))))
    else:
        start = today - timedelta(days=today.weekday())
        end = start + timedelta(days=6)
        hist = date_histogram(storage, start, end)
        for day, total in sorted(hist.items()):
            label = day.strftime("%a")
            bars.append((label, Bar(7200, 0, total, color=_color(total))))

    if not any(bar.end for _, bar in bars):
        console.print("No session data yet.")
        raise SystemExit(0)

    for label, bar in bars:
        console.print(label, bar)

    streak = current_streak(storage, end)
    console.print(f"\N{FIRE}  Current streak: {streak} days")

    longest = longest_streak(storage)
    console.print(f"\N{HIGH VOLTAGE SIGN}  Longest streak: {longest} days")

    full_hist = date_histogram(storage, start, end)
    mpd = most_productive_day(storage, start, end)
    if mpd:
        totals: dict[str, int] = {}
        counts: dict[str, int] = {}
        for d, sec in full_hist.items():
            name = d.strftime("%A")
            totals[name] = totals.get(name, 0) + sec
            counts[name] = counts.get(name, 0) + 1
        avg = totals[mpd] // counts[mpd] if counts[mpd] else 0
        avg_fmt = format_duration_long(avg)
        console.print(f"\N{CALENDAR}  Most productive day: {mpd} (avg. {avg_fmt})")

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
