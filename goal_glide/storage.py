import os
from pathlib import Path
from typing import Iterable, Optional
from tinydb import TinyDB, Query
from .models import Goal

DB_NAME = 'goal_glide.json'
TABLE_NAME = 'goals'

class Storage:
    def __init__(self, path: Optional[Path] = None):
        env_path = os.environ.get('GOAL_GLIDE_DB')
        self.path = Path(path or env_path or DB_NAME)
        self.db = TinyDB(self.path)
        self.table = self.db.table(TABLE_NAME)

    def add_goal(self, goal: Goal) -> None:
        self.table.insert(goal.__dict__)

    def list_goals(self, *, include_archived: bool = False, archived_only: bool = False,
                   priority: Optional[str] = None) -> Iterable[Goal]:
        q = Query()
        if archived_only:
            cond = q.archived == True
        elif include_archived:
            cond = (q.archived == True) | (q.archived == False)
        else:
            cond = q.archived == False
        results = self.table.search(cond)
        if priority:
            results = [r for r in results if r['priority'] == priority]
        return [Goal(**r) for r in results]

    def remove_goal(self, goal_id: str) -> bool:
        q = Query()
        return bool(self.table.remove(q.id == goal_id))

    def find_by_title(self, title: str) -> Optional[Goal]:
        q = Query()
        r = self.table.get(q.title == title)
        return Goal(**r) if r else None
