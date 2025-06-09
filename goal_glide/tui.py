from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from uuid import uuid4
from pathlib import Path
import os
from rich.text import Text


from textual.app import App, ComposeResult
from textual.containers import Vertical
from textual.reactive import reactive
from textual.screen import ModalScreen
from textual.widgets import (
    Tree,
    Footer,
    Header,
    Static,
    Input,
    Button,
)
from textual.widgets.tree import TreeNode

from .cli import get_storage
from .models.goal import Goal, Priority
from .models.session import PomodoroSession
from .models.thought import Thought
from .services import pomodoro
from .services.analytics import total_time_by_goal


@dataclass(slots=True)
class RunningSession:
    goal_id: str
    start: datetime
    duration_sec: int


class InputModal(ModalScreen[str]):
    """Simple modal to capture a line of text."""

    def __init__(self, prompt: str, default: str = "") -> None:
        super().__init__()
        self.prompt = prompt
        self.default = default

    def compose(self) -> ComposeResult:
        yield Vertical(
            Static(self.prompt),
            Input(value=self.default, id="input"),
            Button("OK", id="ok"),
            id="modal",
        )

    async def on_mount(self) -> None:
        self.query_one(Input).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        value = self.query_one(Input).value
        self.dismiss(value)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self.dismiss(event.value)


