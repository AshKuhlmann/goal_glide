from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path

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


def test_date_window_week_month_all(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(report, "date", FakeDate)
    start, end = report._date_window("week")
    assert start == date(2023, 6, 12) and end == date(2023, 6, 18)
    start, end = report._date_window("month")
    assert start == date(2023, 5, 1) and end == date(2023, 5, 31)
    start, end = report._date_window("all")
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
