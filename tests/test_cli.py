from click.testing import CliRunner
import click
import pytest
import json
from datetime import datetime, timedelta

from goal_glide.cli import cli
from goal_glide import config
from goal_glide.models.storage import Storage
from goal_glide.services import pomodoro


def test_add_list_remove(tmp_path):
    runner = CliRunner()

    # add goal
    result = runner.invoke(
        cli, ["goal", "add", "Test Goal"], env={"GOAL_GLIDE_DB_DIR": str(tmp_path)}
    )
    assert result.exit_code == 0

    env = {"GOAL_GLIDE_DB_DIR": str(tmp_path)}
    # list
    result = runner.invoke(cli, ["goal", "list"], env=env)
    assert "Test" in result.output

    # remove using id from storage (rich table may truncate id)
    goal_id = Storage(tmp_path).list_goals()[0].id
    result = runner.invoke(
        cli,
        ["goal", "remove", goal_id],
        input="y\n",
        env=env,
    )
    assert result.exit_code == 0


def test_pomo_session_persisted(tmp_path, monkeypatch):
    monkeypatch.setenv("GOAL_GLIDE_DB_DIR", str(tmp_path))
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("GOAL_GLIDE_SESSION_FILE", str(tmp_path / "session.json"))
    import importlib
    importlib.reload(pomodoro)
    runner = CliRunner()
    res = runner.invoke(
        cli, ["goal", "add", "G"], env={"GOAL_GLIDE_DB_DIR": str(tmp_path)}
    )
    gid = res.output.split()[-1].strip("()")
    runner.invoke(
        cli,
        ["pomo", "start", "--duration", "1", "--goal", gid],
        env={"GOAL_GLIDE_DB_DIR": str(tmp_path)},
    )
    runner.invoke(cli, ["pomo", "stop"], env={"GOAL_GLIDE_DB_DIR": str(tmp_path)})
    # ensure further pomodoro commands see no active session
    status = runner.invoke(
        cli,
        ["pomo", "status"],
        env={"GOAL_GLIDE_DB_DIR": str(tmp_path)},
    )
    assert "No active session" in status.output
    paused = runner.invoke(
        cli,
        ["pomo", "pause"],
        env={"GOAL_GLIDE_DB_DIR": str(tmp_path)},
    )
    assert paused.exit_code == 1
    storage = Storage(tmp_path)
    sessions = storage.list_sessions()
    assert len(sessions) == 1
    assert sessions[0].goal_id == gid


def test_pomo_pause_resume(tmp_path, monkeypatch):
    monkeypatch.setenv("GOAL_GLIDE_DB_DIR", str(tmp_path))
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("GOAL_GLIDE_SESSION_FILE", str(tmp_path / "session.json"))
    import importlib
    importlib.reload(pomodoro)
    runner = CliRunner()
    runner.invoke(cli, ["pomo", "start", "--duration", "1"])
    res = runner.invoke(cli, ["pomo", "pause"])
    assert res.exit_code == 0
    assert "paused" in res.output.lower()
    res = runner.invoke(cli, ["pomo", "resume"])
    assert res.exit_code == 0
    assert "resumed" in res.output.lower()


def test_jot_from_editor(tmp_path, monkeypatch):
    monkeypatch.setenv("GOAL_GLIDE_DB_DIR", str(tmp_path))
    monkeypatch.setattr(click, "edit", lambda *a, **k: "note from editor\n")
    runner = CliRunner()
    result = runner.invoke(cli, ["thought", "jot"])
    assert result.exit_code == 0
    thought_text = Storage(tmp_path).list_thoughts()[0].text
    assert thought_text == "note from editor"


@pytest.mark.parametrize("cmd", ["remove", "archive", "update"])
@pytest.mark.parametrize("goal_id", ["", "!!!", "x" * 100])
def test_goal_commands_invalid_id(cmd, goal_id, tmp_path):
    env = {"GOAL_GLIDE_DB_DIR": str(tmp_path)}
    runner = CliRunner()
    args = ["goal", cmd, goal_id]
    if cmd == "remove":
        result = runner.invoke(cli, args, input="y\n", env=env)
    else:
        result = runner.invoke(cli, args, env=env)
    assert result.exit_code == 1
    assert "Error:" in result.output


