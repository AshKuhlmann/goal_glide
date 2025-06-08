import os
import pytest
import sys
import asyncio
from datetime import datetime, timedelta


from pathlib import Path


def import_app():
    root = str(Path(__file__).resolve().parents[1])
    if root in sys.path:
        sys.path.remove(root)
        sys.path.append(root)
    if "" in sys.path:
        sys.path.remove("")
        sys.path.append("")
    for key in list(sys.modules):
        if key == "rich" or key.startswith("rich."):
            del sys.modules[key]
        if key == "textual" or key.startswith("textual."):
            del sys.modules[key]
    if os.environ.get("DEBUG_IMPORT"):
        print("sys.path", sys.path[:5])
    import importlib
    importlib.invalidate_caches()
    try:
        from goal_glide.tui import GoalGlideApp, RunningSession
    except Exception:
        return None, None
    # Replace reactive descriptors with simple attributes for testing
    GoalGlideApp.selected_goal = None
    GoalGlideApp.active_session = None
    return GoalGlideApp, RunningSession


from goal_glide.models.goal import Goal, Priority
from goal_glide.models.session import PomodoroSession
from goal_glide.services import pomodoro


class DummyStatic:
    def __init__(self) -> None:
        self.content = ""

    def update(self, text: str) -> None:
        self.content = text


class DummyTable:
    def __init__(self) -> None:
        self.rows: list[tuple[tuple[str, str, str, str], str | None]] = []
        self.cursor_type: str | None = None
        self.cursor_coordinate = None

    def add_columns(self, *cols: str) -> None:
        pass

    def clear(self) -> None:
        self.rows.clear()

    def add_row(self, *values: str, key: str | None = None) -> None:
        self.rows.append((values, key))

    @property
    def row_count(self) -> int:  # pragma: no cover - simple property
        return len(self.rows)

    def focus(self) -> None:  # pragma: no cover - no behaviour
        pass


class DummyStorage:
    def __init__(self, goals: list[Goal]):
        self.goals = {g.id: g for g in goals}
        self.sessions: list[PomodoroSession] = []

    def list_goals(self):
        return list(self.goals.values())

    def get_goal(self, gid: str) -> Goal:
        return self.goals[gid]

    def add_session(self, session: PomodoroSession) -> None:
        self.sessions.append(session)

    def archive_goal(self, gid: str) -> None:  # pragma: no cover - not used
        self.goals[gid].archived = True


def make_app(goals: list[Goal]):
    GoalGlideApp, _ = import_app()
    app = object.__new__(GoalGlideApp)
    storage = DummyStorage(goals)
    table = DummyTable()
    panel = DummyStatic()

    def query_one(selector: str, *_, **__):
        if selector == "#detail_panel" or selector == "Static":
            return panel
        return table

    app.storage = storage
    app.query_one = query_one
    return app, storage, table, panel


def test_refresh_goals_populates_table():
    GoalGlideApp, _ = import_app()
    if GoalGlideApp is None:
        pytest.skip("textual not available")
    goals = [Goal(id="g1", title="G1", created=datetime.utcnow(), priority=Priority.low)]
    app, _, table, _ = make_app(goals)
    asyncio.run(app.refresh_goals())
    assert table.row_count == 1
    assert table.rows[0][1] == "g1"


def test_update_detail_with_active_session():
    GoalGlideApp, RunningSession = import_app()
    if GoalGlideApp is None:
        pytest.skip("textual not available")
    goal = Goal(id="g1", title="My Goal", created=datetime.utcnow())
    app, _, _, panel = make_app([goal])
    app.__dict__["selected_goal"] = "g1"
    app.__dict__["active_session"] = RunningSession(
        goal_id="g1",
        start=datetime.utcnow() - timedelta(seconds=30),
        duration_sec=60,
    )
    app.update_detail()
    assert "My Goal" in panel.content
    assert "Press S" not in panel.content
    assert "[" in panel.content and "]" in panel.content


def test_action_toggle_pomo_start_stop(monkeypatch):
    GoalGlideApp, RunningSession = import_app()
    if GoalGlideApp is None:
        pytest.skip("textual not available")
    goal = Goal(id="g1", title="G1", created=datetime.utcnow())
    app, storage, _, _ = make_app([goal])
    app.__dict__["selected_goal"] = "g1"

    fake_session = PomodoroSession.new("g1", datetime.utcnow(), 60)
    monkeypatch.setattr(pomodoro, "start_session", lambda: fake_session)
    monkeypatch.setattr(pomodoro, "stop_session", lambda: fake_session)

    asyncio.run(app.action_toggle_pomo())
    assert app.active_session.goal_id == "g1"
    asyncio.run(app.action_toggle_pomo())
    assert app.active_session is None
    assert storage.sessions and storage.sessions[0].goal_id == "g1"
