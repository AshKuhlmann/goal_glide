from __future__ import annotations


def format_duration(sec: int) -> str:
    """Format seconds as HH:MM."""
    h, m = divmod(sec // 60, 60)
    return f"{h:d}:{m:02d}"


__all__ = ["format_duration"]
