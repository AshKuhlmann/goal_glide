from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any, Dict

DEFAULTS: Dict[str, Any] = {
    "quotes_enabled": True,
    "reminders_enabled": False,
    "reminder_break_min": 5,
    "reminder_interval_min": 30,
}
_CONFIG_CACHE: Dict[str, Any] | None = None
_CONFIG_PATH = Path.home() / ".goal_glide" / "config.toml"


def _load_file() -> Dict[str, Any]:
    if _CONFIG_PATH.exists():
        with _CONFIG_PATH.open("rb") as f:
            return tomllib.load(f)
    return {}


def _config() -> Dict[str, Any]:
    global _CONFIG_CACHE
    if _CONFIG_CACHE is None:
        data = _load_file()
        cfg = DEFAULTS | data
        _CONFIG_CACHE = cfg
    return _CONFIG_CACHE


def quotes_enabled() -> bool:
    return bool(_config().get("quotes_enabled", True))


def reminders_enabled() -> bool:
    return bool(_config().get("reminders_enabled", False))


def reminder_break() -> int:
    return int(_config().get("reminder_break_min", 5))


def reminder_interval() -> int:
    return int(_config().get("reminder_interval_min", 30))


def load_config() -> Dict[str, Any]:
    return dict(_config())


def save_config(cfg: Dict[str, Any]) -> None:
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
    global _CONFIG_CACHE
    _CONFIG_CACHE = cfg
