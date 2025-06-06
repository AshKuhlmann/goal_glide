from __future__ import annotations

import logging
import platform
import subprocess
from typing import Callable


def _mac_notify(msg: str) -> None:
    subprocess.run(["terminal-notifier", "-message", msg], check=False)


def _linux_notify(msg: str) -> None:
    try:
        import notify2

        notify2.init("GoalGlide")
        notify2.Notification("Goal Glide", msg).show()
    except Exception:
        subprocess.run(["notify-send", "Goal Glide", msg], check=False)


def _win_notify(msg: str) -> None:
    from win10toast import ToastNotifier

    ToastNotifier().show_toast("Goal Glide", msg, threaded=True)


_OS_NOTIFIERS: dict[str, Callable[[str], None]] = {
    "Darwin": _mac_notify,
    "Linux": _linux_notify,
    "Windows": _win_notify,
}


def push(msg: str) -> None:
    notifier = _OS_NOTIFIERS.get(platform.system())
    if notifier:
        try:
            notifier(msg)
        except Exception as exc:  # pragma: no cover - log only
            logging.warning("Notification failed: %s", exc)
    else:  # pragma: no cover - unsupported OS
        logging.info("No notifier for OS %s", platform.system())


__all__ = ["push"]
