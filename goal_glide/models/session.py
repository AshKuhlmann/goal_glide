from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime
from uuid import uuid4
from typing import Any


@dataclass(slots=True, frozen=True)
class PomodoroSession:
    id: str
    goal_id: str | None
    start: datetime
    duration_sec: int

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["start"] = self.start.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PomodoroSession":
        start_val = data["start"]
        if isinstance(start_val, str):
            start_dt = datetime.fromisoformat(start_val)
        else:
            start_dt = start_val
        return cls(
            id=data["id"],
            goal_id=data.get("goal_id"),
            start=start_dt,
            duration_sec=data["duration_sec"],
        )

    @classmethod
    def new(
        cls,
        goal_id: str | None,
        start: datetime,
        duration_sec: int,
    ) -> "PomodoroSession":
        return cls(
            id=str(uuid4()),
            goal_id=goal_id,
            start=start,
            duration_sec=duration_sec,
        )
