from __future__ import annotations

from pathlib import Path
from json import JSONDecodeError

import pytest

from goal_glide.models.storage import Storage


def test_corrupt_db_file_raises(tmp_path: Path) -> None:
    db_file = tmp_path / "db.json"
    db_file.write_text("{ bad json")
    with pytest.raises(JSONDecodeError):
        Storage(tmp_path / "db.json")
