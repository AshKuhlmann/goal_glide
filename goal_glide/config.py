from __future__ import annotations

import tomllib
from pathlib import Path
import os
from typing import Any, Dict, TypedDict, cast


class ConfigDict(TypedDict, total=False):
    quotes_enabled: bool
    reminders_enabled: bool
    reminder_break_min: int
    reminder_interval_min: int


DEFAULTS: ConfigDict = {
    "quotes_enabled": True,
    "reminders_enabled": False,
    "reminder_break_min": 5,
    "reminder_interval_min": 30,
}

_CONFIG_PATH = (
    Path(os.environ["GOAL_GLIDE_CONFIG_DIR"]) / "config.toml"
    if "GOAL_GLIDE_CONFIG_DIR" in os.environ
    else Path.home() / ".goal_glide" / "config.toml"
)


def _load_file() -> Dict[str, Any]:
    if _CONFIG_PATH.exists():
        with _CONFIG_PATH.open("rb") as f:
            return tomllib.load(f)
    return {}


def _config() -> ConfigDict:
    data = cast(ConfigDict, _load_file())
    full_cfg: ConfigDict = {**DEFAULTS, **data}
    return full_cfg


def quotes_enabled() -> bool:
    return bool(_config().get("quotes_enabled", True))


def reminders_enabled() -> bool:
    return bool(_config().get("reminders_enabled", False))


def reminder_break() -> int:
    return int(_config().get("reminder_break_min", 5))


def reminder_interval() -> int:
    return int(_config().get("reminder_interval_min", 30))


def load_config() -> ConfigDict:
    file_cfg = cast(ConfigDict, _load_file())
    full_cfg: ConfigDict = {**DEFAULTS, **file_cfg}
    return full_cfg


def save_config(cfg: ConfigDict) -> None:
    _CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    items = []
    for k, v in cfg.items():
        if isinstance(v, bool):
            items.append(f"{k} = {str(v).lower()}")
        else:
            items.append(f"{k} = {v!r}")
    content = "\n".join(items)
    with _CONFIG_PATH.open("w", encoding="utf-8") as f:
        f.write(content)
