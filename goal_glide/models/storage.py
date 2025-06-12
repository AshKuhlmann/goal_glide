from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, TypedDict, cast

from filelock import FileLock
from tinydb import Query, TinyDB
from tinydb.queries import QueryLike

from ..exceptions import (
    GoalAlreadyArchivedError,
    GoalNotArchivedError,
    GoalNotFoundError,
)
from .goal import Goal, Priority
from .session import PomodoroSession
from .thought import TABLE_NAME as THOUGHTS_TABLE
from .thought import Thought


class GoalRow(TypedDict):
    id: str
    title: str
    created: datetime | str
    priority: str
    archived: bool
    tags: list[str]
    phases: list[str]
    parent_id: str | None
    deadline: datetime | str | None
    completed: bool


class ThoughtRow(TypedDict):
    id: str
    text: str
    timestamp: datetime | str
    goal_id: str | None


class SessionRow(TypedDict):
    id: str
    goal_id: str | None
    start: datetime | str
    duration_sec: int


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

    def __init__(self, db_path: Path) -> None:
        self.lock = FileLock(db_path.with_suffix(".lock"))
        with self.lock:
            self.db = TinyDB(db_path, default=str)
        self.table = self.db.table("goals")
        self.thought_table = self.db.table(THOUGHTS_TABLE)
        self.session_table = self.db.table("sessions")

        # migrate existing rows to include new fields
        for row in self.table.all():
            updated = False
            new_row = dict(row)
            if "tags" not in row:
                new_row["tags"] = []
                updated = True
            if "phases" not in row:
                new_row["phases"] = []
                updated = True
            if "parent_id" not in row:
                new_row["parent_id"] = None
                updated = True
            if "deadline" not in row:
                new_row["deadline"] = None
                updated = True
            if "completed" not in row:
                new_row["completed"] = False
                updated = True
            if updated:
                self.table.update(new_row, Query().id == row["id"])

    def _row_to_goal(self, row: GoalRow) -> Goal:
        created = row["created"]
        if isinstance(created, str):
            created_dt = datetime.fromisoformat(created)
        else:
            created_dt = created
        dl = row.get("deadline")
        dl_dt: datetime | None
        if isinstance(dl, str):
            dl_dt = datetime.fromisoformat(dl)
        elif isinstance(dl, datetime):
            dl_dt = dl
        else:
            dl_dt = None
        return Goal(
            id=row["id"],
            title=row["title"],
            created=created_dt,
            priority=Priority(row.get("priority", Priority.medium.value)),
            archived=row.get("archived", False),
            tags=row.get("tags", []),
            phases=row.get("phases", []),
            parent_id=row.get("parent_id"),
            deadline=dl_dt,
            completed=row.get("completed", False),
        )

    def _row_to_thought(self, row: ThoughtRow) -> Thought:
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

    def _row_to_session(self, row: SessionRow) -> PomodoroSession:
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

    def _get_goal_no_lock(self, goal_id: str) -> Goal:
        row = self.table.get(Query().id == goal_id)
        if not row:
            raise GoalNotFoundError(f"Goal {goal_id} not found")
        return self._row_to_goal(cast(GoalRow, row))

    def _update_goal_no_lock(self, goal: Goal) -> None:
        from dataclasses import asdict

        if not self.table.contains(Query().id == goal.id):
            raise GoalNotFoundError(f"Goal {goal.id} not found")
        self.table.update(cast(dict[str, Any], asdict(goal)), Query().id == goal.id)

    def add_goal(self, goal: Goal) -> None:
        """Saves a new goal to the database.

        Args:
            goal: A :class:`Goal` object to be added to the database.
        """

        from dataclasses import asdict

        with self.lock:
            self.table.insert(cast(dict[str, Any], asdict(goal)))

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
                phases=goal.phases,
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
                phases=goal.phases,
                parent_id=goal.parent_id,
                deadline=goal.deadline,
                completed=goal.completed,
            )
            self._update_goal_no_lock(updated)
            return updated

    def add_phases(self, goal_id: str, phases: list[str]) -> Goal:
        with self.lock:
            goal = self._get_goal_no_lock(goal_id)
            updated_phases = list({*goal.phases, *phases})
            updated = Goal(
                id=goal.id,
                title=goal.title,
                created=goal.created,
                priority=goal.priority,
                archived=goal.archived,
                tags=goal.tags,
                phases=sorted(updated_phases),
                parent_id=goal.parent_id,
                deadline=goal.deadline,
                completed=goal.completed,
            )
            self._update_goal_no_lock(updated)
            return updated

    def remove_phase(self, goal_id: str, phase: str) -> Goal:
        with self.lock:
            goal = self._get_goal_no_lock(goal_id)
            if phase not in goal.phases:
                return goal
            new_phases = [p for p in goal.phases if p != phase]
            updated = Goal(
                id=goal.id,
                title=goal.title,
                created=goal.created,
                priority=goal.priority,
                archived=goal.archived,
                tags=goal.tags,
                phases=new_phases,
                parent_id=goal.parent_id,
                deadline=goal.deadline,
                completed=goal.completed,
            )
            self._update_goal_no_lock(updated)
            return updated

    def update_goal(self, goal: Goal) -> None:
        from dataclasses import asdict

        with self.lock:
            if not self.table.contains(Query().id == goal.id):
                raise GoalNotFoundError(f"Goal {goal.id} not found")
            self.table.update(cast(dict[str, Any], asdict(goal)), Query().id == goal.id)

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
                phases=goal.phases,
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
                phases=goal.phases,
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
                phases=goal.phases,
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
                priority=goal.priority,
                archived=goal.archived,
                tags=goal.tags,
                phases=goal.phases,
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
        *,
        due_soon: bool = False,
        overdue: bool = False,
    ) -> list[Goal]:
        """Retrieves goals filtered by various criteria.

        Args:
            include_archived: Whether to include archived goals in the results.
            only_archived: If ``True``, return only archived goals.
            priority: The priority to filter by.
            tags: List of tags goals must contain. All tags are required.
            parent_id: The ID of a parent goal to filter by.
            due_soon: If ``True``, return goals with a deadline in the next
                three days.
            overdue: If ``True``, return goals with a deadline in the past.

        Returns:
            A list of :class:`Goal` objects matching the filter criteria.
        """
        GoalQuery = Query()

        predicates = []

        if only_archived:
            predicates.append(lambda r: r.get("archived") is True)
        elif not include_archived:
            predicates.append(lambda r: not r.get("archived", False))

        if priority:
            predicates.append(GoalQuery.priority == priority.value)

        if tags:
            predicates.append(lambda r: set(tags).issubset(r.get("tags", [])))

        if parent_id is not None:
            predicates.append(GoalQuery.parent_id == parent_id)

        def predicate(row: dict[str, Any]) -> bool:
            row_t = cast(GoalRow, row)
            return all(p(row_t) for p in predicates)

        search_cond = cast(QueryLike, predicate)
        with self.lock:
            rows = self.table.search(search_cond) if predicates else self.table.all()
            goals = [self._row_to_goal(cast(GoalRow, r)) for r in rows]

        if due_soon or overdue:
            now = datetime.utcnow()
            window = timedelta(days=3)
            filtered: list[Goal] = []
            for g in goals:
                if not g.deadline:
                    continue
                if overdue and g.deadline < now:
                    filtered.append(g)
                elif due_soon and now <= g.deadline <= now + window:
                    filtered.append(g)
            goals = filtered

        return goals

    def list_all_tags(self) -> dict[str, int]:
        """Return mapping of tag name to count of goals containing it."""
        counts: dict[str, int] = {}
        with self.lock:
            for row in self.table.all():
                goal_row = cast(GoalRow, row)
                for tag in goal_row.get("tags", []):
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
            return self._row_to_goal(cast(GoalRow, row)) if row else None

    def add_session(self, session: PomodoroSession) -> None:
        from dataclasses import asdict

        with self.lock:
            self.session_table.insert(cast(dict[str, Any], asdict(session)))

    def list_sessions(self) -> list[PomodoroSession]:
        with self.lock:
            rows = self.session_table.all()
            return [self._row_to_session(cast(SessionRow, r)) for r in rows]

    def add_thought(self, thought: Thought) -> None:
        from dataclasses import asdict

        with self.lock:
            self.thought_table.insert(cast(dict[str, Any], asdict(thought)))

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

            rows = [self._row_to_thought(cast(ThoughtRow, r)) for r in db_rows]
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