def test_jot_from_editor_unicode(tmp_path, monkeypatch):
    monkeypatch.setenv("GOAL_GLIDE_DB_DIR", str(tmp_path))
    monkeypatch.setattr(click, "edit", lambda *a, **k: "Привет мир\n")
    runner = CliRunner()
    result = runner.invoke(cli, ["thought", "jot"])
    assert result.exit_code == 0
    stored = Storage(tmp_path).list_thoughts()[0].text
    assert stored == "Привет мир"


def test_jot_from_editor_empty(tmp_path, monkeypatch):
    monkeypatch.setenv("GOAL_GLIDE_DB_DIR", str(tmp_path))
    monkeypatch.setattr(click, "edit", lambda *a, **k: "")
    runner = CliRunner()
    result = runner.invoke(cli, ["thought", "jot"])
    assert result.exit_code == 1
    assert "Error:" in result.output
    assert Storage(tmp_path).list_thoughts() == []


def test_config_quotes_disable(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "_CONFIG_PATH", tmp_path / "config.toml")
    runner = CliRunner()
    result = runner.invoke(cli, ["config", "quotes", "--disable"])
    assert result.exit_code == 0
    assert "Quotes are OFF" in result.output
    assert config.quotes_enabled() is False


def test_config_quotes_enable(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "_CONFIG_PATH", tmp_path / "config.toml")
    runner = CliRunner()
    runner.invoke(cli, ["config", "quotes", "--disable"])
    result = runner.invoke(cli, ["config", "quotes", "--enable"])
    assert result.exit_code == 0
    assert "Quotes are ON" in result.output
    assert config.quotes_enabled() is True


def test_pomo_start_after_archive(tmp_path, monkeypatch):
    monkeypatch.setenv("GOAL_GLIDE_DB_DIR", str(tmp_path))
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("GOAL_GLIDE_SESSION_FILE", str(tmp_path / "session.json"))
    import importlib
    importlib.reload(pomodoro)
    runner = CliRunner()
    env = {"GOAL_GLIDE_DB_DIR": str(tmp_path)}
    add_res = runner.invoke(
        cli,
        ["goal", "add", "g"],
        env=env,
    )
    gid = add_res.output.split()[-1].strip("()")
    runner.invoke(cli, ["goal", "archive", gid], env=env)
    start = runner.invoke(
        cli,
        ["pomo", "start", "--duration", "1", "--goal", gid],
        env=env,
    )
    assert start.exit_code == 0
    assert "Started pomodoro" in start.output


def test_pomo_start_default_from_config(tmp_path, monkeypatch):
    monkeypatch.setenv("GOAL_GLIDE_DB_DIR", str(tmp_path))
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("GOAL_GLIDE_SESSION_FILE", str(tmp_path / "session.json"))
    import importlib
    importlib.reload(pomodoro)
    monkeypatch.setattr(config, "pomo_duration", lambda: 2)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["pomo", "start"],
        env={"GOAL_GLIDE_DB_DIR": str(tmp_path)},
    )
    assert result.exit_code == 0
    data = json.loads((tmp_path / "session.json").read_text())
    assert data["duration_sec"] == 120


def test_list_due_filters(tmp_path):
    env = {"GOAL_GLIDE_DB_DIR": str(tmp_path)}
    runner = CliRunner()
    soon = (datetime.utcnow() + timedelta(days=2)).strftime("%Y-%m-%d")
    later = (datetime.utcnow() + timedelta(days=5)).strftime("%Y-%m-%d")
    past = (datetime.utcnow() - timedelta(days=1)).strftime("%Y-%m-%d")
    runner.invoke(cli, ["goal", "add", "soon", "--deadline", soon], env=env)
    runner.invoke(cli, ["goal", "add", "later", "--deadline", later], env=env)
    runner.invoke(cli, ["goal", "add", "past", "--deadline", past], env=env)

    res = runner.invoke(cli, ["goal", "list", "--due-soon"], env=env)
    assert "soon" in res.output
    assert "later" not in res.output
    assert "past" not in res.output

    res = runner.invoke(cli, ["goal", "list", "--overdue"], env=env)
    assert "past" in res.output
    assert "soon" not in res.output
    assert "later" not in res.output
