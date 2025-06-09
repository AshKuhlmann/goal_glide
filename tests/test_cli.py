from click.testing import CliRunner
import click
import pytest
import json

import goal_glide.cli as cli
from goal_glide import config
from goal_glide.models.storage import Storage
from goal_glide.services import pomodoro


def test_add_list_remove(tmp_path):
    runner = CliRunner()

    # add goal
    result = runner.invoke(
        cli.goal, ["add", "Test Goal"], env={"GOAL_GLIDE_DB_DIR": str(tmp_path)}
    )
    assert result.exit_code == 0

    # list
    result = runner.invoke(cli.goal, ["list"], env={"GOAL_GLIDE_DB_DIR": str(tmp_path)})
    assert "Test Goal" in result.output

    # remove using id from storage (rich table may truncate id)
    goal_id = Storage(tmp_path).list_goals()[0].id
    result = runner.invoke(
        cli.goal,
        ["remove", goal_id],
        input="y\n",
        env={"GOAL_GLIDE_DB_DIR": str(tmp_path)},
    )
    assert result.exit_code == 0


def test_pomo_session_persisted(tmp_path, monkeypatch):
    monkeypatch.setenv("GOAL_GLIDE_DB_DIR", str(tmp_path))
    monkeypatch.setenv("HOME", str(tmp_path))
    pomodoro.POMO_PATH = tmp_path / "session.json"
    runner = CliRunner()
    res = runner.invoke(
        cli.goal, ["add", "G"], env={"GOAL_GLIDE_DB_DIR": str(tmp_path)}
    )
    gid = res.output.split()[-1].strip("()")
    runner.invoke(
        cli.goal,
        ["pomo", "start", "--duration", "1", "--goal", gid],
        env={"GOAL_GLIDE_DB_DIR": str(tmp_path)},
    )
    runner.invoke(cli.goal, ["pomo", "stop"], env={"GOAL_GLIDE_DB_DIR": str(tmp_path)})
    # ensure further pomodoro commands see no active session
    status = runner.invoke(
        cli.goal,
        ["pomo", "status"],
        env={"GOAL_GLIDE_DB_DIR": str(tmp_path)},
    )
    assert "No active session" in status.output
    paused = runner.invoke(
        cli.goal,
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
    pomodoro.POMO_PATH = tmp_path / "session.json"
    runner = CliRunner()
    runner.invoke(cli.goal, ["pomo", "start", "--duration", "1"])
    res = runner.invoke(cli.goal, ["pomo", "pause"])
    assert res.exit_code == 0
    assert "paused" in res.output.lower()
    res = runner.invoke(cli.goal, ["pomo", "resume"])
    assert res.exit_code == 0
    assert "resumed" in res.output.lower()


def test_jot_from_editor(tmp_path, monkeypatch):
    monkeypatch.setenv("GOAL_GLIDE_DB_DIR", str(tmp_path))
    monkeypatch.setattr(click, "edit", lambda *a, **k: "note from editor\n")
    runner = CliRunner()
    result = runner.invoke(cli.thought, ["jot"])
    assert result.exit_code == 0
    thought_text = Storage(tmp_path).list_thoughts()[0].text
    assert thought_text == "note from editor"


@pytest.mark.parametrize("cmd", ["remove", "archive", "update"])
@pytest.mark.parametrize("goal_id", ["", "!!!", "x" * 100])
def test_goal_commands_invalid_id(cmd, goal_id, tmp_path):
    env = {"GOAL_GLIDE_DB_DIR": str(tmp_path)}
    runner = CliRunner()
    args = [cmd, goal_id]
    if cmd == "remove":
        result = runner.invoke(cli.goal, args, input="y\n", env=env)
    else:
        result = runner.invoke(cli.goal, args, env=env)
    assert result.exit_code == 1
    assert "Error:" in result.output


def test_jot_from_editor_unicode(tmp_path, monkeypatch):
    monkeypatch.setenv("GOAL_GLIDE_DB_DIR", str(tmp_path))
    monkeypatch.setattr(click, "edit", lambda *a, **k: "Привет мир\n")
    runner = CliRunner()
    result = runner.invoke(cli.thought, ["jot"])
    assert result.exit_code == 0
    stored = Storage(tmp_path).list_thoughts()[0].text
    assert stored == "Привет мир"


def test_jot_from_editor_empty(tmp_path, monkeypatch):
    monkeypatch.setenv("GOAL_GLIDE_DB_DIR", str(tmp_path))
    monkeypatch.setattr(click, "edit", lambda *a, **k: "")
    runner = CliRunner()
    result = runner.invoke(cli.thought, ["jot"])
    assert result.exit_code == 1
    assert "Error:" in result.output
    assert Storage(tmp_path).list_thoughts() == []


def test_config_quotes_disable(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "_CONFIG_PATH", tmp_path / "config.toml")
    runner = CliRunner()
    result = runner.invoke(cli.goal, ["config", "quotes", "--disable"])
    assert result.exit_code == 0
    assert "Quotes are OFF" in result.output
    assert config.quotes_enabled() is False


def test_config_quotes_enable(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "_CONFIG_PATH", tmp_path / "config.toml")
    runner = CliRunner()
    runner.invoke(cli.goal, ["config", "quotes", "--disable"])
    result = runner.invoke(cli.goal, ["config", "quotes", "--enable"])
    assert result.exit_code == 0
    assert "Quotes are ON" in result.output
    assert config.quotes_enabled() is True


def test_pomo_start_after_archive(tmp_path, monkeypatch):
    monkeypatch.setenv("GOAL_GLIDE_DB_DIR", str(tmp_path))
    monkeypatch.setenv("HOME", str(tmp_path))
    pomodoro.POMO_PATH = tmp_path / "session.json"
    runner = CliRunner()
    add_res = runner.invoke(
        cli.goal,
        ["add", "g"],
        env={"GOAL_GLIDE_DB_DIR": str(tmp_path)},
    )
    gid = add_res.output.split()[-1].strip("()")
    runner.invoke(cli.goal, ["archive", gid], env={"GOAL_GLIDE_DB_DIR": str(tmp_path)})
    start = runner.invoke(
        cli.goal,
        ["pomo", "start", "--duration", "1", "--goal", gid],
        env={"GOAL_GLIDE_DB_DIR": str(tmp_path)},
    )
    assert start.exit_code == 0
    assert "Started pomodoro" in start.output


def test_pomo_start_default_from_config(tmp_path, monkeypatch):
    monkeypatch.setenv("GOAL_GLIDE_DB_DIR", str(tmp_path))
    monkeypatch.setenv("HOME", str(tmp_path))
    pomodoro.POMO_PATH = tmp_path / "session.json"
    monkeypatch.setattr(config, "pomo_duration", lambda: 2)
    runner = CliRunner()
    result = runner.invoke(cli.goal, ["pomo", "start"], env={"GOAL_GLIDE_DB_DIR": str(tmp_path)})
    assert result.exit_code == 0
    data = json.loads((tmp_path / "session.json").read_text())
    assert data["duration_sec"] == 120
