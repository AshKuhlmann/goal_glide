"""Utility functions for sending desktop notifications.

This module dispatches small toast notifications on the three major
platforms.  Each operating system requires a different third-party helper
binary or library.  If a helper is missing we log the failure and print a
hint so that users can easily install the missing dependency.
"""

from __future__ import annotations

import logging
import platform
import subprocess
from typing import Callable


def _mac_notify(msg: str) -> None:
    """Send a notification on macOS using ``terminal-notifier``.

    Parameters
    ----------
    msg:
        The message text to display.
    """

    subprocess.run(["terminal-notifier", "-message", msg], check=False)


def _linux_notify(msg: str) -> None:
    """Show a notification on Linux.

    The function first tries to use the :mod:`notify2` library.  If that
    fails, it falls back to the ``notify-send`` command line tool.

    Parameters
    ----------
    msg:
        The message text to display.
    """

    try:
        import notify2

        notify2.init("GoalGlide")
        notify2.Notification("Goal Glide", msg).show()
    except Exception:
        subprocess.run(["notify-send", "Goal Glide", msg], check=False)


def _win_notify(msg: str) -> None:
    """Display a Windows toast notification via ``win10toast``.

    Parameters
    ----------
    msg:
        The message text to display.
    """

    from win10toast import ToastNotifier

    ToastNotifier().show_toast("Goal Glide", msg, threaded=True)


_OS_NOTIFIERS: dict[str, Callable[[str], None]] = {
    "Darwin": _mac_notify,
    "Linux": _linux_notify,
    "Windows": _win_notify,
}

_HELP_HINTS: dict[str, str] = {
    "Darwin": (
        "Install 'terminal-notifier' with Homebrew: " "brew install terminal-notifier"
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
    """Display ``msg`` as a desktop notification.

    The operating system is detected at runtime and the corresponding helper
    is used.  When no suitable helper is available a helpful message is
    printed so the user can install the required tool.

    Parameters
    ----------
    msg:
        The message text to display.
    """

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
