"""Goal Glide package."""

from __future__ import annotations

from importlib import metadata
from pathlib import Path
import tomllib


try:
    __version__ = metadata.version("goal_glide")
except metadata.PackageNotFoundError:
    # Fallback for editable/checkout usage
    try:
        pyproject = Path(__file__).resolve().parent.parent / "pyproject.toml"
        with pyproject.open("rb") as fh:
            data = tomllib.load(fh)
        __version__ = data.get("tool", {}).get("poetry", {}).get("version", "0.0.0")
    except Exception:  # pragma: no cover - extremely unlikely
        __version__ = "0.0.0"

from .commands.common import handle_exceptions  # noqa: E402,F401  keep import order
from .cli import cli

__all__ = ["handle_exceptions", "__version__", "cli"]
