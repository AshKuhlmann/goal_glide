import pytest
from click.testing import CliRunner
from hypothesis import settings

settings.register_profile("ci", deadline=None)
settings.load_profile("ci")


@pytest.fixture()
def runner(tmp_path, monkeypatch):
    monkeypatch.setenv("GOAL_GLIDE_DB_DIR", str(tmp_path))
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("GOAL_GLIDE_SESSION_FILE", str(tmp_path / "session.json"))
    return CliRunner()
