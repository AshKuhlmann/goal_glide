from click.testing import CliRunner
import click
import pytest
import json
from datetime import datetime, timedelta
from rich.table import Table

import goal_glide.cli as cli
from goal_glide import config
from goal_glide.models.storage import Storage
from goal_glide.services import pomodoro


def test_add_list_remove(tmp_path, runner: CliRunner):

    # add goal
    result = runner.invoke(cli.goal, ["add", "Test Goal"])
    assert result.exit_code == 0

    # list
    result = runner.invoke(cli.goal, ["list"])
    assert "Test" in result.output

    # remove using id from storage (rich table may truncate id)
    goal_id = Storage(tmp_path / "db.json").list_goals()[0].id
    result = runner.invoke(
        cli.goal,
        ["remove", goal_id],
        input="y\n",
    )
    assert result.exit_code == 0


def test_add_duplicate_goal_warning(tmp_path, runner: CliRunner) -> None:
    """Adding a goal twice should show a warning message."""
    runner.invoke(cli.goal, ["add", "dup"])
    result = runner.invoke(cli.goal, ["add", "dup"])

    assert result.exit_code == 0
    assert "Warning: goal with this title already exists." in result.output


def test_pomo_session_persisted(tmp_path, monkeypatch, runner: CliRunner):
    import importlib
    importlib.reload(pomodoro)
    res = runner.invoke(cli.goal, ["add", "G"])
    gid = res.output.split()[-1].strip("()")
    runner.invoke(
        cli.goal,
        ["pomo", "start", "--duration", "1", "--goal", gid],
    )
    runner.invoke(cli.goal, ["pomo", "stop"])
    # ensure further pomodoro commands see no active session
    status = runner.invoke(cli.goal, ["pomo", "status"])
    assert "No active session" in status.output
    paused = runner.invoke(cli.goal, ["pomo", "pause"])
    assert paused.exit_code == 1
    storage = Storage(tmp_path / "db.json")
    sessions = storage.list_sessions()
    assert len(sessions) == 1
    assert sessions[0].goal_id == gid


def test_pomo_pause_resume(tmp_path, monkeypatch, runner: CliRunner):
    import importlib
    importlib.reload(pomodoro)
    runner.invoke(cli.goal, ["pomo", "start", "--duration", "1"])
    res = runner.invoke(cli.goal, ["pomo", "pause"])
    assert res.exit_code == 0
    assert "paused" in res.output.lower()
    res = runner.invoke(cli.goal, ["pomo", "resume"])
    assert res.exit_code == 0
    assert "resumed" in res.output.lower()


def test_jot_from_editor(tmp_path, monkeypatch, runner: CliRunner):
    monkeypatch.setattr(click, "edit", lambda *a, **k: "note from editor\n")
    result = runner.invoke(cli.thought, ["jot"])
    assert result.exit_code == 0
    thought_text = Storage(tmp_path / "db.json").list_thoughts()[0].text
    assert thought_text == "note from editor"


@pytest.mark.parametrize("cmd", ["remove", "archive", "update"])
@pytest.mark.parametrize("goal_id", ["", "!!!", "x" * 100])
def test_goal_commands_invalid_id(cmd, goal_id, tmp_path, runner: CliRunner):
    args = [cmd, goal_id]
    if cmd == "remove":
        result = runner.invoke(cli.goal, args, input="y\n")
    else:
        result = runner.invoke(cli.goal, args)
    assert result.exit_code == 1
    assert "Error:" in result.output


def test_jot_from_editor_unicode(tmp_path, monkeypatch, runner: CliRunner):
    monkeypatch.setattr(click, "edit", lambda *a, **k: "Привет мир\n")
    result = runner.invoke(cli.thought, ["jot"])
    assert result.exit_code == 0
    stored = Storage(tmp_path / "db.json").list_thoughts()[0].text
    assert stored == "Привет мир"


