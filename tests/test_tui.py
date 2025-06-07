import asyncio
import sys
from datetime import datetime

import pytest

from goal_glide.models.goal import Goal
from goal_glide.models.storage import Storage
from goal_glide.services import pomodoro


def _setup_textual() -> object | None:
    if "" in sys.path:
        sys.path.remove("")
        sys.path.append("")
    for key in list(sys.modules):
        if key == "rich" or key.startswith("rich."):
            del sys.modules[key]
    try:
        from textual.pilot import Pilot
    except Exception:  # pragma: no cover - textual not installed
        return None
    return Pilot


@pytest.fixture()
def app_env(monkeypatch, tmp_path):
    monkeypatch.setenv("GOAL_GLIDE_DB_DIR", str(tmp_path))
    monkeypatch.setenv("HOME", str(tmp_path))
    pomodoro.POMO_PATH = tmp_path / "session.json"
    yield


def test_launch_and_quit(app_env):
    Pilot = _setup_textual()
    if Pilot is None:
        pytest.skip("textual not available")
    from goal_glide.tui import GoalGlideApp

    async def run() -> None:
        async with Pilot(GoalGlideApp) as pilot:
            await pilot.press("q")
            assert pilot.app.is_closed

    asyncio.run(run())


def test_toggle_pomo(app_env, tmp_path):
    Pilot = _setup_textual()
    if Pilot is None:
        pytest.skip("textual not available")
    from goal_glide.tui import GoalGlideApp

    storage = Storage(tmp_path)
    g = Goal(id="g1", title="g", created=datetime.utcnow())
    storage.add_goal(g)

    async def run() -> None:
        async with Pilot(GoalGlideApp) as pilot:
            await pilot.pause()
            await pilot.press("s")
            assert pilot.app.active_session is not None
            await pilot.press("s")
            assert pilot.app.active_session is None

    asyncio.run(run())


def test_add_and_archive_goal(app_env, tmp_path, monkeypatch):
    Pilot = _setup_textual()
    if Pilot is None:
        pytest.skip("textual not available")
    from textual.widgets import DataTable
    from goal_glide.tui import GoalGlideApp

    monkeypatch.setattr("builtins.input", lambda *args: "new goal")

    async def run() -> None:
        async with Pilot(GoalGlideApp) as pilot:
            await pilot.pause()
            await pilot.press("a")
            table = pilot.app.query_one(DataTable)
            goals = Storage(tmp_path).list_goals()
            assert table.row_count == 1
            gid = goals[0].id
            await pilot.press("delete")
            assert table.row_count == 0
            assert Storage(tmp_path).get_goal(gid).archived is True

    asyncio.run(run())
