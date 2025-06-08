from datetime import datetime
from pathlib import Path

from goal_glide.models.goal import Goal
from goal_glide.models.storage import Storage


def test_store_and_retrieve_parent(tmp_path: Path) -> None:
    storage = Storage(tmp_path)
    parent = Goal(id="p", title="parent", created=datetime.utcnow())
    child = Goal(id="c", title="child", created=datetime.utcnow(), parent_id="p")
    storage.add_goal(parent)
    storage.add_goal(child)

    loaded = storage.get_goal("c")
    assert loaded.parent_id == "p"


def test_list_goals_parent_filter(tmp_path: Path) -> None:
    storage = Storage(tmp_path)
    p = Goal(id="p", title="parent", created=datetime.utcnow())
    child1 = Goal(id="c1", title="child1", created=datetime.utcnow(), parent_id="p")
    child2 = Goal(id="c2", title="child2", created=datetime.utcnow(), parent_id="p")
    storage.add_goal(p)
    storage.add_goal(child1)
    storage.add_goal(child2)

    children = storage.list_goals(parent_id="p")
    assert {g.id for g in children} == {"c1", "c2"}
