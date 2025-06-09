from __future__ import annotations

import click
from typing import cast

from rich.table import Table

from .common import AppContext, console
from ..config import save_config


@click.group("config")
def config_cmds() -> None:
    """Configuration commands."""
    pass


@config_cmds.command("quotes")
@click.option("--enable/--disable", default=None, help="Toggle motivational quotes")
@click.pass_context
def cfg_quotes(ctx: click.Context, enable: bool | None) -> None:
    obj = cast(AppContext, ctx.obj)
    cfg = obj["config"]
    if enable is not None:
        cfg["quotes_enabled"] = enable
        save_config(cfg)
    console.print(f"Quotes are {'ON' if cfg.get('quotes_enabled', True) else 'OFF'}")


@config_cmds.command("show")
@click.pass_context
def cfg_show(ctx: click.Context) -> None:
    """Show current configuration."""
    obj = cast(AppContext, ctx.obj)
    cfg = obj["config"]
    table = Table(title="Config")
    table.add_column("Key")
    table.add_column("Value")
    for key, value in cfg.items():
        table.add_row(key, str(value))
    console.print(table)
