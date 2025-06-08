from pathlib import Path

import pytest
from pytest import MonkeyPatch

from goal_glide import cli, config
from click.testing import CliRunner


@pytest.fixture()
def cfg_path(tmp_path: Path, monkeypatch: MonkeyPatch) -> Path:
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


def test_show_command_outputs_all_settings(cfg_path: Path) -> None:
    cfg = {
        "quotes_enabled": False,
        "reminders_enabled": True,
        "reminder_break_min": 10,
        "reminder_interval_min": 20,
    }
    config.save_config(cfg)
    config._CONFIG_CACHE = None
    runner = CliRunner()
    result = runner.invoke(cli.goal, ["config", "show"])
    assert result.exit_code == 0
    for k, v in cfg.items():
        assert k in result.output
        assert str(v) in result.output


def test_partial_config_file_loads_defaults(cfg_path: Path) -> None:
    cfg_path.write_text("quotes_enabled = false", encoding="utf-8")
    config._CONFIG_CACHE = None
    loaded = config.load_config()
    assert loaded["quotes_enabled"] is False
    for key, value in config.DEFAULTS.items():
        if key != "quotes_enabled":
            assert loaded[key] == value

    assert config.quotes_enabled() is False
    assert config.reminders_enabled() is config.DEFAULTS["reminders_enabled"]
    assert config.reminder_break() == config.DEFAULTS["reminder_break_min"]
    assert config.reminder_interval() == config.DEFAULTS["reminder_interval_min"]


def test_cache_prevents_reload_without_clear(cfg_path: Path) -> None:
    cfg_path.write_text("quotes_enabled = false", encoding="utf-8")
    config._CONFIG_CACHE = None
    first = config.quotes_enabled()
    assert first is False
    cfg_path.write_text("quotes_enabled = true", encoding="utf-8")
    second = config.quotes_enabled()
    assert second is False
    config._CONFIG_CACHE = None
    third = config.quotes_enabled()
    assert third is True


def test_save_creates_parent_dirs(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    nested = tmp_path / "a" / "b" / "config.toml"
    monkeypatch.setattr(config, "_CONFIG_PATH", nested)
    config._CONFIG_CACHE = None
    config.save_config({"quotes_enabled": False})
    assert nested.parent.exists() is True
    assert nested.exists() is True
