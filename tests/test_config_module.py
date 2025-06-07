from pathlib import Path

import pytest

from goal_glide import config


@pytest.fixture()
def cfg_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "config.toml"
    monkeypatch.setattr(config, "_CONFIG_PATH", path)
    config._CONFIG_CACHE = None
    return path


def test_default_values_when_file_missing(cfg_path: Path) -> None:
    assert config.quotes_enabled() is True
    assert config.reminders_enabled() is False
    assert config.reminder_break() == 5
    assert config.reminder_interval() == 30
    assert config.load_config() == config.DEFAULTS


def test_save_and_load_roundtrip(cfg_path: Path) -> None:
    new_cfg = {
        "quotes_enabled": False,
        "reminders_enabled": True,
        "reminder_break_min": 10,
        "reminder_interval_min": 20,
    }
    config.save_config(new_cfg)
    config._CONFIG_CACHE = None
    loaded = config.load_config()
    assert loaded["quotes_enabled"] is False
    assert loaded["reminders_enabled"] is True
    text = cfg_path.read_text()
    assert "quotes_enabled = false" in text
    assert "reminders_enabled = true" in text
