from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from tinydb import Query, TinyDB

from ..exceptions import (
    GoalAlreadyArchivedError,
    GoalNotArchivedError,
    GoalNotFoundError,
)
from .goal import Goal, Priority
from .session import PomodoroSession
from .thought import TABLE_NAME as THOUGHTS_TABLE
from .thought import Thought


class Storage:
    def __init__(self, db_dir: Path | None = None) -> None:
        base = db_dir or Path.home() / ".goal_glide"
        db_path = Path(base) / "db.json"
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self.db = TinyDB(db_path)
        self.table = self.db.table("goals")
        self.thought_table = self.db.table(THOUGHTS_TABLE)
        self.session_table = self.db.table("sessions")

        # migrate existing rows to include tags field
        for row in self.table.all():
            if "tags" not in row:
                new_row = dict(row)
                new_row["tags"] = []
                self.table.update(new_row, Query().id == row["id"])

    def _row_to_goal(self, row: dict[str, Any]) -> Goal:
        created = row["created"]
        if isinstance(created, str):
            created_dt = datetime.fromisoformat(created)
        else:
            created_dt = created
        return Goal(
            id=row["id"],
            title=row["title"],
            created=created_dt,
            priority=Priority(row.get("priority", Priority.medium.value)),
            archived=row.get("archived", False),
            tags=row.get("tags", []),
        )

    def _row_to_thought(self, row: dict[str, Any]) -> Thought:
        ts = row["timestamp"]
        if isinstance(ts, str):
            ts_dt = datetime.fromisoformat(ts)
        else:
            ts_dt = ts
        return Thought(
            id=row["id"],
            text=row["text"],
            timestamp=ts_dt,
            goal_id=row.get("goal_id"),
        )

    def _row_to_session(self, row: dict[str, Any]) -> PomodoroSession:
        st = row["start"]
        if isinstance(st, str):
            st_dt = datetime.fromisoformat(st)
        else:
            st_dt = st
        return PomodoroSession(
            id=row["id"],
            goal_id=row.get("goal_id"),
            start=st_dt,
            duration_sec=row["duration_sec"],
        )

    def add_goal(self, goal: Goal) -> None:
        from dataclasses import asdict

        self.table.insert(asdict(goal))

    def get_goal(self, goal_id: str) -> Goal:
        row = self.table.get(Query().id == goal_id)
        if not row:
            raise GoalNotFoundError(f"Goal {goal_id} not found")
        return self._row_to_goal(row)

    def add_tags(self, goal_id: str, tags: list[str]) -> Goal:
        goal = self.get_goal(goal_id)
        updated_tags = list({*goal.tags, *tags})
        updated = Goal(
            id=goal.id,
            title=goal.title,
            created=goal.created,
            priority=goal.priority,
            archived=goal.archived,
            tags=sorted(updated_tags),
        )
        self.update_goal(updated)
        return updated

    def remove_tag(self, goal_id: str, tag: str) -> Goal:
        goal = self.get_goal(goal_id)
        if tag not in goal.tags:
            return goal
        new_tags = [t for t in goal.tags if t != tag]
        updated = Goal(
            id=goal.id,
            title=goal.title,
            created=goal.created,
            priority=goal.priority,
            archived=goal.archived,
            tags=new_tags,
        )
        self.update_goal(updated)
        return updated

    def update_goal(self, goal: Goal) -> None:
        from dataclasses import asdict

        if not self.table.contains(Query().id == goal.id):
            raise GoalNotFoundError(f"Goal {goal.id} not found")
        self.table.update(asdict(goal), Query().id == goal.id)

    def archive_goal(self, goal_id: str) -> Goal:
        goal = self.get_goal(goal_id)
        if goal.archived:
            raise GoalAlreadyArchivedError(f"Goal {goal_id} already archived")
        updated = Goal(
            id=goal.id,
            title=goal.title,
            created=goal.created,
            priority=goal.priority,
            archived=True,
            tags=goal.tags,
        )
        self.update_goal(updated)
        return updated

    def restore_goal(self, goal_id: str) -> Goal:
        goal = self.get_goal(goal_id)
        if not goal.archived:
            raise GoalNotArchivedError(f"Goal {goal_id} is not archived")
        updated = Goal(
            id=goal.id,
            title=goal.title,
            created=goal.created,
            priority=goal.priority,
            archived=False,
            tags=goal.tags,
        )
        self.update_goal(updated)
        return updated

    def list_goals(
        self,
        include_archived: bool = False,
        only_archived: bool = False,
        priority: Priority | None = None,
        tags: list[str] | None = None,
    ) -> list[Goal]:
        results = []
        for row in self.table.all():
            g = self._row_to_goal(row)
            if only_archived and not g.archived:
                continue
            if not include_archived and not only_archived and g.archived:
                continue
            if priority and g.priority != priority:
                continue
            if tags and not set(tags).issubset(g.tags):
                continue
            results.append(g)
        return results

    def list_all_tags(self) -> dict[str, int]:
        """Return mapping of tag name to count of goals containing it."""
        counts: dict[str, int] = {}
        for row in self.table.all():
            for tag in row.get("tags", []):
                counts[tag] = counts.get(tag, 0) + 1
        return counts

    def remove_goal(self, goal_id: str) -> None:
        if not self.table.contains(Query().id == goal_id):
            raise GoalNotFoundError(f"Goal {goal_id} not found")
        self.table.remove(Query().id == goal_id)

    def find_by_title(self, title: str) -> Goal | None:
        row = self.table.get(Query().title == title)
        return self._row_to_goal(row) if row else None

    def add_session(self, session: PomodoroSession) -> None:
        from dataclasses import asdict

        self.session_table.insert(asdict(session))

    def list_sessions(self) -> list[PomodoroSession]:
        return [self._row_to_session(r) for r in self.session_table.all()]

    def add_thought(self, thought: Thought) -> None:
        from dataclasses import asdict

        self.thought_table.insert(asdict(thought))

    def list_thoughts(
        self,
        goal_id: str | None = None,
        limit: int | None = 10,
        newest_first: bool = True,
    ) -> list[Thought]:
        rows = [self._row_to_thought(r) for r in self.thought_table.all()]
        if goal_id is not None:
            rows = [t for t in rows if t.goal_id == goal_id]
        rows.sort(key=lambda t: t.timestamp, reverse=newest_first)
        if limit is not None:
            rows = rows[:limit]
        return rows

    def remove_thought(self, thought_id: str) -> bool:
        """Delete a thought. Returns True if removed."""
        if not self.thought_table.contains(Query().id == thought_id):
            return False
        self.thought_table.remove(Query().id == thought_id)
        return True
