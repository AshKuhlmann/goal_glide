from datetime import datetime, timedelta

import pytest

from goal_glide.utils import format as fmt
from goal_glide.utils import timefmt
from goal_glide.utils import tag
from goal_glide.exceptions import InvalidTagError


def test_format_duration_basic() -> None:
    assert fmt.format_duration(0) == "0:00"
    assert fmt.format_duration(3661) == "1:01"


def test_natural_delta_formats(monkeypatch: pytest.MonkeyPatch) -> None:
    fixed_now = datetime(2023, 1, 2, 12, 0, 0)
    monkeypatch.setattr(timefmt, "datetime", type("D", (), {"now": staticmethod(lambda: fixed_now)})())
    assert timefmt.natural_delta(fixed_now - timedelta(seconds=30)) == "<1m ago"
    assert timefmt.natural_delta(fixed_now - timedelta(minutes=5)) == "5m ago"
    assert timefmt.natural_delta(fixed_now - timedelta(hours=2)) == "2h ago"
    assert timefmt.natural_delta(fixed_now - timedelta(days=3)) == "3d ago"


def test_validate_tag() -> None:
    assert tag.validate_tag("work") == "work"
    with pytest.raises(InvalidTagError):
        tag.validate_tag("BAD@TAG")
