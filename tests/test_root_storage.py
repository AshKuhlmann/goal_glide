from datetime import datetime

from dataclasses import dataclass

from goal_glide.models.goal import Priority
from goal_glide.storage import Storage


@dataclass
class FakeGoal:
    id: str
    title: str
    created: datetime
    priority: str = "medium"
    archived: bool = False


def test_crud_operations(tmp_path):
    store = Storage(tmp_path / "db.json")
    g1 = FakeGoal(
        id="1", title="A", created=datetime.utcnow(), priority=Priority.high.value
    )
    store.add_goal(g1)
    assert [g.id for g in store.list_goals()] == ["1"]
    assert store.find_by_title("A").id == "1"
    assert store.remove_goal("1") is True
    assert list(store.list_goals()) == []


def test_list_filters(tmp_path):
    store = Storage(tmp_path / "db.json")
    g1 = FakeGoal(
        id="1", title="a", created=datetime.utcnow(), priority=Priority.low.value
    )
    g2 = FakeGoal(
        id="2",
        title="b",
        created=datetime.utcnow(),
        archived=True,
        priority=Priority.high.value,
    )
    store.add_goal(g1)
    store.add_goal(g2)
    assert len(list(store.list_goals())) == 1
    assert len(list(store.list_goals(include_archived=True))) == 2
    assert len(list(store.list_goals(archived_only=True))) == 1
    assert len(list(store.list_goals(priority="high", include_archived=True))) == 1
