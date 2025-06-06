from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from uuid import uuid4

TABLE_NAME = "thoughts"


@dataclass(slots=True, frozen=True)
class Thought:
    id: str
    text: str
    timestamp: datetime
    goal_id: Optional[str] = None

    @classmethod
    def new(cls, text: str, goal_id: str | None) -> "Thought":
        return cls(
            id=str(uuid4()),
            text=text.strip(),
            timestamp=datetime.now(),
            goal_id=goal_id,
        )
