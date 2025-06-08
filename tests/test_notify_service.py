import sys
from types import SimpleNamespace

import pytest

from goal_glide.services import notify


def test_linux_notify_with_notify2(monkeypatch):
    events: list[tuple[str, str] | str] = []

    class DummyNotification:
        def __init__(self, title: str, message: str) -> None:
            events.append((title, message))

        def show(self) -> None:
            events.append("show")

    dummy = SimpleNamespace(init=lambda name: events.append(("init", name)), Notification=DummyNotification)
    monkeypatch.setitem(sys.modules, "notify2", dummy)

    notify._linux_notify("hello")

    assert events == [("init", "GoalGlide"), ("Goal Glide", "hello"), "show"]


def test_linux_notify_fallback(monkeypatch):
    if "notify2" in sys.modules:
        monkeypatch.delitem(sys.modules, "notify2", raising=False)
    called = []
    monkeypatch.setattr(notify.subprocess, "run", lambda cmd, check=False: called.append(cmd))

    notify._linux_notify("hi")

    assert called == [["notify-send", "Goal Glide", "hi"]]


def test_push_unsupported_os(monkeypatch):
    msgs = []
    monkeypatch.setattr(notify.platform, "system", lambda: "Atari")
    monkeypatch.setattr(notify.logging, "info", lambda msg, *a: msgs.append(msg % a))

    notify.push("hi")

    assert msgs == ["No notifier for OS Atari"]
