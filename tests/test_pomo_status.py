import datetime
from pathlib import Path

from click.testing import CliRunner

from goal_glide.cli import cli
from goal_glide.services import pomodoro


def test_status_no_session(tmp_path: Path, monkeypatch, runner: CliRunner):
    env = {"GOAL_GLIDE_DB_DIR": str(tmp_path), "HOME": str(tmp_path)}
    result = runner.invoke(cli, ["pomo", "status"], env=env)
    assert result.exit_code == 0
    assert "No active session" in result.output


def test_status_with_session(tmp_path: Path, monkeypatch, runner: CliRunner):
    env = {"GOAL_GLIDE_DB_DIR": str(tmp_path), "HOME": str(tmp_path)}
    start_time = datetime.datetime(2023, 1, 1, 12, 0, 0)

    class StartDT(datetime.datetime):
        @classmethod
        def now(cls) -> datetime.datetime:  # type: ignore[override]
            return start_time

    monkeypatch.setattr(pomodoro, "datetime", StartDT)
    pomodoro.start_session(
        30,
        session_path=Path(env["GOAL_GLIDE_DB_DIR"]) / "session.json",
        config_path=Path(env["GOAL_GLIDE_DB_DIR"]) / "config.toml",
    )

    later = start_time + datetime.timedelta(minutes=10)

    class LaterDT(datetime.datetime):
        @classmethod
        def now(cls) -> datetime.datetime:  # type: ignore[override]
            return later

    monkeypatch.setattr(pomodoro, "datetime", LaterDT) # Also affects the cli call context
    result = runner.invoke(cli, ["pomo", "status"], env=env)
    assert result.exit_code == 0
    assert "Elapsed 10m" in result.output
    assert "Remaining 20m" in result.output


def test_status_paused(tmp_path: Path, monkeypatch, runner: CliRunner):
    env = {"GOAL_GLIDE_DB_DIR": str(tmp_path), "HOME": str(tmp_path)}
    start_time = datetime.datetime(2023, 1, 1, 12, 0, 0)

    class StartDT(datetime.datetime):
        @classmethod
        def now(cls) -> datetime.datetime:  # type: ignore[override]
            return start_time

    monkeypatch.setattr(pomodoro, "datetime", StartDT)
    pomodoro.start_session(
        30,
        session_path=Path(env["GOAL_GLIDE_DB_DIR"]) / "session.json",
        config_path=Path(env["GOAL_GLIDE_DB_DIR"]) / "config.toml",
    )

    later = start_time + datetime.timedelta(minutes=10)
    dt_cls = type("DT", (datetime.datetime,), {"now": classmethod(lambda cls: later)})
    monkeypatch.setattr(pomodoro, "datetime", dt_cls)
    pomodoro.pause_session(Path(env["GOAL_GLIDE_DB_DIR"]) / "session.json")

    much_later = start_time + datetime.timedelta(minutes=20)

    class LaterDT(datetime.datetime):
        @classmethod
        def now(cls) -> datetime.datetime:  # type: ignore[override]
            return much_later

    monkeypatch.setattr(pomodoro, "datetime", LaterDT) # Also affects the cli call context
    result = runner.invoke(cli, ["pomo", "status"], env=env)
    assert result.exit_code == 0
    assert "Elapsed 10m" in result.output
    assert "Remaining 20m" in result.output
