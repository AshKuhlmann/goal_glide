from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

import pytest
from click.testing import CliRunner

from goal_glide.cli import goal, thought
from goal_glide.models.storage import Storage
from goal_glide.models.thought import Thought


@pytest.fixture()
def runner(monkeypatch, tmp_path: Path) -> CliRunner:
    monkeypatch.setenv("GOAL_GLIDE_DB_DIR", str(tmp_path))
    return CliRunner()


def test_jot_basic(tmp_path: Path, runner: CliRunner) -> None:
    result = runner.invoke(thought, ["jot", "note"])
    assert result.exit_code == 0
    storage = Storage(tmp_path)
    thoughts = storage.list_thoughts()
    assert len(thoughts) == 1
    assert thoughts[0].text == "note"
    assert thoughts[0].goal_id is None


def test_jot_with_goal(tmp_path: Path, runner: CliRunner) -> None:
    runner.invoke(goal, ["add", "goal 1"])
    goal_id = Storage(tmp_path).list_goals()[0].id
    result = runner.invoke(thought, ["jot", "idea", "-g", goal_id])
    assert result.exit_code == 0
    t = Storage(tmp_path).list_thoughts()[0]
    assert t.goal_id == goal_id


def test_jot_blank_fails(tmp_path: Path, runner: CliRunner) -> None:
    result = runner.invoke(thought, ["jot", "  "])
    assert result.exit_code != 0
    assert not Storage(tmp_path).list_thoughts()


def test_list_default_order(tmp_path: Path, runner: CliRunner) -> None:
    storage = Storage(tmp_path)
    older = Thought(id="1", text="old", timestamp=datetime.now() - timedelta(hours=1))
    newer = Thought(id="2", text="new", timestamp=datetime.now())
    storage.add_thought(older)
    storage.add_thought(newer)
    result = runner.invoke(thought, ["list"])
    rows = [line for line in result.output.splitlines() if "│" in line]
    assert "new" in rows[0]
    assert "old" in rows[1]


def test_list_limit(tmp_path: Path, runner: CliRunner) -> None:
    storage = Storage(tmp_path)
    for i in range(5):
        storage.add_thought(Thought(id=str(i), text=f"t{i}", timestamp=datetime.now()))
    result = runner.invoke(thought, ["list", "--limit", "3"])
    assert result.exit_code == 0
    rows = [line for line in result.output.splitlines() if "│" in line]
    assert len(rows) <= 3


def test_list_goal_filter(tmp_path: Path, runner: CliRunner) -> None:
    runner.invoke(goal, ["add", "g"])
    goal_id = Storage(tmp_path).list_goals()[0].id
    Storage(tmp_path).add_thought(Thought(id="1", text="a", timestamp=datetime.now()))
    Storage(tmp_path).add_thought(
        Thought(id="2", text="b", timestamp=datetime.now(), goal_id=goal_id)
    )
    result = runner.invoke(thought, ["list", "-g", goal_id])
    rows = [line for line in result.output.splitlines() if "│" in line]
    assert any("b" in r for r in rows)
    assert all(r.split("│")[3].strip() != "a" for r in rows)


def test_migration_keeps_other_tables(tmp_path: Path, runner: CliRunner) -> None:
    # seed pre-existing tables
    db = Storage(tmp_path).db
    db.table("goals").insert({"id": "g"})
    db.table("sessions").insert({"id": "s"})
    Storage(tmp_path).add_thought(Thought(id="t", text="x", timestamp=datetime.now()))
    db2 = Storage(tmp_path).db
    assert len(db2.table("goals").all()) == 1
    assert len(db2.table("sessions").all()) == 1


def test_remove_thought(tmp_path: Path, runner: CliRunner) -> None:
    t = Thought(id="x", text="bye", timestamp=datetime.now())
    Storage(tmp_path).add_thought(t)
    result = runner.invoke(thought, ["rm", "x"])
    assert result.exit_code == 0
    assert not Storage(tmp_path).list_thoughts()


def test_remove_thought_missing(tmp_path: Path, runner: CliRunner) -> None:
    result = runner.invoke(thought, ["rm", "bad"])
    assert result.exit_code == 0
    assert "not found" in result.output
