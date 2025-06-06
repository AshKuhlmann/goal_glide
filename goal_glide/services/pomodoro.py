from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

from rich.console import Console

from .. import config

console = Console()

on_new_session: list[Callable[[], None]] = []
on_session_end: list[Callable[[], None]] = []

POMO_PATH = Path.home() / ".goal_glide" / "session.json"


@dataclass(slots=True)
class PomodoroSession:
    start: datetime
    duration_sec: int


def start_session(duration_min: int = 25) -> PomodoroSession:
    session = PomodoroSession(start=datetime.now(), duration_sec=duration_min * 60)
    POMO_PATH.parent.mkdir(parents=True, exist_ok=True)
    with POMO_PATH.open("w", encoding="utf-8") as fp:
        json.dump(
            {"start": session.start.isoformat(), "duration_sec": session.duration_sec},
            fp,
        )
    for cb in on_new_session:
        cb()
    return session


def load_session() -> Optional[PomodoroSession]:
    if not POMO_PATH.exists():
        return None
    with POMO_PATH.open(encoding="utf-8") as fp:
        data = json.load(fp)
    return PomodoroSession(
        start=datetime.fromisoformat(data["start"]), duration_sec=data["duration_sec"]
    )


def stop_session() -> PomodoroSession:
    session = load_session()
    if session is None:
        raise RuntimeError("No active session")
    POMO_PATH.unlink(missing_ok=True)
    for cb in on_session_end:
        cb()
    if config.reminders_enabled():
        console.print(":bell:  Break & interval reminders scheduled.", style="green")
    return session
