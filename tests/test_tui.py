import asyncio
from datetime import datetime

import pytest

from goal_glide.models.goal import Goal
from goal_glide.models.storage import Storage
from goal_glide.services import pomodoro


def _setup_textual() -> bool:
    return False


@pytest.fixture()
def app_env(monkeypatch, tmp_path):
    monkeypatch.setenv("GOAL_GLIDE_DB_DIR", str(tmp_path))
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("GOAL_GLIDE_SESSION_FILE", str(tmp_path / "session.json"))
    import importlib
    importlib.reload(pomodoro)
    yield


def test_launch_and_quit(app_env):
    if not _setup_textual():
        pytest.skip("textual not available")
    from goal_glide.tui import GoalGlideApp

    async def run() -> None:
        async with GoalGlideApp().run_test() as pilot:
            await pilot.press("q")
            assert not pilot.app.is_running

    asyncio.run(run())


def test_toggle_pomo(app_env, tmp_path):
    if not _setup_textual():
        pytest.skip("textual not available")
    from goal_glide.tui import GoalGlideApp

    storage = Storage(tmp_path)
    g = Goal(id="g1", title="g", created=datetime.utcnow())
    storage.add_goal(g)

    async def run() -> None:
        async with GoalGlideApp().run_test() as pilot:
            pilot.app.selected_goal = g.id
            await pilot.pause()
            await pilot.press("s")
            assert pilot.app.active_session is not None
            await pilot.press("s")
            assert pilot.app.active_session is None

    asyncio.run(run())


def test_add_and_archive_goal(app_env, tmp_path):
    if not _setup_textual():
        pytest.skip("textual not available")
    from textual.widgets import Tree
    from goal_glide.tui import GoalGlideApp

    async def run() -> None:
        async with GoalGlideApp().run_test() as pilot:
            await pilot.pause()
            await pilot.press("a")
            await pilot.press(*"new goal", "enter")
            await pilot.press("enter")
            await pilot.press("enter")
            tree = pilot.app.query_one(Tree)
            goals = Storage(tmp_path).list_goals()
            assert len(tree.root.children) == 1
            gid = goals[0].id
            pilot.app.selected_goal = gid
            await pilot.press("delete")
            assert len(tree.root.children) == 0
            assert Storage(tmp_path).get_goal(gid).archived is True

    asyncio.run(run())