class GoalGlideApp(App[None]):
    CSS_PATH = "tui.css"
    BINDINGS = [
        ("a", "add_goal", "Add Goal"),
        ("delete", "archive_goal", "Archive"),
        ("s", "toggle_pomo", "Start/Stop"),
        ("t", "jot_thought", "Thought"),
        ("e", "edit_goal", "Edit"),
        ("q", "quit", "Quit"),
    ]

    active_session: reactive[RunningSession | None] = reactive(None)
    selected_goal: reactive[str | None] = reactive(None)

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Tree("Goals", id="goal_tree")
        yield Static(id="detail_panel")
        yield Footer()

    async def on_mount(self) -> None:
        self.storage = get_storage()
        await self.refresh_goals()
        self.set_interval(1.0, self._tick)
        tree = self.query_one(Tree)
        tree.focus()

    async def refresh_goals(self) -> None:
        tree = self.query_one(Tree)
        tree.root.remove_children()
        goals = list(self.storage.list_goals())
        children: dict[str, list[Goal]] = {}
        roots: list[Goal] = []
        for g in goals:
            if g.parent_id:
                children.setdefault(g.parent_id, []).append(g)
            else:
                roots.append(g)
        for lst in children.values():
            lst.sort(key=lambda g: g.created)
        roots.sort(key=lambda g: g.created)

        def add_nodes(node: TreeNode, goal: Goal) -> None:
            label = goal.title
            if goal.deadline:
                now = datetime.utcnow()
                if goal.deadline < now:
                    label = f"[red]{goal.title}[/]"
                elif goal.deadline - now <= timedelta(days=3):
                    label = f"[yellow]{goal.title}[/]"
            branch = node.add(label, goal.id)
            for child in children.get(goal.id, []):
                add_nodes(branch, child)

        for g in roots:
            add_nodes(tree.root, g)
        tree.root.expand()

    async def on_tree_node_highlighted(self, event: Tree.NodeHighlighted[str]) -> None:
        self.selected_goal = event.node.data
        self.update_detail()

    def update_detail(self) -> None:
        panel = self.query_one("#detail_panel", Static)
        if not self.selected_goal:
            panel.update("No goal selected")
            return
        goal = self.storage.get_goal(self.selected_goal)
        lines = [
            f"[b]{goal.title}[/b]",
            f"Priority: {goal.priority.value}",
            f"Created: {goal.created:%Y-%m-%d}",
        ]
        if goal.deadline:
            now = datetime.utcnow()
            date_str = f"{goal.deadline:%Y-%m-%d}"
            if goal.deadline < now:
                lines.append(f"Deadline: [red]{date_str}[/]")
            elif goal.deadline - now <= timedelta(days=3):
                lines.append(f"Deadline: [yellow]{date_str}[/]")
            else:
                lines.append(f"Deadline: {date_str}")
        focus_totals = total_time_by_goal(self.storage)
        if goal.id in focus_totals:
            mins = focus_totals[goal.id] // 60
            lines.append(f"Focus: {mins}m")
        if goal.tags:
            lines.append(f"Tags: {', '.join(goal.tags)}")
        thoughts = self.storage.list_thoughts(goal.id, limit=5)
        if thoughts:
            lines.append("Thoughts:")
            for t in thoughts:
                lines.append(f"- {t.text}")
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
        panel.update(Text("\n".join(lines)))

    async def action_add_goal(self) -> None:  # pragma: no cover - interactive
        title = await self.push_screen(InputModal("Goal title:"), wait_for_dismiss=True)
        if not title or not str(title).strip():
            return
        title = str(title).strip()

        prio = await self.push_screen(
            InputModal(
                "Priority (low/medium/high):",
                default=Priority.medium.value,
            ),
            wait_for_dismiss=True,
        )
        prio_str = str(prio).strip() if prio else Priority.medium.value
        try:
            priority = Priority(prio_str) if prio_str else Priority.medium
        except Exception:
            priority = Priority.medium

        dl = await self.push_screen(
            InputModal("Deadline YYYY-MM-DD (optional):"), wait_for_dismiss=True
        )
        deadline = None
        if dl and str(dl).strip():
            try:
                deadline = datetime.strptime(str(dl).strip(), "%Y-%m-%d")
            except Exception:
                deadline = None

        g = Goal(
            id=str(uuid4()),
            title=title,
            created=datetime.utcnow(),
            priority=priority,
            deadline=deadline,
        )
        self.storage.add_goal(g)
        await self.refresh_goals()

    async def action_archive_goal(self) -> None:  # pragma: no cover - interactive
        if not self.selected_goal:
            return
        self.storage.archive_goal(self.selected_goal)
        await self.refresh_goals()

    async def action_edit_goal(self) -> None:  # pragma: no cover - interactive
        if not self.selected_goal:
            return
        goal = self.storage.get_goal(self.selected_goal)
        new_title = await self.push_screen(
            InputModal("Edit title:", default=goal.title),
            wait_for_dismiss=True,
        )
        if not new_title:
            new_title = goal.title
        new_prio = await self.push_screen(
            InputModal("Priority (low/medium/high):", default=goal.priority.value),
            wait_for_dismiss=True,
        )
        try:
            priority = Priority(str(new_prio).strip()) if new_prio else goal.priority
        except Exception:
            priority = goal.priority
        updated = Goal(
            id=goal.id,
            title=str(new_title).strip() or goal.title,
            created=goal.created,
            priority=priority,
            archived=goal.archived,
            tags=goal.tags,
            parent_id=goal.parent_id,
            deadline=goal.deadline,
            completed=goal.completed,
        )
        self.storage.update_goal(updated)
        await self.refresh_goals()

    async def action_jot_thought(self) -> None:  # pragma: no cover - interactive
        text = await self.push_screen(InputModal("Thought:"), wait_for_dismiss=True)
        if not text or not str(text).strip():
            return
        thought = Thought.new(str(text).strip(), self.selected_goal)
        self.storage.add_thought(thought)

    async def action_toggle_pomo(self) -> None:
        if not self.selected_goal:
            return
        if self.active_session and self.active_session.goal_id == self.selected_goal:
            base = Path(
                os.environ.get("GOAL_GLIDE_DB_DIR") or Path.home() / ".goal_glide"
            )
            pomodoro.stop_session(base / "session.json", base / "config.toml")
            self.storage.add_session(
                PomodoroSession.new(
                    self.selected_goal,
                    self.active_session.start,
                    self.active_session.duration_sec,
                )
            )
            self.active_session = None
        else:
            base = Path(
                os.environ.get("GOAL_GLIDE_DB_DIR") or Path.home() / ".goal_glide"
            )
            session = pomodoro.start_session(
                session_path=base / "session.json", config_path=base / "config.toml"
            )
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
