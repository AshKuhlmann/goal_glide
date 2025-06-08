from __future__ import annotations


def format_duration(sec: int) -> str:
    """Format seconds as HH:MM."""
    h, m = divmod(sec // 60, 60)
    return f"{h:d}:{m:02d}"


def format_duration_long(sec: int) -> str:
    """Format seconds as e.g. '2h 15m'."""
    h = sec // 3600
    m = (sec % 3600) // 60
    parts = []
    if h:
        parts.append(f"{h}h")
    if m or not parts:
        parts.append(f"{m}m")
    return " ".join(parts)


__all__ = ["format_duration", "format_duration_long"]
