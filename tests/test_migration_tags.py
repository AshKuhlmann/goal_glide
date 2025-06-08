from __future__ import annotations

from datetime import datetime
from pathlib import Path

from goal_glide.models.storage import Storage
from tinydb import Query, TinyDB


def test_tags_migration(tmp_path: Path) -> None:
    db_path = tmp_path / "db.json"
    db = TinyDB(db_path)
    goals = db.table("goals")
    goals.insert({"id": "g1", "title": "t1", "created": datetime.now().isoformat()})
    goals.insert(
        {
            "id": "g2",
            "title": "t2",
            "created": datetime.now().isoformat(),
            "tags": ["t"],
        }
    )

    storage = Storage(tmp_path)
    goal1 = storage.get_goal("g1")
    goal2 = storage.get_goal("g2")

    assert goal1.tags == []
    assert goal2.tags == ["t"]


def test_tags_migration_updates_db(tmp_path: Path) -> None:
    """Verify migration writes missing tags back to the DB file."""
    db_path = tmp_path / "db.json"
    db = TinyDB(db_path)
    db.table("goals").insert({"id": "g1", "title": "t1", "created": datetime.now().isoformat()})

    storage = Storage(tmp_path)

    db2 = TinyDB(db_path)
    row = db2.table("goals").get(Query().id == "g1")
    assert row["tags"] == []
