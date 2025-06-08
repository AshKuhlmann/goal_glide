from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Literal

import pandas as pd
from jinja2 import Environment, PackageLoader, select_autoescape

from ..models.storage import Storage
from ..utils.format import format_duration
from .analytics import (
    current_streak,
    total_time_by_goal,
    date_histogram,
)

Range = Literal["week", "month", "all"]
Fmt = Literal["html", "md", "csv"]

__all__ = ["build_report"]


def _date_window(range_: Range) -> tuple[date, date]:
    today = date.today()
    if range_ == "week":
        start = today - timedelta(days=today.weekday())
        end = start + timedelta(days=6)
    elif range_ == "month":
        first = today.replace(day=1)
        prev = first - timedelta(days=1)
        start = prev.replace(day=1)
        end = prev
    else:
        start = date.min
        end = today
    return start, end


def build_report(
    storage: Storage,
    range_: Range,
    fmt: Fmt,
    out_path: Path | None,
    start: date | None = None,
    end: date | None = None,
) -> Path:
    if start is None or end is None:
        start, end = _date_window(range_)
    goals_sec = total_time_by_goal(storage, start, end)

    tag_totals: dict[str, int] = {}
    for gid, sec in goals_sec.items():
        g = storage.get_goal(gid)
        for t in g.tags:
            tag_totals[t] = tag_totals.get(t, 0) + sec

    hist = date_histogram(storage, start, end)
    streak = current_streak(storage, end)

    if fmt == "csv":
        df = pd.DataFrame(
            [
                {
                    "goal_id": gid,
                    "title": storage.get_goal(gid).title,
                    "total_sec": sec,
                    "tags": ",".join(storage.get_goal(gid).tags),
                }
                for gid, sec in goals_sec.items()
            ]
        )
        out = out_path or Path.home() / f"GoalGlide_{range_}_{start}_{end}.csv"
        df.to_csv(out, index=False)
        return out

    env = Environment(
        loader=PackageLoader("goal_glide", "templates"), autoescape=select_autoescape()
    )
    tpl = env.get_template("report_template.j2")
    html = tpl.render(
        start=start,
        end=end,
        generated=datetime.now(),
        total_sec=sum(goals_sec.values()),
        top_goals=sorted(goals_sec.items(), key=lambda x: x[1], reverse=True)[:5],
        tag_totals=sorted(tag_totals.items(), key=lambda x: x[1], reverse=True),
        streak=streak,
        hist=hist,
        fmt=fmt,
        format_duration=format_duration,
    )
    out = out_path or Path.home() / f"GoalGlide_{range_}_{start}_{end}.{fmt}"
    out.write_text(
        html if fmt == "html" else html.replace("<br>", "  \n"), encoding="utf-8"
    )
    return out
