from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import uuid4


@dataclass(slots=True, frozen=True)
class PomodoroSession:
    id: str
    goal_id: str
    start: datetime
    duration_sec: int

    @classmethod
    def new(cls, goal_id: str, start: datetime, duration_sec: int) -> "PomodoroSession":
        return cls(
            id=str(uuid4()), goal_id=goal_id, start=start, duration_sec=duration_sec
        )
