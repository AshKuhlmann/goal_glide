from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from goal_glide.services import pomodoro


@pytest.fixture()
def session_path(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    path = tmp_path / "session.json"
    monkeypatch.setattr(pomodoro, "POMO_PATH", path)
    return path


def _patch_now(monkeypatch: pytest.MonkeyPatch, when: datetime) -> None:
    class FakeDT(datetime):
        @classmethod
        def now(cls) -> datetime:  # type: ignore[override]
            return when

    monkeypatch.setattr(pomodoro, "datetime", FakeDT)


def test_start_session_writes_file(
    monkeypatch: pytest.MonkeyPatch, session_path: Path
) -> None:
    fake_now = datetime(2023, 1, 1, 12, 0, 0)
    _patch_now(monkeypatch, fake_now)
    session = pomodoro.start_session(1)
    assert isinstance(session, pomodoro.PomodoroSession)
    assert session.start == fake_now
    assert session.duration_sec == 60
    assert session_path.exists()
    data = json.loads(session_path.read_text())
    assert data["start"] == fake_now.isoformat()
    assert data["duration_sec"] == 60


def test_load_session_returns_equivalent(
    monkeypatch: pytest.MonkeyPatch, session_path: Path
) -> None:
    fake_now = datetime(2023, 1, 1, 13, 0, 0)
    _patch_now(monkeypatch, fake_now)
    original = pomodoro.start_session(1)
    loaded = pomodoro.load_session()
    assert loaded == original


def test_stop_session_deletes_file(
    monkeypatch: pytest.MonkeyPatch, session_path: Path
) -> None:
    fake_now = datetime(2023, 1, 1, 14, 0, 0)
    _patch_now(monkeypatch, fake_now)
    original = pomodoro.start_session(1)
    stopped = pomodoro.stop_session()
    assert stopped == original
    assert not session_path.exists()


def test_stop_session_no_file_raises(session_path: Path) -> None:
    with pytest.raises(RuntimeError):
        pomodoro.stop_session()


def test_pause_resume_flow(monkeypatch: pytest.MonkeyPatch, session_path: Path) -> None:
    start = datetime(2023, 1, 2, 9, 0, 0)
    _patch_now(monkeypatch, start)
    pomodoro.start_session(10)

    five = start + timedelta(minutes=5)
    _patch_now(monkeypatch, five)
    paused = pomodoro.pause_session()
    assert paused.paused is True
    data = json.loads(session_path.read_text())
    assert data["elapsed_sec"] == 300

    seven = start + timedelta(minutes=7)
    _patch_now(monkeypatch, seven)
    resumed = pomodoro.resume_session()
    assert resumed.paused is False
    assert json.loads(session_path.read_text())["elapsed_sec"] == 300

    twelve = start + timedelta(minutes=12)
    _patch_now(monkeypatch, twelve)
    pomodoro.stop_session()
