"""Simple cross-platform desktop notification helpers."""

from __future__ import annotations

import logging
import platform
import subprocess
from typing import Callable


def _mac_notify(msg: str) -> None:
    """Display a notification on macOS using ``terminal-notifier``."""

    subprocess.run(["terminal-notifier", "-message", msg], check=False)


def _linux_notify(msg: str) -> None:
    """Show a notification on Linux via ``notify2`` or ``notify-send``."""

    try:
        import notify2

        notify2.init("GoalGlide")
        notify2.Notification("Goal Glide", msg).show()
    except Exception:
        subprocess.run(["notify-send", "Goal Glide", msg], check=False)


def _win_notify(msg: str) -> None:
    """Send a Windows toast notification using ``win10toast``."""

    from win10toast import ToastNotifier

    ToastNotifier().show_toast("Goal Glide", msg, threaded=True)


_OS_NOTIFIERS: dict[str, Callable[[str], None]] = {
    "Darwin": _mac_notify,
    "Linux": _linux_notify,
    "Windows": _win_notify,
}

_HELP_HINTS: dict[str, str] = {
    "Darwin": (
        "Install 'terminal-notifier' with Homebrew: "
        "brew install terminal-notifier"
    ),
    "Linux": "Install 'notify2' via pip or 'notify-send' via your package manager",
    "Windows": "Install 'win10toast' via pip: pip install win10toast",
}

_DEFAULT_HINT = (
    "Desktop notifications require an external helper. "
    "Install 'terminal-notifier' on macOS, 'notify2' or 'notify-send' on Linux, "
    "or 'win10toast' on Windows."
)


def push(msg: str) -> None:
    """Push a notification message using the appropriate OS backend."""

    osname = platform.system()
    notifier = _OS_NOTIFIERS.get(osname)
    hint = _HELP_HINTS.get(osname, _DEFAULT_HINT)
    if notifier:
        try:
            notifier(msg)
        except Exception as exc:  # pragma: no cover - log only
            logging.warning("Notification failed: %s", exc)
            print(hint)
    else:  # pragma: no cover - unsupported OS
        logging.info("No notifier for OS %s", osname)
        print(hint)


__all__ = ["push"]
