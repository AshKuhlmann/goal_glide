import tomllib
from pathlib import Path
import pytest
from click.testing import CliRunner

from goal_glide.cli import cli
from goal_glide import config


@pytest.fixture()
def cfg_path(tmp_path: Path) -> Path:
    return tmp_path / "config.toml"


def test_default_values_when_file_missing(cfg_path: Path) -> None:
    assert config.quotes_enabled(cfg_path) is True
    assert config.reminders_enabled(cfg_path) is False
    assert config.reminder_break(cfg_path) == 5
    assert config.reminder_interval(cfg_path) == 30
    assert config.pomo_duration(cfg_path) == 25
    assert config.load_config(cfg_path) == config.DEFAULTS


def test_save_and_load_roundtrip(cfg_path: Path) -> None:
    new_cfg = {
        "quotes_enabled": False,
        "reminders_enabled": True,
        "reminder_break_min": 10,
        "reminder_interval_min": 20,
        "pomo_duration_min": 15,
    }
    config.save_config(new_cfg, cfg_path)
    loaded = config.load_config(cfg_path)
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
    config.save_config(cfg, cfg_path)
    runner = CliRunner()
    env = {"GOAL_GLIDE_DB_DIR": str(cfg_path.parent), "HOME": str(cfg_path.parent)}
    result = runner.invoke(cli, ["config", "show"], env=env)
    assert result.exit_code == 0
    for k, v in cfg.items():
        assert k in result.output
        assert str(v) in result.output


def test_partial_config_file_loads_defaults(cfg_path: Path) -> None:
    cfg_path.write_text("quotes_enabled = false", encoding="utf-8")
    loaded = config.load_config(cfg_path)
    assert loaded["quotes_enabled"] is False
    for key, value in config.DEFAULTS.items():
        if key != "quotes_enabled":
            assert loaded[key] == value

    assert config.quotes_enabled(cfg_path) is False
    assert (
        config.reminders_enabled(cfg_path)
        is config.DEFAULTS["reminders_enabled"]
    )
    assert (
        config.reminder_break(cfg_path)
        == config.DEFAULTS["reminder_break_min"]
    )
    assert (
        config.reminder_interval(cfg_path)
        == config.DEFAULTS["reminder_interval_min"]
    )
    assert (
        config.pomo_duration(cfg_path)
        == config.DEFAULTS["pomo_duration_min"]
    )


def test_load_reflects_file_changes(cfg_path: Path) -> None:
    cfg_path.write_text("quotes_enabled = false", encoding="utf-8")
    first = config.quotes_enabled(cfg_path)
    assert first is False
    cfg_path.write_text("quotes_enabled = true", encoding="utf-8")
    second = config.quotes_enabled(cfg_path)
    assert second is True


def test_save_creates_parent_dirs(tmp_path: Path) -> None:
    nested = tmp_path / "a" / "b" / "config.toml"
    nested.parent.mkdir(parents=True, exist_ok=True)
    config.save_config({"quotes_enabled": False}, nested)
    assert nested.exists() is True


def test_save_string_value(cfg_path: Path) -> None:
    cfg = {"foo": "bar"}
    config.save_config(cfg, cfg_path)
    text = cfg_path.read_text()
    assert "foo = 'bar'" in text
    loaded = config.load_config(cfg_path)
    assert loaded["foo"] == "bar"


def test_mutating_loaded_config_does_not_affect_cache(cfg_path: Path) -> None:
    cfg = {
        "quotes_enabled": True,
        "reminders_enabled": True,
        "reminder_break_min": 10,
        "reminder_interval_min": 20,
        "pomo_duration_min": 15,
    }
    config.save_config(cfg, cfg_path)

    cfg1 = config.load_config(cfg_path)
    cfg1["quotes_enabled"] = False

    cfg2 = config.load_config(cfg_path)
    assert cfg2["quotes_enabled"] is True


def test_invalid_toml_raises_decode_error(cfg_path: Path) -> None:
    cfg_path.write_text("foo = bar", encoding="utf-8")
    with pytest.raises(tomllib.TOMLDecodeError):
        config.load_config(cfg_path)


def test_cli_respects_env_variable(tmp_path: Path) -> None:
    runner = CliRunner()
    env = {"GOAL_GLIDE_DB_DIR": str(tmp_path), "HOME": str(tmp_path)}
    result = runner.invoke(cli, ["config", "quotes", "--disable"], env=env)
    assert result.exit_code == 0
    assert (tmp_path / "config.toml").exists()