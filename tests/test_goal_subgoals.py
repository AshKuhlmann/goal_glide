from datetime import datetime
from pathlib import Path
import tempfile

from click.testing import CliRunner

from goal_glide.cli import goal
from goal_glide.models.goal import Goal
from goal_glide.models.storage import Storage


def test_store_and_retrieve_parent(tmp_path: Path) -> None:
    storage = Storage(tmp_path / "db.json")
    parent = Goal(id="p", title="parent", created=datetime.utcnow())
    child = Goal(id="c", title="child", created=datetime.utcnow(), parent_id="p")
    storage.add_goal(parent)
    storage.add_goal(child)

    loaded = storage.get_goal("c")
    assert loaded.parent_id == "p"


def test_list_goals_parent_filter(tmp_path: Path) -> None:
    storage = Storage(tmp_path / "db.json")
    p = Goal(id="p", title="parent", created=datetime.utcnow())
    child1 = Goal(id="c1", title="child1", created=datetime.utcnow(), parent_id="p")
    child2 = Goal(id="c2", title="child2", created=datetime.utcnow(), parent_id="p")
    storage.add_goal(p)
    storage.add_goal(child1)
    storage.add_goal(child2)

    children = storage.list_goals(parent_id="p")
    assert {g.id for g in children} == {"c1", "c2"}


def test_remove_parent_keeps_children(tmp_path: Path) -> None:
    storage = Storage(tmp_path / "db.json")
    parent = Goal(id="p", title="p", created=datetime.utcnow())
    c1 = Goal(id="c1", title="c1", created=datetime.utcnow(), parent_id="p")
    c2 = Goal(id="c2", title="c2", created=datetime.utcnow(), parent_id="p")
    storage.add_goal(parent)
    storage.add_goal(c1)
    storage.add_goal(c2)

    storage.remove_goal("p")

    assert storage.get_goal("c1").parent_id == "p"
    assert storage.get_goal("c2").parent_id == "p"
    children = storage.list_goals(parent_id="p")
    assert {g.id for g in children} == {"c1", "c2"}


def test_list_goals_parent_with_archived_flags(tmp_path: Path) -> None:
    storage = Storage(tmp_path / "db.json")
    p = Goal(id="p", title="parent", created=datetime.utcnow())
    active = Goal(id="a", title="active", created=datetime.utcnow(), parent_id="p")
    archived = Goal(id="b", title="archived", created=datetime.utcnow(), parent_id="p")
    storage.add_goal(p)
    storage.add_goal(active)
    storage.add_goal(archived)
    storage.archive_goal("b")

    listed = storage.list_goals(parent_id="p")
    assert [g.id for g in listed] == ["a"]

    listed = storage.list_goals(parent_id="p", include_archived=True)
    assert {g.id for g in listed} == {"a", "b"}

    listed = storage.list_goals(parent_id="p", only_archived=True)
    assert [g.id for g in listed] == ["b"]


def test_list_goals_parent_missing_returns_empty(tmp_path: Path) -> None:
    storage = Storage(tmp_path / "db.json")
    storage.add_goal(Goal(id="p", title="parent", created=datetime.utcnow()))
    storage.add_goal(
        Goal(id="c", title="child", created=datetime.utcnow(), parent_id="p")
    )

    assert storage.list_goals(parent_id="missing") == []


from hypothesis import given, settings, strategies as st


@st.composite
def _parent_child_mapping(draw: st.DrawFn) -> dict[str, list[str]]:
    parents = draw(
        st.lists(st.text(min_size=1, max_size=3), unique=True, min_size=1, max_size=5)
    )
    all_children = draw(
        st.lists(st.text(min_size=1, max_size=3), unique=True, max_size=10)
    )
    mapping = {p: [] for p in parents}
    for cid in all_children:
        parent = draw(st.sampled_from(parents))
        mapping[parent].append(cid)
    return mapping


@given(_parent_child_mapping())
@settings(max_examples=25)
def test_list_goals_parent_property(mapping: dict[str, list[str]]) -> None:
    with tempfile.TemporaryDirectory() as d:
        storage = Storage(Path(d) / "db.json")
        for pid in mapping:
            storage.add_goal(Goal(id=pid, title=pid, created=datetime.utcnow()))
        for pid, cids in mapping.items():
            for cid in cids:
                storage.add_goal(
                    Goal(
                        id=cid,
                        title=cid,
                        created=datetime.utcnow(),
                        parent_id=pid,
                    )
                )
        for pid, cids in mapping.items():
            listed = storage.list_goals(parent_id=pid)
            assert {g.id for g in listed} == set(cids)


def test_cli_add_with_parent(tmp_path: Path) -> None:
    runner = CliRunner()
    env = {"GOAL_GLIDE_DB_DIR": str(tmp_path)}
    runner.invoke(goal, ["add", "parent"], env=env)
    pid = Storage(tmp_path / "db.json").list_goals()[0].id
    runner.invoke(goal, ["add", "child", "--parent", pid], env=env)
    children = Storage(tmp_path / "db.json").list_goals(parent_id=pid)
    assert len(children) == 1 and children[0].title == "child"


def test_goal_tree_output(tmp_path: Path) -> None:
    runner = CliRunner()
    env = {"GOAL_GLIDE_DB_DIR": str(tmp_path)}
    runner.invoke(goal, ["add", "parent"], env=env)
    pid = Storage(tmp_path / "db.json").list_goals()[0].id
    runner.invoke(goal, ["add", "child", "--parent", pid], env=env)
    result = runner.invoke(goal, ["tree"], env=env)
    assert "child" in result.output
    assert result.output.find("child") > result.output.find("parent")
