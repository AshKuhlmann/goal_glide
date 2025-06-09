"""Scheduling helper for break and interval reminders."""

from __future__ import annotations

from datetime import datetime, timedelta

from apscheduler.schedulers.background import BackgroundScheduler
from pathlib import Path

from ..config import reminder_break, reminder_interval, reminders_enabled
from . import pomodoro
from .notify import push

_sched: BackgroundScheduler | None = None


def _scheduler() -> BackgroundScheduler:
    """Return the lazily created :class:`BackgroundScheduler` instance.

    The scheduler runs in the background thread and is shared by all
    reminder functions in this module.
    """

    global _sched
    if _sched is None:
        _sched = BackgroundScheduler(daemon=True)
        _sched.start()
    return _sched


def schedule_after_stop(config_path: Path) -> None:
    """Set up reminders once a Pomodoro session finishes.

    Two jobs are scheduled: one to notify the user when a break is over and
    another periodic reminder encouraging them to start a new session.
    """

    if not reminders_enabled(config_path):
        return
    sched = _scheduler()
    sched.remove_all_jobs(jobstore="default")
    now = datetime.now()
    sched.add_job(
        push,
        "date",
        run_date=now + timedelta(minutes=reminder_break(config_path)),
        args=["Break over, ready for next session?"],
        id="break_end",
    )
    sched.add_job(
        push,
        "interval",
        minutes=reminder_interval(config_path),
        args=["Time for another Pomodoro!"],
        id="next_pomo",
    )


def cancel_all() -> None:
    """Remove any pending reminder jobs from the scheduler."""

    if _sched:
        _sched.remove_all_jobs()


pomodoro.on_session_end.append(schedule_after_stop)
pomodoro.on_new_session.append(cancel_all)


__all__ = ["schedule_after_stop", "cancel_all"]
