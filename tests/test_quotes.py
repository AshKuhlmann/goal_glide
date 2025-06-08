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


def test_get_random_quote_offline_no_network(monkeypatch: pytest.MonkeyPatch) -> None:
    sample = [{"quote": "L", "author": "A"}]
    monkeypatch.setattr(quotes, "_LOCAL_CACHE", sample)

    def fail(*args: Any, **kwargs: Any) -> None:  # pragma: no cover
        raise AssertionError("network call attempted")

    monkeypatch.setattr(quotes.requests, "get", fail)
    monkeypatch.setattr(quotes.random, "choice", lambda seq: seq[0])
    q, a = quotes.get_random_quote(use_online=False)
    assert (q, a) == ("L", "A")


def test_get_random_quote_uses_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    sample = [{"quote": "C", "author": "B"}]
    monkeypatch.setattr(quotes, "_LOCAL_CACHE", sample)

    def fail() -> list[dict[str, str]]:  # pragma: no cover
        raise AssertionError("_load_local_quotes should not be called")

    monkeypatch.setattr(quotes, "_load_local_quotes", fail)
    monkeypatch.setattr(quotes.random, "choice", lambda seq: seq[0])
    q, a = quotes.get_random_quote(use_online=False)
    assert (q, a) == ("C", "B")


@pytest.mark.parametrize(
    "resp, expect_error",
    [
        (type("Resp", (), {"ok": False})(), False),
        (
            type(
                "Resp",
                (),
                {"ok": True, "json": staticmethod(lambda: [{}])},
            )(),
            True,
        ),
    ],
)
def test_get_random_quote_bad_response(
    monkeypatch: pytest.MonkeyPatch, resp: Any, expect_error: bool
) -> None:
    sample = [{"quote": "F", "author": "B"}]
    monkeypatch.setattr(quotes, "_LOCAL_CACHE", sample)
    monkeypatch.setattr(quotes.random, "choice", lambda seq: seq[0])
    monkeypatch.setattr(quotes.requests, "get", lambda *a, **k: resp)

    if expect_error:
        with pytest.raises(KeyError):
            quotes.get_random_quote()
    else:
        q, a = quotes.get_random_quote()
        assert (q, a) == ("F", "B")


def test_load_local_quotes_invalid_json(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text("{invalid", encoding="utf-8")
    monkeypatch.setattr(quotes, "DATA_PATH", bad)
    with pytest.raises(json.JSONDecodeError):
        quotes._load_local_quotes()


def test_load_local_quotes_not_list(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    bad = tmp_path / "obj.json"
    bad.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(quotes, "DATA_PATH", bad)
    with pytest.raises(AssertionError):
        quotes._load_local_quotes()
