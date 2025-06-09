"""Create, load and manage Pomodoro sessions."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional, TypedDict, cast

from rich.console import Console
from filelock import FileLock

from .. import config
from ..models.session import PomodoroSession

console = Console()

on_new_session: list[Callable[[], None]] = []
on_session_end: list[Callable[[Path], None]] = []


@dataclass(slots=True)
class ActiveSession:
    goal_id: str | None
    start: datetime
    duration_sec: int
    elapsed_sec: int
    paused: bool
    last_start: datetime | None


class SessionData(TypedDict):
    start: str
    duration_sec: int
    goal_id: str | None
    elapsed_sec: int
    paused: bool
    last_start: str | None


def _load_data(session_path: Path) -> SessionData | None:
    lock = FileLock(session_path.with_suffix(".lock"))
    with lock:
        if not session_path.exists():
            return None
        with session_path.open(encoding="utf-8") as fp:
            data = cast(SessionData, json.load(fp))
    # backward compatibility for older session files
    data.setdefault("elapsed_sec", 0)
    data.setdefault("paused", False)
    data.setdefault("last_start", data.get("start"))
    return data


def _save_data(data: SessionData, session_path: Path) -> None:
    lock = FileLock(session_path.with_suffix(".lock"))
    with lock:
        with session_path.open("w", encoding="utf-8") as fp:
            json.dump(data, fp)


def start_session(
    duration_min: int | None = None,
    goal_id: str | None = None,
    *,
    session_path: Path,
    config_path: Path,
) -> PomodoroSession:
    """Start a new Pomodoro timer.

    Parameters
    ----------
    duration_min:
        Optional custom duration in minutes.  When not provided the default
        from the configuration is used.
    goal_id:
        Identifier of the goal this session relates to.
    session_path:
        File path used to persist the session state.
    config_path:
        Path to the configuration file from which defaults are read.

    Returns
    -------
    PomodoroSession
        The newly created session object.
    """
    dur = (
        duration_min if duration_min is not None else config.pomo_duration(config_path)
    )
    session = PomodoroSession(
        id="",
        goal_id=goal_id,
        start=datetime.now(),
        duration_sec=dur * 60,
    )
    data: SessionData = {
        "start": session.start.isoformat(),
        "duration_sec": session.duration_sec,
        "goal_id": session.goal_id,
        "elapsed_sec": 0,
        "paused": False,
        "last_start": session.start.isoformat(),
    }
    _save_data(data, session_path)
    for cb in on_new_session:
        cb()
    return session


def load_session(session_path: Path) -> Optional[PomodoroSession]:
    """Load a previously started session.

    Only the static session information is returned. Runtime data such as
    the elapsed time or pause state is ignored.

    Parameters
    ----------
    session_path:
        Path to the JSON file storing the session data.

    Returns
    -------
    ActiveSession | None
        ``ActiveSession`` with runtime information or ``None`` if no session
        exists.
    """
    data = _load_data(session_path)
    if data is None:
        return None
    return PomodoroSession(
        id="",
        goal_id=data.get("goal_id"),
        start=datetime.fromisoformat(data["start"]),
        duration_sec=data["duration_sec"],
    )


def load_active_session(session_path: Path) -> Optional[ActiveSession]:
    """Load the session including elapsed time and pause state.

    Parameters
    ----------
    session_path:
        Path to the JSON file storing the session data.
    """
    data = _load_data(session_path)
    if data is None:
        return None
    raw_last = data.get("last_start")
    last_start = datetime.fromisoformat(raw_last) if raw_last is not None else None
    return ActiveSession(
        goal_id=data.get("goal_id"),
        start=datetime.fromisoformat(data["start"]),
        duration_sec=data["duration_sec"],
        elapsed_sec=data.get("elapsed_sec", 0),
        paused=data.get("paused", False),
        last_start=last_start,
    )


def stop_session(session_path: Path, config_path: Path) -> PomodoroSession:
    """Stop the active timer and trigger any reminder jobs.

    Parameters
    ----------
    session_path:
        Location of the session file to remove.
    config_path:
        Configuration used when scheduling follow-up reminders.

    Returns
    -------
    PomodoroSession
        Representation of the finished session.
    """
    active = load_active_session(session_path)
    if active is None:
        raise RuntimeError("No active session")
    # update elapsed if still running
    if not active.paused and active.last_start is not None:
        now = datetime.now()
        delta = int((now - active.last_start).total_seconds())
        data = _load_data(session_path) or cast(SessionData, {})
        data["elapsed_sec"] = active.elapsed_sec + delta
        _save_data(data, session_path)
    session_path.unlink(missing_ok=True)
    for cb in on_session_end:
        cb(config_path)
    if config.reminders_enabled(config_path):
        console.print(":bell:  Break & interval reminders scheduled.", style="green")
    return PomodoroSession(
        id="",
        goal_id=active.goal_id,
        start=active.start,
        duration_sec=active.duration_sec,
    )


def pause_session(session_path: Path) -> ActiveSession:
    """Pause the running timer and update the elapsed time.

    Parameters
    ----------
    session_path:
        File containing the active session information.

    Returns
    -------
    ActiveSession
        Updated session state reflecting the pause.
    """
    active = load_active_session(session_path)
    if active is None:
        raise RuntimeError("No active session")
    if active.paused:
        raise RuntimeError("Session already paused")
    now = datetime.now()
    delta = int((now - active.last_start).total_seconds()) if active.last_start else 0
    data = _load_data(session_path) or cast(SessionData, {})
    data["elapsed_sec"] = active.elapsed_sec + delta
    data["paused"] = True
    data["last_start"] = None
    _save_data(data, session_path)
    return load_active_session(session_path)  # type: ignore[return-value]


def resume_session(session_path: Path) -> ActiveSession:
    """Resume a previously paused Pomodoro.

    Parameters
    ----------
    session_path:
        File containing the paused session information.

    Returns
    -------
    ActiveSession
        Updated state after the timer has resumed.
    """
    active = load_active_session(session_path)
    if active is None:
        raise RuntimeError("No active session")
    if not active.paused:
        raise RuntimeError("Session is not paused")
    now = datetime.now()
    data = _load_data(session_path) or cast(SessionData, {})
    data["paused"] = False
    data["last_start"] = now.isoformat()
    _save_data(data, session_path)
    return load_active_session(session_path)  # type: ignore[return-value]
