from click.testing import CliRunner

from goal_glide.cli import cli
from goal_glide.models.storage import Storage
from goal_glide.services import pomodoro


def test_add_list_remove(tmp_path):
    runner = CliRunner()

    # add goal
    result = runner.invoke(
        cli, ["add", "Test Goal"], env={"GOAL_GLIDE_DB_DIR": str(tmp_path)}
    )
    assert result.exit_code == 0

    # list
    result = runner.invoke(cli, ["list"], env={"GOAL_GLIDE_DB_DIR": str(tmp_path)})
    assert "Test Goal" in result.output

    # remove
    # get id from list output
    lines = [line for line in result.output.splitlines() if "Test Goal" in line]
    goal_id = lines[0].split()[0]
    result = runner.invoke(
        cli,
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
    res = runner.invoke(cli, ["add", "G"], env={"GOAL_GLIDE_DB_DIR": str(tmp_path)})
    gid = res.output.split()[-1].strip("()")
    runner.invoke(
        cli,
        ["pomo", "start", "--duration", "1", "--goal", gid],
        env={"GOAL_GLIDE_DB_DIR": str(tmp_path)},
    )
    runner.invoke(
        cli, ["pomo", "stop"], env={"GOAL_GLIDE_DB_DIR": str(tmp_path)}
    )
    storage = Storage(tmp_path)
    sessions = storage.list_sessions()
    assert len(sessions) == 1
    assert sessions[0].goal_id == gid


def test_list_sort_order(tmp_path):
    runner = CliRunner()
    env = {"GOAL_GLIDE_DB_DIR": str(tmp_path)}

    r_high = runner.invoke(cli, ["add", "H", "-p", "high"], env=env)
    high_id = r_high.output.split("(")[-1].strip().strip(")")
    runner.invoke(cli, ["add", "M", "-p", "medium"], env=env)
    runner.invoke(cli, ["add", "L", "-p", "low"], env=env)

    runner.invoke(cli, ["archive", high_id], env=env)

    result = runner.invoke(cli, ["list", "--all"], env=env)
    rows = [line for line in result.output.splitlines() if "|" in line][1:]
    priorities = []
    archived_flags = []
    for row in rows:
        parts = [p.strip() for p in row.split("|")]
        priorities.append(parts[2])
        archived_flags.append(parts[4] == "yes")

    assert priorities == ["medium", "low", "high"]
    assert archived_flags == [False, False, True]
