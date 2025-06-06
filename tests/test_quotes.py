from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from goal_glide.services import quotes


def test_local_file_has_many_quotes() -> None:
    data = json.loads(Path(quotes.DATA_PATH).read_text(encoding="utf-8"))
    assert len(data) >= 200


def test_get_random_quote_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    sample = [{"quote": "Local", "author": "A"}]
    monkeypatch.setattr(quotes, "_LOCAL_CACHE", None)
    monkeypatch.setattr(quotes, "_load_local_quotes", lambda: sample)
    monkeypatch.setattr(quotes.random, "choice", lambda seq: seq[0])
    monkeypatch.setattr(
        quotes.requests,
        "get",
        lambda *a, **k: (_ for _ in ()).throw(quotes.requests.RequestException()),
    )
    q, a = quotes.get_random_quote()
    assert (q, a) == ("Local", "A")


def test_get_random_quote_online(monkeypatch: pytest.MonkeyPatch) -> None:
    class Resp:
        ok = True

        @staticmethod
        def json() -> list[dict[str, Any]]:
            return [{"q": "Net", "a": "B"}]

    monkeypatch.setattr(quotes.requests, "get", lambda *a, **k: Resp())
    q, a = quotes.get_random_quote()
    assert (q, a) == ("Net", "B")
