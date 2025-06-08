from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path
from bs4 import BeautifulSoup

import pandas as pd
import pytest

from goal_glide.models.goal import Goal
from goal_glide.models.session import PomodoroSession
from goal_glide.models.storage import Storage
from goal_glide.services import report


class FakeDate(date):
    @classmethod
    def today(cls) -> date:  # type: ignore[override]
        return date(2023, 6, 14)


def seed(storage: Storage) -> None:
    g1 = Goal(id="g1", title="A", created=datetime(2023, 6, 1), tags=["work"])
    g2 = Goal(id="g2", title="B", created=datetime(2023, 6, 1), tags=["play"])
    g3 = Goal(id="g3", title="C", created=datetime(2023, 6, 1), tags=["work"])
    for g in (g1, g2, g3):
        storage.add_goal(g)
    week_start = FakeDate.today() - timedelta(days=FakeDate.today().weekday())
    storage.add_session(
        PomodoroSession(
            id="s1",
            goal_id="g1",
            start=datetime.combine(week_start, datetime.min.time()),
            duration_sec=600,
        )
    )
    storage.add_session(
        PomodoroSession(
            id="s2",
            goal_id="g2",
            start=datetime.combine(week_start + timedelta(days=1), datetime.min.time()),
            duration_sec=1200,
        )
    )
    storage.add_session(
        PomodoroSession(
            id="s3",
            goal_id="g3",
            start=datetime.combine(week_start + timedelta(days=2), datetime.min.time()),
            duration_sec=1800,
        )
    )


def seed_many(storage: Storage) -> None:
    week_start = FakeDate.today() - timedelta(days=FakeDate.today().weekday())
    durations = [600, 1200, 1800, 2400, 3000, 3600]
    for i, dur in enumerate(durations, start=1):
        gid = f"g{i}"
        storage.add_goal(Goal(id=gid, title=f"G{i}", created=datetime(2023, 6, 1)))
        storage.add_session(
            PomodoroSession(
                id=f"s{i}",
                goal_id=gid,
                start=datetime.combine(week_start + timedelta(days=i - 1), datetime.min.time()),
                duration_sec=dur,
            )
        )


def test_date_window_week_month_all(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(report, "date", FakeDate)
    start, end = report._date_window("week")
    assert start == date(2023, 6, 12) and end == date(2023, 6, 18)
    start, end = report._date_window("month")
    assert start == date(2023, 5, 1) and end == date(2023, 5, 31)
    start, end = report._date_window("all")
    assert start == date.min and end == FakeDate.today()


@pytest.mark.parametrize(
    "today,week_start,week_end,month_start,month_end",
    [
        (
            date(2023, 1, 1),
            date(2022, 12, 26),
            date(2023, 1, 1),
            date(2022, 12, 1),
            date(2022, 12, 31),
        ),
        (
            date(2023, 12, 31),
            date(2023, 12, 25),
            date(2023, 12, 31),
            date(2023, 11, 1),
            date(2023, 11, 30),
        ),
        (
            date(2023, 6, 1),
            date(2023, 5, 29),
            date(2023, 6, 4),
            date(2023, 5, 1),
            date(2023, 5, 31),
        ),
    ],
)
def test_date_window_edge_cases(
    monkeypatch: pytest.MonkeyPatch,
    today: date,
    week_start: date,
    week_end: date,
    month_start: date,
    month_end: date,
) -> None:
    class EdgeDate(date):
        @classmethod
        def today(cls) -> date:  # type: ignore[override]
            return today

    monkeypatch.setattr(report, "date", EdgeDate)
    start, end = report._date_window("week")
    assert (start, end) == (week_start, week_end)
    start, end = report._date_window("month")
    assert (start, end) == (month_start, month_end)


def test_date_window_unknown_range(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(report, "date", FakeDate)
    start, end = report._date_window("unknown")  # type: ignore[arg-type]
    assert start == date.min and end == FakeDate.today()


def test_csv_output_rows_and_headers(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(report, "date", FakeDate)
    storage = Storage(tmp_path)
    seed(storage)
    out = report.build_report(storage, "week", "csv", tmp_path / "r.csv")
    df = pd.read_csv(out)
    assert list(df.columns) == ["goal_id", "title", "total_sec", "tags"]
    assert len(df) == 3


def test_html_contains_sections(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(report, "date", FakeDate)
    storage = Storage(tmp_path)
    seed(storage)
    out = report.build_report(storage, "week", "html", tmp_path / "r.html")
    text = out.read_text()
    assert "Total Focus Time" in text
    assert "Top Goals" in text
    assert "Histogram" in text
    assert "Most Productive Day" in text


def test_markdown_formatting(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(report, "date", FakeDate)
    storage = Storage(tmp_path)
    seed(storage)
    out = report.build_report(storage, "week", "md", tmp_path / "r.md")
    text = out.read_text()
    assert "  \n" in text
    assert "<br>" not in text


def test_empty_storage_outputs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(report, "date", FakeDate)
    storage = Storage(tmp_path)
    html = report.build_report(storage, "week", "html", tmp_path / "e.html")
    csv = report.build_report(storage, "week", "csv", tmp_path / "e.csv")
    md = report.build_report(storage, "week", "md", tmp_path / "e.md")
    assert html.exists()
    assert csv.exists()
    assert md.exists()
    html_text = html.read_text()
    md_text = md.read_text()
    csv_text = csv.read_text()
    assert "0:00" in html_text
    assert "0:00" in md_text
    assert "0" in html_text
    assert "0" in md_text
    assert csv_text.strip() == ""


def test_custom_range_skips_date_window(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(report, "date", FakeDate)
    storage = Storage(tmp_path)
    seed(storage)

    def boom(*args: object, **kwargs: object) -> None:
        raise AssertionError("_date_window should not be called")

    monkeypatch.setattr(report, "_date_window", boom)

    start = date(2023, 6, 12)
    end = date(2023, 6, 14)
    out = report.build_report(
        storage, "week", "html", tmp_path / "out.html", start=start, end=end
    )
    text = out.read_text()
    assert f"Period: {start} - {end}" in text


def test_html_top_goals_limit_and_order(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(report, "date", FakeDate)
    storage = Storage(tmp_path)
    seed_many(storage)
    out = report.build_report(storage, "week", "html", tmp_path / "top.html")
    soup = BeautifulSoup(out.read_text(), "html.parser")
    table = soup.find("h2", string="Top Goals").find_next("table")
    rows = table.find_all("tr")[1:]
    assert len(rows) == 5
    secs = [int(r.find_all("td")[1].text) for r in rows]
    assert secs == sorted(secs, reverse=True)
