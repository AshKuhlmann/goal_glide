from __future__ import annotations

import click
from typing import cast

from .common import AppContext, handle_exceptions
from ..config import save_config


@click.group("reminder", help="Configure desktop break reminders.")
def reminder_cmds() -> None:
    pass


@reminder_cmds.command("enable")
@handle_exceptions
@click.pass_context
def reminder_enable(ctx: click.Context) -> None:
    obj = cast(AppContext, ctx.obj)
    cfg = obj["config"]
    cfg["reminders_enabled"] = True
    save_config(cfg)
    click.echo("Reminders ON")


@reminder_cmds.command("disable")
@handle_exceptions
@click.pass_context
def reminder_disable(ctx: click.Context) -> None:
    obj = cast(AppContext, ctx.obj)
    cfg = obj["config"]
    cfg["reminders_enabled"] = False
    save_config(cfg)
    click.echo("Reminders OFF")


@reminder_cmds.command("config")
@click.option("--break", "break_", type=int, help="Break length minutes (1-120)")
@click.option("--interval", type=int, help="Interval minutes (1-120)")
@handle_exceptions
@click.pass_context
def reminder_config(ctx: click.Context, break_: int | None, interval: int | None) -> None:
    obj = cast(AppContext, ctx.obj)
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
    click.echo(
        f"Break {cfg['reminder_break_min']}m, Interval {cfg['reminder_interval_min']}m"
    )


@reminder_cmds.command("status")
@click.pass_context
def reminder_status(ctx: click.Context) -> None:
    obj = cast(AppContext, ctx.obj)
    cfg = obj["config"]
    enabled = cfg.get("reminders_enabled", False)
    break_min = cfg.get("reminder_break_min", 5)
    interval_min = cfg.get("reminder_interval_min", 30)
    click.echo(
        f"Enabled: {enabled} | Break: {break_min}m | Interval: {interval_min}m"
    )
