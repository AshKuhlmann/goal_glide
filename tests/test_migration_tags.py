from __future__ import annotations

from datetime import datetime
from pathlib import Path

from goal_glide.models.storage import Storage
from tinydb import TinyDB


def test_migrate_adds_empty_tags(tmp_path: Path) -> None:
    db_path = tmp_path / "db.json"
    db = TinyDB(db_path)
    goals = db.table("goals")
    goals.insert({"id": "g1", "title": "t", "created": datetime.now().isoformat()})

    storage = Storage(tmp_path)
    goal = storage.get_goal("g1")
    assert goal.tags == []


def test_migrate_keeps_existing_tags(tmp_path: Path) -> None:
    db_path = tmp_path / "db.json"
    db = TinyDB(db_path)
    goals = db.table("goals")
    goals.insert(
        {
            "id": "g1",
            "title": "t",
            "created": datetime.now().isoformat(),
            "tags": ["a"],
        }
    )

    storage = Storage(tmp_path)
    goal = storage.get_goal("g1")
    assert goal.tags == ["a"]
