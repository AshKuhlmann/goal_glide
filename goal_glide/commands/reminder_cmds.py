from __future__ import annotations

import click
from rich.console import Console
from typing import cast

from .common import AppContext, handle_exceptions
from ..config import save_config
from .. import config as cfg

console = Console()


@click.group("reminder", help="Configure desktop break reminders.")
def reminder_cmds() -> None:
    pass


@reminder_cmds.command("enable")
@handle_exceptions
@click.pass_context
def reminder_enable(ctx: click.Context) -> None:
    obj = cast(AppContext, ctx.obj)
    c = obj["config"]
    c["reminders_enabled"] = True
    save_config(c)
    console.print("Reminders ON")


@reminder_cmds.command("disable")
@handle_exceptions
@click.pass_context
def reminder_disable(ctx: click.Context) -> None:
    obj = cast(AppContext, ctx.obj)
    c = obj["config"]
    c["reminders_enabled"] = False
    save_config(c)
    console.print("Reminders OFF")


@reminder_cmds.command("config")
@click.option("--break", "break_", type=int, help="Break length minutes (1-120)")
@click.option("--interval", type=int, help="Interval minutes (1-120)")
@handle_exceptions
@click.pass_context
def reminder_config(ctx: click.Context, break_: int | None, interval: int | None) -> None:
    obj = cast(AppContext, ctx.obj)
    c = obj["config"]
    if break_ is not None:
        if not 1 <= break_ <= 120:
            raise ValueError("break must be between 1 and 120")
        c["reminder_break_min"] = break_
    if interval is not None:
        if not 1 <= interval <= 120:
            raise ValueError("interval must be between 1 and 120")
        c["reminder_interval_min"] = interval
    save_config(c)
    console.print(f"Break {c['reminder_break_min']}m, Interval {c['reminder_interval_min']}m")


@reminder_cmds.command("status")
@click.pass_context
def reminder_status(ctx: click.Context) -> None:
    obj = cast(AppContext, ctx.obj)
    cfg_dict = obj["config"]
    enabled = cfg_dict.get("reminders_enabled", False)
    break_min = cfg_dict.get("reminder_break_min", 5)
    interval_min = cfg_dict.get("reminder_interval_min", 30)
    console.print(f"Enabled: {enabled} | Break: {break_min}m | Interval: {interval_min}m")

