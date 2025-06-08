from __future__ import annotations

import sys
from dataclasses import dataclass
from datetime import datetime
from uuid import uuid4

# ensure real rich is used (textual dependency)
if "" in sys.path:
    sys.path.remove("")
    sys.path.append("")

from textual.app import App, ComposeResult
from textual.coordinate import Coordinate
from textual.reactive import reactive
from textual.widgets import DataTable, Footer, Header, Static

from .cli import get_storage
from .models.goal import Goal, Priority
from .models.session import PomodoroSession
from .models.thought import Thought
from .services import pomodoro


@dataclass(slots=True)
class RunningSession:
    goal_id: str
    start: datetime
    duration_sec: int


class GoalGlideApp(App[None]):
    CSS_PATH = "tui.css"
    BINDINGS = [
        ("a", "add_goal", "Add Goal"),
        ("delete", "archive_goal", "Archive"),
        ("s", "toggle_pomo", "Start/Stop"),
        ("t", "jot_thought", "Thought"),
        ("q", "quit", "Quit"),
    ]

    active_session: reactive[RunningSession | None] = reactive(None)
    selected_goal: reactive[str | None] = reactive(None)

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield DataTable(id="goal_table")
        yield Static(id="detail_panel")
        yield Footer()

    async def on_mount(self) -> None:
        self.storage = get_storage()
        table = self.query_one(DataTable)
        table.add_columns("ID", "Title", "Pri.", "Tags")
        await self.refresh_goals()
        self.set_interval(1.0, self._tick)
        table.focus()

    async def refresh_goals(self) -> None:
        table = self.query_one(DataTable)
        table.clear()
        goals = list(self.storage.list_goals())
        for g in goals:
            table.add_row(g.id, g.title, g.priority.value, ", ".join(g.tags), key=g.id)
        if goals:
            table.cursor_type = "row"
            table.cursor_coordinate = Coordinate(0, 0)

    async def on_data_table_row_highlighted(
        self, event: DataTable.RowHighlighted
    ) -> None:
        self.selected_goal = str(event.row_key)
        self.update_detail()

    def update_detail(self) -> None:
        panel = self.query_one("#detail_panel", Static)
        if not self.selected_goal:
            panel.update("No goal selected")
            return
        goal = self.storage.get_goal(self.selected_goal)
        lines = [f"[b]{goal.title}[/b]", f"Priority: {goal.priority.value}"]
        if goal.tags:
            lines.append(f"Tags: {', '.join(goal.tags)}")
        if self.active_session and self.active_session.goal_id == goal.id:
            elapsed = int((datetime.now() - self.active_session.start).total_seconds())
            remaining = max(self.active_session.duration_sec - elapsed, 0)
            bar_len = 20
            filled = int(elapsed / self.active_session.duration_sec * bar_len)
            bar = "#" * filled + "-" * (bar_len - filled)
            mins, sec = divmod(remaining, 60)
            lines.append(f"[{bar}] {mins:02}:{sec:02}")
        else:
            lines.append("Press S to start Pomodoro")
        panel.update("\n".join(lines))

    async def action_add_goal(self) -> None:  # pragma: no cover - interactive
        title = input("Goal title: ").strip()
        if not title:
            return
        g = Goal(
            id=str(uuid4()),
            title=title,
            created=datetime.utcnow(),
            priority=Priority.medium,
        )
        self.storage.add_goal(g)
        await self.refresh_goals()

    async def action_archive_goal(self) -> None:  # pragma: no cover - interactive
        if not self.selected_goal:
            return
        self.storage.archive_goal(self.selected_goal)
        await self.refresh_goals()

    async def action_jot_thought(self) -> None:  # pragma: no cover - interactive
        text = input("Thought: ").strip()
        if not text:
            return
        thought = Thought.new(text, self.selected_goal)
        self.storage.add_thought(thought)

    async def action_toggle_pomo(self) -> None:
        if not self.selected_goal:
            return
        if self.active_session and self.active_session.goal_id == self.selected_goal:
            pomodoro.stop_session()
            self.storage.add_session(
                PomodoroSession.new(
                    self.selected_goal,
                    self.active_session.start,
                    self.active_session.duration_sec,
                )
            )
            self.active_session = None
        else:
            session = pomodoro.start_session()
            self.active_session = RunningSession(
                goal_id=self.selected_goal,
                start=session.start,
                duration_sec=session.duration_sec,
            )
        self.update_detail()

    async def action_quit(self) -> None:
        self.exit()

    def _tick(self) -> None:
        if self.active_session:
            self.update_detail()


def run() -> None:
    GoalGlideApp().run()


__all__ = ["run", "GoalGlideApp"]

if __name__ == "__main__":  # pragma: no cover
    run()
