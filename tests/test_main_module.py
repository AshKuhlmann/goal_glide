import runpy

import pytest


def test_main_invokes_cli(monkeypatch: pytest.MonkeyPatch) -> None:
    called = []

    def fake_cli() -> None:
        called.append(True)

    monkeypatch.setattr("goal_glide.cli.cli", fake_cli)
    runpy.run_module("goal_glide.__main__", run_name="__main__")
    assert called == [True]
