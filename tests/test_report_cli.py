from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

import pandas as pd

import pytest
from click.testing import CliRunner

from goal_glide import cli
from goal_glide.models.goal import Goal
from goal_glide.models.session import PomodoroSession
from goal_glide.models.storage import Storage
from goal_glide.services import report


@pytest.fixture()
def runner(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> CliRunner:
    monkeypatch.setenv("GOAL_GLIDE_DB_DIR", str(tmp_path))
    return CliRunner()


class FakeDate(date):
    @classmethod
    def today(cls) -> date:  # type: ignore[override]
        return date(2023, 6, 14)


def seed(storage: Storage) -> None:
    storage.add_goal(Goal(id="g", title="A", created=datetime.now()))
    start = datetime.combine(FakeDate.today(), datetime.min.time())
    storage.add_session(
        PomodoroSession(id="s", goal_id="g", start=start, duration_sec=600)
    )


def test_cli_creates_html(
    tmp_path: Path, runner: CliRunner, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(report, "date", FakeDate)
    storage = Storage(tmp_path)
    seed(storage)
    out = tmp_path / "rep.html"
    result = runner.invoke(
        cli.goal,
        ["report", "make", "--out", str(out)],
        env={"GOAL_GLIDE_DB_DIR": str(tmp_path)},
    )
    assert result.exit_code == 0
    assert out.exists()
    assert "Report saved to" in result.output


def test_cli_flag_collision(runner: CliRunner) -> None:
    result = runner.invoke(cli.goal, ["report", "make", "--week", "--month"])
    assert result.exit_code != 0
    assert "only one" in result.output


def test_cli_custom_range(
    tmp_path: Path, runner: CliRunner, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(report, "date", FakeDate)
    storage = Storage(tmp_path)
    seed(storage)
    out = tmp_path / "range.html"
    result = runner.invoke(
        cli.goal,
        [
            "report",
            "make",
            "--from",
            "2023-06-01",
            "--to",
            "2023-06-14",
            "--out",
            str(out),
        ],
        env={"GOAL_GLIDE_DB_DIR": str(tmp_path)},
    )
    assert result.exit_code == 0
    assert out.exists()


@pytest.mark.parametrize(
    "flag, expected",
    [
        ("--week", "week"),
        ("--month", "month"),
        ("--all", "all"),
    ],
)
def test_cli_range_flags(
    tmp_path: Path,
    runner: CliRunner,
    monkeypatch: pytest.MonkeyPatch,
    flag: str,
    expected: str,
) -> None:
    captured: list[str] = []

    def fake_build_report(
        storage: Storage,
        range_: str,
        fmt: str,
        out_path: Path | None,
        start: date | None = None,
        end: date | None = None,
    ) -> Path:
        captured.append(range_)
        out = tmp_path / "dummy.html"
        out.write_text("", encoding="utf-8")
        return out

    monkeypatch.setattr(report, "build_report", fake_build_report)
    result = runner.invoke(
        cli.goal,
        ["report", "make", flag],
        env={"GOAL_GLIDE_DB_DIR": str(tmp_path)},
    )
    assert result.exit_code == 0
    assert captured == [expected]


@pytest.mark.parametrize(
    "args, msg",
    [
        (["--from", "2023-01-01"], "Specify both --from and --to"),
        (["--to", "2023-01-01"], "Specify both --from and --to"),
        (
            ["--week", "--from", "2023-01-01", "--to", "2023-01-07"],
            "--from/--to cannot be combined with range flags",
        ),
    ],
)
def test_report_make_usage_errors(runner: CliRunner, args: list[str], msg: str) -> None:
    result = runner.invoke(cli.goal, ["report", "make", *args])
    assert result.exit_code != 0
    assert msg in result.output


def test_cli_default_output_path(
    tmp_path: Path, runner: CliRunner, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.setattr(report, "date", FakeDate)
    storage = Storage(tmp_path)
    seed(storage)
    result = runner.invoke(
        cli.goal,
        ["report", "make", "--week"],
        env={"GOAL_GLIDE_DB_DIR": str(tmp_path)},
    )
    assert result.exit_code == 0
    assert list(tmp_path.glob("GoalGlide_week_*"))


def test_cli_md_and_csv(
    tmp_path: Path,
    runner: CliRunner,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(report, "date", FakeDate)
    storage = Storage(tmp_path)
    seed(storage)
    md_out = tmp_path / "rep.md"
    csv_out = tmp_path / "rep.csv"
    result_md = runner.invoke(
        cli.goal,
        ["report", "make", "--format", "md", "--out", str(md_out)],
        env={"GOAL_GLIDE_DB_DIR": str(tmp_path)},
    )
    result_csv = runner.invoke(
        cli.goal,
        ["report", "make", "--format", "csv", "--out", str(csv_out)],
        env={"GOAL_GLIDE_DB_DIR": str(tmp_path)},
    )
    assert result_md.exit_code == 0
    assert result_csv.exit_code == 0
    md_text = md_out.read_text()
    assert "  \n" in md_text
    assert "<br>" not in md_text
    df = pd.read_csv(csv_out)
    assert list(df.columns) == ["goal_id", "title", "total_sec", "tags"]


def test_cli_empty_storage_reports(
    tmp_path: Path,
    runner: CliRunner,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(report, "date", FakeDate)
    Storage(tmp_path)  # initialize empty storage
    md_out = tmp_path / "empty.md"
    csv_out = tmp_path / "empty.csv"
    result_md = runner.invoke(
        cli.goal,
        ["report", "make", "--format", "md", "--out", str(md_out)],
        env={"GOAL_GLIDE_DB_DIR": str(tmp_path)},
    )
    result_csv = runner.invoke(
        cli.goal,
        ["report", "make", "--format", "csv", "--out", str(csv_out)],
        env={"GOAL_GLIDE_DB_DIR": str(tmp_path)},
    )
    assert result_md.exit_code == 0
    assert result_csv.exit_code == 0
    assert md_out.exists()
    assert csv_out.exists()
    assert "0:00" in md_out.read_text()
    assert csv_out.read_text().strip() == ""
