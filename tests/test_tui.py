import asyncio
from datetime import datetime

import pytest

from goal_glide.models.goal import Goal
from goal_glide.models.storage import Storage
from goal_glide.services import pomodoro


def _setup_textual() -> bool:
    """Return True if the ``textual`` package can be imported."""
    try:
        import textual  # noqa: F401
    except Exception:
        return False
    return True


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

    storage = Storage(tmp_path / "db.json")
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

    # Pre-populate storage with a goal so we don't rely on interactive input
    storage = Storage(tmp_path / "db.json")
    g = Goal(id="g1", title="goal", created=datetime.utcnow())
    storage.add_goal(g)

    async def run() -> None:
        async with GoalGlideApp().run_test() as pilot:
            await pilot.pause()
            tree = pilot.app.query_one(Tree)
            assert len(tree.root.children) == 1
            pilot.app.selected_goal = g.id
            await pilot.press("delete")
            assert len(tree.root.children) == 0
            assert Storage(tmp_path / "db.json").get_goal(g.id).archived is True

    asyncio.run(run())


def test_update_detail_no_goal(app_env):
    if not _setup_textual():
        pytest.skip("textual not available")
    from textual.widgets import Static
    from goal_glide.tui import GoalGlideApp

    async def run() -> None:
        async with GoalGlideApp().run_test() as pilot:
            await pilot.pause()
            pilot.app.selected_goal = None
            pilot.app.update_detail()
            panel = pilot.app.query_one("#detail_panel", Static)
            assert "No goal selected" in str(panel.renderable)

    asyncio.run(run())


def test_update_detail_with_goal(app_env, tmp_path):
    if not _setup_textual():
        pytest.skip("textual not available")
    from textual.widgets import Static, Tree
    from goal_glide.tui import GoalGlideApp

    storage = Storage(tmp_path / "db.json")
    g = Goal(id="gid", title="Goal A", created=datetime.utcnow())
    storage.add_goal(g)

    async def run() -> None:
        async with GoalGlideApp().run_test() as pilot:
            await pilot.pause()
            tree = pilot.app.query_one(Tree)
            assert len(tree.root.children) == 1
            pilot.app.selected_goal = g.id
            pilot.app.update_detail()
            panel = pilot.app.query_one("#detail_panel", Static)
            assert "Goal A" in str(panel.renderable)
            assert "Priority" in str(panel.renderable)
            assert "Press S to start Pomodoro" in str(panel.renderable)

    asyncio.run(run())


def test_update_detail_deadline_color(app_env, tmp_path):
    if not _setup_textual():
        pytest.skip("textual not available")
    from datetime import timedelta
    from textual.widgets import Static
    from goal_glide.tui import GoalGlideApp

    storage = Storage(tmp_path / "db.json")
    now = datetime.utcnow()
    past = Goal(id="g1", title="Past", created=now, deadline=now - timedelta(days=1))
    soon = Goal(id="g2", title="Soon", created=now, deadline=now + timedelta(days=2))
    storage.add_goal(past)
    storage.add_goal(soon)

    async def run() -> None:
        async with GoalGlideApp().run_test() as pilot:
            await pilot.pause()

            pilot.app.selected_goal = past.id
            pilot.app.update_detail()
            panel = pilot.app.query_one("#detail_panel", Static)
            assert f"Deadline: [red]{past.deadline:%Y-%m-%d}" in str(panel.renderable)

            pilot.app.selected_goal = soon.id
            pilot.app.update_detail()
            panel = pilot.app.query_one("#detail_panel", Static)
            assert f"Deadline: [yellow]{soon.deadline:%Y-%m-%d}" in str(panel.renderable)

    asyncio.run(run())
