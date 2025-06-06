from __future__ import annotations

from datetime import datetime, timedelta


def natural_delta(dt: datetime) -> str:
    delta = datetime.now() - dt
    if delta < timedelta(minutes=1):
        return "<1m ago"
    if delta < timedelta(hours=1):
        mins = int(delta.total_seconds() // 60)
        return f"{mins}m ago"
    if delta < timedelta(days=1):
        hours = int(delta.total_seconds() // 3600)
        return f"{hours}h ago"
    days = delta.days
    return f"{days}d ago"
