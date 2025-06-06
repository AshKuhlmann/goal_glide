from __future__ import annotations


def format_duration(sec: int) -> str:
    h, m = divmod(sec // 60, 60)
    return f"{h} h {m:02} m"


__all__ = ["format_duration"]
