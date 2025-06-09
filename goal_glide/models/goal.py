from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Optional, Any
from enum import Enum


class Priority(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"


@dataclass(slots=True, frozen=True)
class Goal:
    id: str
    title: str
    created: datetime
    priority: Priority = Priority.medium
    archived: bool = False
    tags: list[str] = field(default_factory=list)
    parent_id: str | None = None
    deadline: Optional[datetime] = None

    def to_dict(self) -> dict[str, Any]:
        """Return a serialisable representation for TinyDB."""
        data = asdict(self)
        data["created"] = self.created.isoformat()
        if self.deadline is not None:
            data["deadline"] = self.deadline.isoformat()
        data["priority"] = self.priority.value
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Goal":
        created = data["created"]
        if isinstance(created, str):
            created_dt = datetime.fromisoformat(created)
        else:
            created_dt = created
        deadline = data.get("deadline")
        if isinstance(deadline, str):
            deadline_dt = datetime.fromisoformat(deadline)
        else:
            deadline_dt = deadline
        priority_val = data.get("priority", Priority.medium.value)
        priority = (
            priority_val
            if isinstance(priority_val, Priority)
            else Priority(priority_val)
        )
        return cls(
            id=data["id"],
            title=data["title"],
            created=created_dt,
            priority=priority,
            archived=data.get("archived", False),
            tags=list(data.get("tags", [])),
            parent_id=data.get("parent_id"),
            deadline=deadline_dt,
        )
