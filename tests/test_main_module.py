import runpy
import sys
import types

import pytest


def _patch_cli(monkeypatch: pytest.MonkeyPatch, impl: callable) -> None:
    """Inject a minimal ``goal_glide.cli`` module using *impl* as ``cli``."""

    fake_cli_module = types.ModuleType("goal_glide.cli")
    fake_cli_module.cli = impl
    fake_cli_module.handle_exceptions = lambda func: func
    monkeypatch.setitem(sys.modules, "goal_glide.cli", fake_cli_module)


def test_main_invokes_cli(monkeypatch: pytest.MonkeyPatch) -> None:
    called = []

    def fake_cli() -> None:
        called.append(True)

    _patch_cli(monkeypatch, fake_cli)
    runpy.run_module("goal_glide.__main__", run_name="__main__")
    assert called == [True]


def test_main_does_not_invoke_cli_when_not_main(monkeypatch: pytest.MonkeyPatch) -> None:
    called = []

    def fake_cli() -> None:
        called.append(True)

    _patch_cli(monkeypatch, fake_cli)
    runpy.run_module("goal_glide.__main__", run_name="not_main")
    assert called == []


def test_main_propagates_cli_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_cli() -> None:
        raise RuntimeError("boom")

    _patch_cli(monkeypatch, fake_cli)
    with pytest.raises(RuntimeError):
        runpy.run_module("goal_glide.__main__", run_name="__main__")
