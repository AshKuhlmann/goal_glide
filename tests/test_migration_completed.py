from datetime import datetime
from pathlib import Path
from tinydb import TinyDB, Query
from goal_glide.models.storage import Storage


def test_completed_migration(tmp_path: Path) -> None:
    db_path = tmp_path / "db.json"
    db = TinyDB(db_path)
    db.table("goals").insert(
        {"id": "g1", "title": "t", "created": datetime.now().isoformat()}
    )
    Storage(tmp_path / "db.json")
    row = TinyDB(db_path).table("goals").get(Query().id == "g1")
    assert row["completed"] is False
