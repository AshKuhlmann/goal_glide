import os
from pathlib import Path
from typing import Iterable, Optional

from tinydb import Query, Table, TinyDB

from .models.goal import Goal

DB_NAME = "goal_glide.json"
TABLE_NAME = "goals"


class Storage:
    """TinyDB wrapper used by CLI tests."""

    def __init__(self, path: Optional[Path] = None):
        env_dir = os.environ.get("GOAL_GLIDE_DB_DIR")
        if path is not None:
            self.path = Path(path)
        else:
            base = Path(env_dir) if env_dir else Path(".")
            base.mkdir(parents=True, exist_ok=True)
            self.path = base / DB_NAME
        self.db: TinyDB = TinyDB(self.path)
        self.table: Table = self.db.table(TABLE_NAME)

    def add_goal(self, goal: Goal) -> None:
        self.table.insert(goal.__dict__)

    def list_goals(
        self,
        *,
        include_archived: bool = False,
        archived_only: bool = False,
        priority: Optional[str] = None,
    ) -> Iterable[Goal]:
        q = Query()
        if archived_only:
            results = self.table.search(q.archived == True)  # noqa: E712
        elif include_archived:
            results = self.table.all()
        else:
            results = self.table.search(q.archived == False)  # noqa: E712
        if priority:
            results = [r for r in results if r["priority"] == priority]
        return [Goal(**r) for r in results]

    def remove_goal(self, goal_id: str) -> bool:
        q = Query()
        return bool(self.table.remove(q.id == goal_id))

    def find_by_title(self, title: str) -> Optional[Goal]:
        q = Query()
        r = self.table.get(q.title == title)
        return Goal(**r) if r else None
