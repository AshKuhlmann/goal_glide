import datetime
from pathlib import Path

from click.testing import CliRunner

from goal_glide import cli
from goal_glide.services import pomodoro


def test_status_no_session(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("GOAL_GLIDE_DB_DIR", str(tmp_path))
    pomodoro.POMO_PATH = tmp_path / "session.json"
    runner = CliRunner()
    result = runner.invoke(cli.goal, ["pomo", "status"])
    assert result.exit_code == 0
    assert "No active session" in result.output


def test_status_with_session(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("GOAL_GLIDE_DB_DIR", str(tmp_path))
    pomodoro.POMO_PATH = tmp_path / "session.json"
    start_time = datetime.datetime(2023, 1, 1, 12, 0, 0)

    class StartDT(datetime.datetime):
        @classmethod
        def now(cls) -> datetime.datetime:  # type: ignore[override]
            return start_time

    monkeypatch.setattr(pomodoro, "datetime", StartDT)
    pomodoro.start_session(30)

    later = start_time + datetime.timedelta(minutes=10)

    class LaterDT(datetime.datetime):
        @classmethod
        def now(cls) -> datetime.datetime:  # type: ignore[override]
            return later

    monkeypatch.setattr(cli, "datetime", LaterDT)
    runner = CliRunner()
    result = runner.invoke(cli.goal, ["pomo", "status"])
    assert result.exit_code == 0
    assert "Elapsed 10m" in result.output
    assert "Remaining 20m" in result.output


def test_status_paused(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("GOAL_GLIDE_DB_DIR", str(tmp_path))
    pomodoro.POMO_PATH = tmp_path / "session.json"
    start_time = datetime.datetime(2023, 1, 1, 12, 0, 0)

    class StartDT(datetime.datetime):
        @classmethod
        def now(cls) -> datetime.datetime:  # type: ignore[override]
            return start_time

    monkeypatch.setattr(pomodoro, "datetime", StartDT)
    pomodoro.start_session(30)

    later = start_time + datetime.timedelta(minutes=10)
    dt_cls = type("DT", (datetime.datetime,), {"now": classmethod(lambda cls: later)})
    monkeypatch.setattr(pomodoro, "datetime", dt_cls)
    pomodoro.pause_session()

    much_later = start_time + datetime.timedelta(minutes=20)

    class LaterDT(datetime.datetime):
        @classmethod
        def now(cls) -> datetime.datetime:  # type: ignore[override]
            return much_later

    monkeypatch.setattr(cli, "datetime", LaterDT)
    runner = CliRunner()
    result = runner.invoke(cli.goal, ["pomo", "status"])
    assert result.exit_code == 0
    assert "Elapsed 10m" in result.output
    assert "Remaining 20m" in result.output