def test_jot_from_editor_empty(tmp_path, monkeypatch, runner: CliRunner):
    monkeypatch.setattr(click, "edit", lambda *a, **k: "")
    result = runner.invoke(cli.thought, ["jot"])
    assert result.exit_code == 1
    assert "Error:" in result.output
    assert Storage(tmp_path / "db.json").list_thoughts() == []


def test_config_quotes_disable(tmp_path, monkeypatch, runner: CliRunner):
    cfg_path = tmp_path / "config.toml"
    result = runner.invoke(cli.goal, ["config", "quotes", "--disable"])
    assert result.exit_code == 0
    assert "Quotes are OFF" in result.output
    assert config.quotes_enabled(cfg_path) is False


def test_config_quotes_enable(tmp_path, monkeypatch, runner: CliRunner):
    cfg_path = tmp_path / "config.toml"
    runner.invoke(cli.goal, ["config", "quotes", "--disable"])
    result = runner.invoke(cli.goal, ["config", "quotes", "--enable"])
    assert result.exit_code == 0
    assert "Quotes are ON" in result.output
    assert config.quotes_enabled(cfg_path) is True


def test_pomo_start_after_archive(tmp_path, monkeypatch, runner: CliRunner):
    import importlib
    importlib.reload(pomodoro)
    add_res = runner.invoke(
        cli.goal,
        ["add", "g"],
    )
    gid = add_res.output.split()[-1].strip("()")
    runner.invoke(cli.goal, ["archive", gid])
    start = runner.invoke(
        cli.goal,
        ["pomo", "start", "--duration", "1", "--goal", gid],
    )
    assert start.exit_code == 0
    assert "Started pomodoro" in start.output


def test_pomo_start_default_from_config(tmp_path, monkeypatch, runner: CliRunner):
    import importlib
    importlib.reload(pomodoro)
    monkeypatch.setattr(config, "pomo_duration", lambda path: 2)
    result = runner.invoke(
        cli.goal,
        ["pomo", "start"],
    )
    assert result.exit_code == 0
    data = json.loads((tmp_path / "session.json").read_text())
    assert data["duration_sec"] == 120


def test_list_due_filters(tmp_path, runner: CliRunner):
    soon = (datetime.utcnow() + timedelta(days=2)).strftime("%Y-%m-%d")
    later = (datetime.utcnow() + timedelta(days=5)).strftime("%Y-%m-%d")
    past = (datetime.utcnow() - timedelta(days=1)).strftime("%Y-%m-%d")
    runner.invoke(cli.goal, ["add", "soon", "--deadline", soon])
    runner.invoke(cli.goal, ["add", "later", "--deadline", later])
    runner.invoke(cli.goal, ["add", "past", "--deadline", past])

    res = runner.invoke(cli.goal, ["list", "--due-soon"])
    assert "soon" in res.output
    assert "later" not in res.output
    assert "past" not in res.output

    res = runner.invoke(cli.goal, ["list", "--overdue"])
    assert "past" in res.output
    assert "soon" not in res.output
    assert "later" not in res.output


def test_list_deadline_colors(tmp_path, runner: CliRunner, monkeypatch) -> None:
    """Deadlines should be color coded in ``goal list`` output."""
    past = (datetime.utcnow() - timedelta(days=1)).strftime("%Y-%m-%d")
    near = (datetime.utcnow() + timedelta(days=2)).strftime("%Y-%m-%d")
    future = (datetime.utcnow() + timedelta(days=5)).strftime("%Y-%m-%d")

    runner.invoke(cli.goal, ["add", "past", "--deadline", past])
    runner.invoke(cli.goal, ["add", "near", "--deadline", near])
    runner.invoke(cli.goal, ["add", "future", "--deadline", future])

    printed: list[Table] = []
    monkeypatch.setattr(
        cli.console,
        "print",
        lambda obj, *a, **k: printed.append(obj),
    )

    result = runner.invoke(cli.goal, ["list"])
    assert result.exit_code == 0
    table = printed[0]
    deadlines = table.columns[4]._cells
    assert deadlines[0] == f"[red]{past}[/]"
    assert deadlines[1] == f"[yellow]{near}[/]"
    assert deadlines[2] == future
