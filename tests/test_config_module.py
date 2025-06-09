from pathlib import Path

import pytest
from pytest import MonkeyPatch
import tomllib

from goal_glide import cli, config
from click.testing import CliRunner


@pytest.fixture()
def cfg_path(tmp_path: Path, monkeypatch: MonkeyPatch) -> Path:
    path = tmp_path / "config.toml"
    monkeypatch.setattr(config, "_CONFIG_PATH", path)
    return path


def test_default_values_when_file_missing(cfg_path: Path) -> None:
    assert config.quotes_enabled() is True
    assert config.reminders_enabled() is False
    assert config.reminder_break() == 5
    assert config.reminder_interval() == 30
    assert config.pomo_duration() == 25
    assert config.load_config() == config.DEFAULTS


def test_save_and_load_roundtrip(cfg_path: Path) -> None:
    new_cfg = {
        "quotes_enabled": False,
        "reminders_enabled": True,
        "reminder_break_min": 10,
        "reminder_interval_min": 20,
        "pomo_duration_min": 15,
    }
    config.save_config(new_cfg)
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
        "pomo_duration_min": 15,
    }
    config.save_config(cfg)
    runner = CliRunner()
    result = runner.invoke(cli.goal, ["config", "show"])
    assert result.exit_code == 0
    for k, v in cfg.items():
        assert k in result.output
        assert str(v) in result.output


def test_partial_config_file_loads_defaults(cfg_path: Path) -> None:
    cfg_path.write_text("quotes_enabled = false", encoding="utf-8")
    loaded = config.load_config()
    assert loaded["quotes_enabled"] is False
    for key, value in config.DEFAULTS.items():
        if key != "quotes_enabled":
            assert loaded[key] == value

    assert config.quotes_enabled() is False
    assert config.reminders_enabled() is config.DEFAULTS["reminders_enabled"]
    assert config.reminder_break() == config.DEFAULTS["reminder_break_min"]
    assert config.reminder_interval() == config.DEFAULTS["reminder_interval_min"]
    assert config.pomo_duration() == config.DEFAULTS["pomo_duration_min"]


def test_load_reflects_file_changes(cfg_path: Path) -> None:
    cfg_path.write_text("quotes_enabled = false", encoding="utf-8")
    first = config.quotes_enabled()
    assert first is False
    cfg_path.write_text("quotes_enabled = true", encoding="utf-8")
    second = config.quotes_enabled()
    assert second is True


def test_save_creates_parent_dirs(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    nested = tmp_path / "a" / "b" / "config.toml"
    monkeypatch.setattr(config, "_CONFIG_PATH", nested)
    config.save_config({"quotes_enabled": False})
    assert nested.parent.exists() is True
    assert nested.exists() is True


def test_save_string_value(cfg_path: Path) -> None:
    cfg = {"foo": "bar"}
    config.save_config(cfg)
    text = cfg_path.read_text()
    assert "foo = 'bar'" in text
    loaded = config.load_config()
    assert loaded["foo"] == "bar"


def test_mutating_loaded_config_does_not_affect_cache(cfg_path: Path) -> None:
    cfg = {
        "quotes_enabled": True,
        "reminders_enabled": True,
        "reminder_break_min": 10,
        "reminder_interval_min": 20,
        "pomo_duration_min": 15,
    }
    config.save_config(cfg)

    cfg1 = config.load_config()
    cfg1["quotes_enabled"] = False

    cfg2 = config.load_config()
    assert cfg2["quotes_enabled"] is True


def test_invalid_toml_raises_decode_error(cfg_path: Path) -> None:
    cfg_path.write_text("foo = bar", encoding="utf-8")
    with pytest.raises(tomllib.TOMLDecodeError):
        config.load_config()


def test_config_path_from_env(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("GOAL_GLIDE_CONFIG_DIR", str(tmp_path))
    import importlib
    import goal_glide.config as cfg

    importlib.reload(cfg)
    assert cfg._CONFIG_PATH == tmp_path / "config.toml"

    monkeypatch.delenv("GOAL_GLIDE_CONFIG_DIR", raising=False)
    importlib.reload(cfg)
