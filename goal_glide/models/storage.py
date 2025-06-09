from __future__ import annotations

from pathlib import Path
from typing import Any, cast
from collections.abc import Mapping

from filelock import FileLock
from tinydb import Query, TinyDB
from tinydb.queries import QueryLike
from tinydb.table import Document

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
    """Manages persistence of goals, sessions and thoughts in TinyDB.

    This class handles all database operations such as creating, reading,
    updating and deleting records. It also performs simple migrations when new
    fields are introduced.

    Attributes:
        db: The underlying :class:`TinyDB` instance.
        table: Table used for storing goals.
        thought_table: Table used for storing thoughts.
        session_table: Table used for storing pomodoro sessions.
    """

    def __init__(self, db_dir: Path | None = None) -> None:
        base = db_dir or Path.home() / ".goal_glide"
        db_path = Path(base) / "db.json"
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self.lock = FileLock(db_path.with_suffix(".lock"))
        with self.lock:
            self.db = TinyDB(db_path, default=str)
        self.table = self.db.table("goals")
        self.thought_table = self.db.table(THOUGHTS_TABLE)
        self.session_table = self.db.table("sessions")

        # Migrate existing rows to include new fields
        # This lock ensures migration happens safely.
        with self.lock:
            for row in self.table.all():
                updated = False
                new_row = dict(row)
                if "tags" not in row:
                    new_row["tags"] = []
                    updated = True
                if "parent_id" not in row:
                    new_row["parent_id"] = None
        if row is None:
                if "deadline" not in row:
                    new_row["deadline"] = None
                    updated = True
                if "completed" not in row:
                    new_row["completed"] = False
                    updated = True
                if updated:
                    self.table.update(new_row, Query().id == row["id"])

    def _row_to_goal(self, row: Document | dict[str, Any]) -> Goal:
        return Goal.from_dict(dict(row))

    def _row_to_thought(self, row: Document | dict[str, Any]) -> Thought:
        return Thought.from_dict(dict(row))

    def _row_to_session(self, row: Document | dict[str, Any]) -> PomodoroSession:
        return PomodoroSession.from_dict(dict(row))

    def _get_goal_no_lock(self, goal_id: str) -> Goal:
        """Retrieves a goal without acquiring the file lock. Assumes lock is held."""
        row = self.table.get(Query().id == goal_id)
        if not row:
            raise GoalNotFoundError(f"Goal {goal_id} not found")
        return self._row_to_goal(row)

    def _update_goal_no_lock(self, goal: Goal) -> None:
        """Updates a goal without acquiring the file lock. Assumes lock is held."""
        if not self.table.contains(Query().id == goal.id):
            raise GoalNotFoundError(f"Goal {goal.id} not found")
        self.table.update(goal.to_dict(), Query().id == goal.id)

    def add_goal(self, goal: Goal) -> None:
        """Saves a new goal to the database.

        Args:
            goal: A :class:`Goal` object to be added to the database.
        """
        with self.lock:
            self.table.insert(goal.to_dict())

    def get_goal(self, goal_id: str) -> Goal:
        with self.lock:
            return self._get_goal_no_lock(goal_id)

    def add_tags(self, goal_id: str, tags: list[str]) -> Goal:
        with self.lock:
            goal = self._get_goal_no_lock(goal_id)
            updated_tags = list({*goal.tags, *tags})
            updated = Goal(
                id=goal.id,
                title=goal.title,
                created=goal.created,
                priority=goal.priority,
                archived=goal.archived,
                tags=sorted(updated_tags),
                parent_id=goal.parent_id,
                deadline=goal.deadline,
                completed=goal.completed,
            )
            self._update_goal_no_lock(updated)
            return updated

    def remove_tag(self, goal_id: str, tag: str) -> Goal:
        with self.lock:
            goal = self._get_goal_no_lock(goal_id)
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
                parent_id=goal.parent_id,
                deadline=goal.deadline,
                completed=goal.completed,
            )
            self._update_goal_no_lock(updated)
            return updated

    def update_goal(self, goal: Goal) -> None:
        with self.lock:
            if not self.table.contains(Query().id == goal.id):
                raise GoalNotFoundError(f"Goal {goal.id} not found")
            self.table.update(goal.to_dict(), Query().id == goal.id)

    def archive_goal(self, goal_id: str) -> Goal:
        with self.lock:
            goal = self._get_goal_no_lock(goal_id)
            if goal.archived:
                raise GoalAlreadyArchivedError(f"Goal {goal_id} already archived")
            updated = Goal(
                id=goal.id,
                title=goal.title,
                created=goal.created,
                priority=goal.priority,
                archived=True,
                tags=goal.tags,
                parent_id=goal.parent_id,
                deadline=goal.deadline,
                completed=goal.completed,
            )
            self._update_goal_no_lock(updated)
            return updated

    def restore_goal(self, goal_id: str) -> Goal:
        with self.lock:
            goal = self._get_goal_no_lock(goal_id)
            if not goal.archived:
                raise GoalNotArchivedError(f"Goal {goal_id} is not archived")
            updated = Goal(
                id=goal.id,
                title=goal.title,
                created=goal.created,
                priority=goal.priority,
                archived=False,
                tags=goal.tags,
                parent_id=goal.parent_id,
                deadline=goal.deadline,
                completed=goal.completed,
            )
            self._update_goal_no_lock(updated)
            return updated

    def complete_goal(self, goal_id: str) -> Goal:
        with self.lock:
            goal = self._get_goal_no_lock(goal_id)
            if goal.completed:
                return goal
            updated = Goal(
                id=goal.id,
                title=goal.title,
                created=goal.created,
                priority=goal.priority,
                archived=goal.archived,
                tags=goal.tags,
                parent_id=goal.parent_id,
                deadline=goal.deadline,
                completed=True,
            )
            self._update_goal_no_lock(updated)
            return updated

    def reopen_goal(self, goal_id: str) -> Goal:
        with self.lock:
            goal = self._get_goal_no_lock(goal_id)
            if not goal.completed:
                return goal
            updated = Goal(
                id=goal.id,
                title=goal.title,
                created=goal.created,
        def predicate(row: Mapping[str, Any]) -> bool:
                archived=goal.archived,
                tags=goal.tags,
                parent_id=goal.parent_id,
                deadline=goal.deadline,
                completed=False,
            )
            self._update_goal_no_lock(updated)
            return updated

    def list_goals(
        self,
        include_archived: bool = False,
        only_archived: bool = False,
        priority: Priority | None = None,
        tags: list[str] | None = None,
        parent_id: str | None = None,
    ) -> list[Goal]:
        """Retrieves goals filtered by various criteria.

        Args:
            include_archived: Whether to include archived goals in the results.
            only_archived: If ``True``, return only archived goals.
            priority: The priority to filter by.
            tags: List of tags goals must contain. All tags are required.
            parent_id: The ID of a parent goal to filter by.

        Returns:
            A list of :class:`Goal` objects matching the filter criteria.
        """
        GoalQuery = Query()
        predicates = []

        if only_archived:
            predicates.append(GoalQuery.archived == True)
        elif not include_archived:
            # Goals created before 'archived' field will not have it.
            predicates.append(GoalQuery.archived != True)

        if priority:
            predicates.append(GoalQuery.priority == priority.value)

        if tags:
            # Using .all() to check for a subset of tags
            predicates.append(GoalQuery.tags.all(tags))

        if parent_id is not None:
            predicates.append(GoalQuery.parent_id == parent_id)

        # Combine all predicates with a logical AND
        final_query = Query()
        for p in predicates:
            final_query = final_query & p

        with self.lock:
            rows = self.table.search(final_query) if predicates else self.table.all()
            return [self._row_to_goal(r) for r in rows]

    def list_all_tags(self) -> dict[str, int]:
        """Return mapping of tag name to count of goals containing it."""
        counts: dict[str, int] = {}
        with self.lock:
            for row in self.table.all():
                for tag in row.get("tags", []):
                    counts[tag] = counts.get(tag, 0) + 1
        return counts

    def remove_goal(self, goal_id: str) -> None:
        with self.lock:
            if not self.table.contains(Query().id == goal_id):
                raise GoalNotFoundError(f"Goal {goal_id} not found")
            self.table.remove(Query().id == goal_id)

    def find_by_title(self, title: str) -> Goal | None:
        with self.lock:
            row = self.table.get(Query().title == title)
            return self._row_to_goal(row) if row else None

    def add_session(self, session: PomodoroSession) -> None:
        with self.lock:
            self.session_table.insert(session.to_dict())

    def list_sessions(self) -> list[PomodoroSession]:
        with self.lock:
            rows = self.session_table.all()
            return [self._row_to_session(r) for r in rows]

    def add_thought(self, thought: Thought) -> None:
        with self.lock:
            self.thought_table.insert(thought.to_dict())

    def list_thoughts(
        self,
        goal_id: str | None = None,
        limit: int | None = 10,
        newest_first: bool = True,
    ) -> list[Thought]:
        ThoughtQuery = Query()
        with self.lock:
            if goal_id is not None:
                db_rows = self.thought_table.search(ThoughtQuery.goal_id == goal_id)
            else:
                db_rows = self.thought_table.all()

            rows = [self._row_to_thought(r) for r in db_rows]
            rows.sort(key=lambda t: t.timestamp, reverse=newest_first)
            if limit is not None:
                rows = rows[:limit]
            return rows

    def remove_thought(self, thought_id: str) -> bool:
        """Delete a thought. Returns True if removed."""
        with self.lock:
            if not self.thought_table.contains(Query().id == thought_id):
                return False
            self.thought_table.remove(Query().id == thought_id)
            return True
