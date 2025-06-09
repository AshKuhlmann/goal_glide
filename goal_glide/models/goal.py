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
    completed: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Return a dictionary representation suitable for TinyDB."""
        data = asdict(self)
        data["created"] = self.created.isoformat()
        if self.deadline:
            data["deadline"] = self.deadline.isoformat()
        if isinstance(self.priority, Priority):
            data["priority"] = self.priority.value
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Goal":
        """Create :class:`Goal` from a TinyDB row."""
        created_val = data["created"]
        if isinstance(created_val, str):
            created_dt = datetime.fromisoformat(created_val)
        else:
            created_dt = created_val

        dl_val = data.get("deadline")
        if isinstance(dl_val, str):
            dl_dt = datetime.fromisoformat(dl_val)
        elif isinstance(dl_val, datetime):
            dl_dt = dl_val
        else:
            dl_dt = None

        priority_val = data.get("priority", Priority.medium.value)
        priority_enum = (
            Priority(priority_val)
            if isinstance(priority_val, str)
            else priority_val
        )

        return cls(
            id=data["id"],
            title=data["title"],
            created=created_dt,
            priority=priority_enum,
            archived=data.get("archived", False),
            tags=data.get("tags", []),
            parent_id=data.get("parent_id"),
            deadline=dl_dt,
            completed=data.get("completed", False),
        )
