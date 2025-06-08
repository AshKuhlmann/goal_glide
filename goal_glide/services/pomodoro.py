from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional, TypedDict, cast

from rich.console import Console

from .. import config
from ..models.session import PomodoroSession

console = Console()

on_new_session: list[Callable[[], None]] = []
on_session_end: list[Callable[[], None]] = []

POMO_PATH = Path.home() / ".goal_glide" / "session.json"


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


def _load_data() -> SessionData | None:
    if not POMO_PATH.exists():
        return None
    with POMO_PATH.open(encoding="utf-8") as fp:
        data = cast(SessionData, json.load(fp))
    # backward compatibility for older session files
    data.setdefault("elapsed_sec", 0)
    data.setdefault("paused", False)
    data.setdefault("last_start", data.get("start"))
    return data


def _save_data(data: SessionData) -> None:
    POMO_PATH.parent.mkdir(parents=True, exist_ok=True)
    with POMO_PATH.open("w", encoding="utf-8") as fp:
        json.dump(data, fp)


def start_session(
    duration_min: int = 25,
    goal_id: str | None = None,
) -> PomodoroSession:
    session = PomodoroSession(
        id="",
        goal_id=goal_id,
        start=datetime.now(),
        duration_sec=duration_min * 60,
    )
    data: SessionData = {
        "start": session.start.isoformat(),
        "duration_sec": session.duration_sec,
        "goal_id": session.goal_id,
        "elapsed_sec": 0,
        "paused": False,
        "last_start": session.start.isoformat(),
    }
    _save_data(data)
    for cb in on_new_session:
        cb()
    return session


def load_session() -> Optional[PomodoroSession]:
    data = _load_data()
    if data is None:
        return None
    return PomodoroSession(
        id="",
        goal_id=data.get("goal_id"),
        start=datetime.fromisoformat(data["start"]),
        duration_sec=data["duration_sec"],
    )


def load_active_session() -> Optional[ActiveSession]:
    data = _load_data()
    if data is None:
        return None
    last_start = (
        datetime.fromisoformat(data["last_start"])
        if data.get("last_start")
        else None
    )
    return ActiveSession(
        goal_id=data.get("goal_id"),
        start=datetime.fromisoformat(data["start"]),
        duration_sec=data["duration_sec"],
        elapsed_sec=data.get("elapsed_sec", 0),
        paused=data.get("paused", False),
        last_start=last_start,
    )


def stop_session() -> PomodoroSession:
    active = load_active_session()
    if active is None:
        raise RuntimeError("No active session")
    # update elapsed if still running
    if not active.paused and active.last_start is not None:
        now = datetime.now()
        delta = int((now - active.last_start).total_seconds())
        data = _load_data() or cast(SessionData, {})
        data["elapsed_sec"] = active.elapsed_sec + delta
        _save_data(data)
    POMO_PATH.unlink(missing_ok=True)
    for cb in on_session_end:
        cb()
    if config.reminders_enabled():
        console.print(":bell:  Break & interval reminders scheduled.", style="green")
    return PomodoroSession(
        id="",
        goal_id=active.goal_id,
        start=active.start,
        duration_sec=active.duration_sec,
    )


def pause_session() -> ActiveSession:
    active = load_active_session()
    if active is None:
        raise RuntimeError("No active session")
    if active.paused:
        raise RuntimeError("Session already paused")
    now = datetime.now()
    delta = int((now - active.last_start).total_seconds()) if active.last_start else 0
    data = _load_data() or cast(SessionData, {})
    data["elapsed_sec"] = active.elapsed_sec + delta
    data["paused"] = True
    data["last_start"] = None
    _save_data(data)
    return load_active_session()  # type: ignore[return-value]


def resume_session() -> ActiveSession:
    active = load_active_session()
    if active is None:
        raise RuntimeError("No active session")
    if not active.paused:
        raise RuntimeError("Session is not paused")
    now = datetime.now()
    data = _load_data() or cast(SessionData, {})
    data["paused"] = False
    data["last_start"] = now.isoformat()
    _save_data(data)
    return load_active_session()  # type: ignore[return-value]
