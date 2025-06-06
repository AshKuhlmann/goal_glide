from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
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
