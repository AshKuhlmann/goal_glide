from __future__ import annotations

from datetime import datetime, timedelta

from apscheduler.schedulers.background import BackgroundScheduler

from ..config import reminder_break, reminder_interval, reminders_enabled
from . import pomodoro
from .notify import push

_sched: BackgroundScheduler | None = None


def _scheduler() -> BackgroundScheduler:
    global _sched
    if _sched is None:
        _sched = BackgroundScheduler(daemon=True)
        _sched.start()
    return _sched


def schedule_after_stop() -> None:
    if not reminders_enabled():
        return
    sched = _scheduler()
    sched.remove_all_jobs(jobstore="default")
    now = datetime.now()
    sched.add_job(
        push,
        "date",
        run_date=now + timedelta(minutes=reminder_break()),
        args=["Break over, ready for next session?"],
        id="break_end",
    )
    sched.add_job(
        push,
        "interval",
        minutes=reminder_interval(),
        args=["Time for another Pomodoro!"],
        id="next_pomo",
    )


def cancel_all() -> None:
    if _sched:
        _sched.remove_all_jobs()


pomodoro.on_session_end.append(schedule_after_stop)
pomodoro.on_new_session.append(cancel_all)


__all__ = ["schedule_after_stop", "cancel_all"]
