from __future__ import annotations

import click
from typing import cast

from .commands.common import AppContext, get_storage, handle_exceptions
from .config import load_config
from .commands.goal_cmds import goal_cmds
from .commands.pomo_cmds import pomo_cmds
from .commands.tag_cmds import tag_cmds
from .commands.thought_cmds import thought_cmds
from .commands.config_cmds import config_cmds
from .commands.reminder_cmds import reminder_cmds
from .commands.report_cmds import report_cmds
from .commands.stats_cmds import stats_cmds
from .commands.version_cmds import version_cmds


@click.group()
@click.pass_context
@handle_exceptions
def cli(ctx: click.Context) -> None:
    """Goal Glide: A command-line tool for managing personal goals and
    tracking focus with the Pomodoro technique."""
    storage = get_storage()
    config = load_config()
    ctx.obj = cast(AppContext, {"storage": storage, "config": config})


cli.add_command(goal_cmds)
cli.add_command(pomo_cmds)
goal_cmds.add_command(tag_cmds)
cli.add_command(thought_cmds)
cli.add_command(config_cmds)
cli.add_command(reminder_cmds)
cli.add_command(report_cmds)
cli.add_command(stats_cmds)
cli.add_command(version_cmds)

__all__ = ["cli"]
