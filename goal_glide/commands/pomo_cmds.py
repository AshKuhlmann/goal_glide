from __future__ import annotations

from typing import cast

import click

from .common import AppContext, handle_exceptions, console
from .. import cli as main_cli
from .. import config as cfg
from ..config import ConfigDict
from ..models.session import PomodoroSession
from ..models.storage import Storage
from ..services.pomodoro import (
    load_active_session,
    pause_session,
    resume_session,
    start_session,
    stop_session,
)


def _fmt(seconds: int) -> str:
    mins = int(seconds // 60)
    return f"{mins}m"


def _print_completion(session: PomodoroSession, config: ConfigDict) -> None:
    console.print(f"Pomodoro complete ✅ ({_fmt(session.duration_sec)})")
    if config.get("quotes_enabled", True):
        quote, author = main_cli.cli.get_random_quote()
        console.print(
            f"[cyan italic]“{quote}”[/]\n— [bold]{author}[/]", justify="center"
        )


@click.group(name="pomo", help="Manage pomodoro sessions.")
def pomo_cmds() -> None:
    pass


@pomo_cmds.command("start")
@click.option(
    "--duration",
    type=int,
    default=None,
    show_default=False,
    help="Minutes (defaults to config)",
)
@click.option("-g", "--goal", "goal_id", help="Associate with goal ID")
@handle_exceptions
def start_pomo(duration: int | None, goal_id: str | None) -> None:
    dur = duration
    if dur is None:
        dur = cfg.pomo_duration()
    start_session(dur, goal_id)
    console.print(f"Started pomodoro for {dur}m")


@pomo_cmds.command("stop")
@handle_exceptions
@click.pass_context
def stop_pomo(ctx: click.Context) -> None:
    session = stop_session()
    obj = cast(AppContext, ctx.obj)
    storage: Storage = obj["storage"]
    storage.add_session(
        PomodoroSession.new(session.goal_id, session.start, session.duration_sec)
    )
    _print_completion(session, obj["config"])


@pomo_cmds.command("pause")
@handle_exceptions
def pause_pomo() -> None:
    pause_session()
    console.print("Session paused")


@pomo_cmds.command("resume")
@handle_exceptions
def resume_pomo() -> None:
    resume_session()
    console.print("Session resumed")


@pomo_cmds.command("status")
@handle_exceptions
def status_pomo() -> None:
    """Show the remaining time for the current session."""
    session = load_active_session()
    if session is None:
        console.print("No active session")
        return
    elapsed = session.elapsed_sec
    if not session.paused and session.last_start is not None:
        now = main_cli.cli.datetime.now()
        elapsed += int((now - session.last_start).total_seconds())
    remaining = max(session.duration_sec - elapsed, 0)
    console.print(f"Elapsed {_fmt(elapsed)} | Remaining {_fmt(remaining)}")
