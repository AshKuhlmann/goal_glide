from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional, Any
from uuid import uuid4

TABLE_NAME = "thoughts"


@dataclass(slots=True, frozen=True)
class Thought:
    id: str
    text: str
    timestamp: datetime
    goal_id: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Thought":
        ts = data["timestamp"]
        if isinstance(ts, str):
            ts_dt = datetime.fromisoformat(ts)
        else:
            ts_dt = ts
        return cls(
            id=data["id"],
            text=data["text"],
            timestamp=ts_dt,
            goal_id=data.get("goal_id"),
        )

    @classmethod
    def new(cls, text: str, goal_id: str | None) -> "Thought":
        return cls(
            id=str(uuid4()),
            text=text.strip(),
            timestamp=datetime.now(),
            goal_id=goal_id,
        )
