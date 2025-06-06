from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable


class Query:
    def __init__(self) -> None:
        self._attr: str | None = None

    def __getattr__(self, item: str) -> "Query":
        self._attr = item
        return self

    def __eq__(self, other: Any) -> Callable[[dict[str, Any]], bool]:  # type: ignore[override]
        attr = self._attr

        def test(row: dict[str, Any]) -> bool:
            if attr is None:
                return False
            return bool(row.get(attr) == other)

        return test


class Table:
    def __init__(self, db: "TinyDB", name: str) -> None:
        self.db = db
        self.name = name
        self.db.data.setdefault(name, [])

    def insert(self, record: dict[str, Any]) -> None:
        self.db.data[self.name].append(record)
        self.db._save()

    def all(self) -> list[dict[str, Any]]:
        return list(self.db.data.get(self.name, []))

    def get(self, predicate: Callable[[dict[str, Any]], bool]) -> dict[str, Any] | None:
        for row in self.db.data.get(self.name, []):
            if predicate(row):
                return row
        return None

    def contains(self, predicate: Callable[[dict[str, Any]], bool]) -> bool:
        return self.get(predicate) is not None

    def search(
        self, predicate: Callable[[dict[str, Any]], bool]
    ) -> list[dict[str, Any]]:
        return [row for row in self.db.data.get(self.name, []) if predicate(row)]

    def remove(self, predicate: Callable[[dict[str, Any]], bool]) -> int:
        rows = self.db.data.get(self.name, [])
        before = len(rows)
        self.db.data[self.name] = [row for row in rows if not predicate(row)]
        self.db._save()
        return before - len(self.db.data[self.name])

    def update(
        self, record: dict[str, Any], predicate: Callable[[dict[str, Any]], bool]
    ) -> None:
        rows = self.db.data.get(self.name, [])
        for idx, row in enumerate(rows):
            if predicate(row):
                rows[idx] = record
                self.db._save()
                return


class TinyDB:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.data: dict[str, list[dict[str, Any]]]
        if self.path.exists():
            self.data = json.loads(self.path.read_text())
        else:
            self.data = {}
        self.data.setdefault("_default", [])

    def table(self, name: str) -> Table:
        return Table(self, name)

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self.data, default=str))
