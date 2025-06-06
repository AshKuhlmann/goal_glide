from dataclasses import dataclass
from datetime import datetime


@dataclass
class Goal:
    id: str
    title: str
    created: datetime
    priority: str = "medium"
    archived: bool = False
