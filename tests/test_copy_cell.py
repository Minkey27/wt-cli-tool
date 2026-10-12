import asyncio
from pathlib import Path

import pytest
from textual.widgets import DataTable

from wt import app as app_module
from wt import compose, worktrees
from wt.compose import ComposeState, Status

# Under $HOME so the Path cell shows "~/..." and the copy must expand it.
WT_PATH = Path.home() / "repos" / "feature-branch-with-a-long-name"

# Column x-offsets inside the table (declared width + 1 cell padding each side):
# Branch 0-41, Status 42-55, URL 56-83, Path 84+. Row 0 sits under the header.
BRANCH_CELL = (10, 1)
STATUS_CELL = (45, 1)
URL_CELL = (60, 1)
PATH_CELL = (90, 1)
PAST_LAST_COLUMN = (150, 1)  # Path content ("~/repos/...") ends around x=125


def _run_click(monkeypatch, offset, *, double=True, branch="feat/x", head="abc1234") -> list[str]:
    """Mount the app against one fake worktree, click at `offset`, return what was copied."""
    wt = worktrees.Worktree(path=WT_PATH, branch=branch, head=head, is_main=False, is_locked=False)
    monkeypatch.setattr(worktrees, "list_worktrees", lambda cwd: [wt])

    async def fake_state(path):
        return ComposeState(Status.RUNNING, "http://localhost:8000")

    monkeypatch.setattr(compose, "get_state", fake_state)
    copied: list[str] = []
    monkeypatch.setattr(app_module, "_copy_text", lambda app, text: copied.append(text))

    async def run() -> None:
        app = app_module.WtApp(repo_root=Path("/srv/repos"), cwd=Path("/"))
        async with app.run_test(size=(160, 20)) as pilot:
            await pilot.pause()
            click = pilot.double_click if double else pilot.click
            await click(DataTable, offset=offset)
            await pilot.pause()

    asyncio.run(run())
    return copied


@pytest.mark.parametrize(
    ("offset", "expected"),
    [
        (BRANCH_CELL, ["feat/x"]),
        (URL_CELL, ["http://localhost:8000"]),
        (PATH_CELL, [str(WT_PATH)]),
        (STATUS_CELL, []),
        # DataTable reports this empty space as column 0 (Branch) with out_of_bounds set.
        (PAST_LAST_COLUMN, []),
    ],
    ids=["branch", "url", "path", "status", "past-last-column"],
)
def test_double_click_copies_cell_value(monkeypatch, offset, expected):
    assert _run_click(monkeypatch, offset) == expected


def test_single_click_on_path_copies_nothing(monkeypatch):
    assert _run_click(monkeypatch, PATH_CELL, double=False) == []


def test_double_click_on_detached_branch_copies_full_sha(monkeypatch):
    sha = "a" * 40
    assert _run_click(monkeypatch, BRANCH_CELL, branch=None, head=sha) == [sha]
