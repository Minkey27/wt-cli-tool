import asyncio
import json
from pathlib import Path

from textual.widgets import DataTable

from wt import app as app_module
from wt import compose, worktrees
from wt.compose import ComposeState, Status

STATUSES = {
    "/srv/main": Status.STOPPED,
    "/srv/no-compose": Status.NO_COMPOSE,
    "/srv/running": Status.RUNNING,
}
STATUS_HEADER = (45, 0)


def _run(monkeypatch, steps) -> list[tuple[list[str], str, str]]:
    """Mount the app on three fake worktrees, run each step, and record after each
    one the row order, the worktree under the cursor and the Status header label.

    Steps get the pilot and a per-run copy of STATUSES they may change.
    """
    statuses = dict(STATUSES)
    wts = [
        worktrees.Worktree(path=Path(p), branch=p, head="abc", is_main=i == 0, is_locked=False)
        for i, p in enumerate(STATUSES)
    ]
    monkeypatch.setattr(worktrees, "list_worktrees", lambda cwd: wts)

    async def fake_state(path):
        return ComposeState(statuses[str(path)], None)

    async def fake_usage():
        return {}

    monkeypatch.setattr(compose, "get_state", fake_state)
    monkeypatch.setattr(compose, "get_usage", fake_usage)
    seen = []

    async def run() -> None:
        app = app_module.WtApp(repo_root=Path("/srv"), cwd=Path("/"))
        async with app.run_test(size=(160, 20)) as pilot:
            await pilot.pause()
            table = app.query_one(DataTable)
            for step in steps:
                await step(pilot, statuses)
                await pilot.pause()
                order = [row.key.value for row in table.ordered_rows]
                cursor = order[table.cursor_coordinate.row]
                seen.append((order, cursor, table.columns["status"].label.plain))

    asyncio.run(run())
    return seen


async def _press_o(pilot, statuses):
    await pilot.press("o")


async def _click_status_header(pilot, statuses):
    await pilot.click(DataTable, offset=STATUS_HEADER)


async def _start_no_compose_and_refresh(pilot, statuses):
    statuses["/srv/no-compose"] = Status.RUNNING
    await pilot.press("r")


def test_o_toggles_sort_by_status_and_cursor_follows_its_worktree(monkeypatch):
    sorted_view, unsorted_view = _run(monkeypatch, [_press_o, _press_o])
    assert sorted_view == (
        ["/srv/running", "/srv/main", "/srv/no-compose"],
        "/srv/main",
        "Status ▾",
    )
    assert unsorted_view == (
        ["/srv/main", "/srv/no-compose", "/srv/running"],
        "/srv/main",
        "Status",
    )


def test_clicking_status_header_sorts(monkeypatch):
    [(order, _, label)] = _run(monkeypatch, [_click_status_header])
    assert (order, label) == (["/srv/running", "/srv/main", "/srv/no-compose"], "Status ▾")


def test_sort_is_reapplied_when_a_status_changes(monkeypatch):
    *_, (order, _, _) = _run(monkeypatch, [_press_o, _start_no_compose_and_refresh])
    assert order == ["/srv/no-compose", "/srv/running", "/srv/main"]


async def _noop(pilot, statuses):
    pass


def test_sort_choice_is_saved(monkeypatch, state_path):
    _run(monkeypatch, [_press_o])
    assert json.loads(state_path.read_text()) == {"sort_by_status": True}
    _run(monkeypatch, [_press_o])
    assert json.loads(state_path.read_text()) == {"sort_by_status": False}


def test_saved_sort_choice_is_restored_on_start(monkeypatch, state_path):
    state_path.write_text('{"sort_by_status": true}')
    [(order, _, label)] = _run(monkeypatch, [_noop])
    assert (order, label) == (["/srv/running", "/srv/main", "/srv/no-compose"], "Status ▾")


def test_unreadable_state_file_starts_unsorted(monkeypatch, state_path):
    state_path.write_text("not json")
    [(order, _, label)] = _run(monkeypatch, [_noop])
    assert (order, label) == (["/srv/main", "/srv/no-compose", "/srv/running"], "Status")
