from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import cast

import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from .common import AppContext
from ..models.storage import Storage
from ..services import report

console = Console()


@click.group("report")
def report_cmds() -> None:
    """Generate progress reports."""
    pass


@report_cmds.command("make")
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
    obj = cast(AppContext, ctx.obj)
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

