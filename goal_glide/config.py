from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any, Dict, TypedDict, cast


class ConfigDict(TypedDict, total=False):
    quotes_enabled: bool
    reminders_enabled: bool
    reminder_break_min: int
    reminder_interval_min: int
    pomo_duration_min: int


DEFAULTS: ConfigDict = {
    "quotes_enabled": True,
    "reminders_enabled": False,
    "reminder_break_min": 5,
    "reminder_interval_min": 30,
    "pomo_duration_min": 25,
}


def _load_file(config_path: Path) -> Dict[str, Any]:
    if config_path.exists():
        with config_path.open("rb") as f:
            return tomllib.load(f)
    return {}


def load_config(config_path: Path) -> ConfigDict:
    file_cfg = cast(ConfigDict, _load_file(config_path))
    full_cfg: ConfigDict = {**DEFAULTS, **file_cfg}
    return full_cfg


def save_config(cfg: ConfigDict, config_path: Path) -> None:
    items = []
    for k, v in cfg.items():
        if isinstance(v, bool):
            items.append(f"{k} = {str(v).lower()}")
        else:
            items.append(f"{k} = {v!r}")
    content = "\n".join(items)
    with config_path.open("w", encoding="utf-8") as f:
        f.write(content)


def quotes_enabled(config_path: Path) -> bool:
    return bool(load_config(config_path).get("quotes_enabled", True))


def reminders_enabled(config_path: Path) -> bool:
    return bool(load_config(config_path).get("reminders_enabled", False))


def reminder_break(config_path: Path) -> int:
    return int(load_config(config_path).get("reminder_break_min", 5))


def reminder_interval(config_path: Path) -> int:
    return int(load_config(config_path).get("reminder_interval_min", 30))


def pomo_duration(config_path: Path) -> int:
    return int(load_config(config_path).get("pomo_duration_min", 25))
