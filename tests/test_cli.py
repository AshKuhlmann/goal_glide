from click.testing import CliRunner

from goal_glide.cli import cli
from goal_glide.storage import DB_NAME


def test_add_list_remove(tmp_path):
    db_path = tmp_path / DB_NAME
    runner = CliRunner()

    # add goal
    result = runner.invoke(
        cli, ["add", "Test Goal"], env={"GOAL_GLIDE_DB": str(db_path)}
    )
    assert result.exit_code == 0

    # list
    result = runner.invoke(cli, ["list"], env={"GOAL_GLIDE_DB": str(db_path)})
    assert "Test Goal" in result.output

    # remove
    # get id from list output
    lines = [line for line in result.output.splitlines() if "Test Goal" in line]
    goal_id = lines[0].split()[0]
    result = runner.invoke(
        cli, ["remove", goal_id], input="y\n", env={"GOAL_GLIDE_DB": str(db_path)}
    )
    assert result.exit_code == 0
