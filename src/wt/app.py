from __future__ import annotations

import asyncio
import contextlib
from pathlib import Path

from rich.text import Text
from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import DataTable, Footer, Header, Static

from wt import compose, worktrees
from wt.compose import Status
from wt.modals import ConfirmTeardownModal, ErrorModal

STATUS_DISPLAY: dict[Status, tuple[str, str]] = {
    Status.RUNNING: ("● running", "green"),
    Status.PARTIAL: ("◐ partial", "yellow"),
    Status.STOPPED: ("○ stopped", ""),
    Status.NO_COMPOSE: ("─ no-comp", "dim"),
    Status.ERROR: ("✗ error", "red"),
}


class RowState:
    """Mutable per-row state held by the app."""

    def __init__(self, wt: worktrees.Worktree) -> None:
        self.wt = wt
        self.resolved_path = wt.path.resolve()
        self.status: Status | None = None
        self.url: str | None = None
        self.locked: bool = False  # True while an action is in flight
        self.last_error: str | None = None


class WtApp(App):
    BINDINGS = [
        Binding("s", "start_selected", "Start"),
        Binding("x", "stop_selected", "Stop"),
        Binding("t", "teardown_selected", "Teardown"),
        Binding("enter", "show_error", "Show Error", show=False),
        Binding("r", "refresh", "Refresh"),
        Binding("q", "quit", "Quit"),
        Binding("ctrl+c", "quit", "Quit", show=False),
    ]

    CSS = """
    Screen { layout: vertical; }
    DataTable { height: 1fr; }
    #toast { dock: bottom; height: 3; background: $error 30%; color: $text; padding: 0 1; }
    """

    def __init__(self, repo_root: Path, cwd: Path) -> None:
        super().__init__()
        self._repo_root = repo_root
        self._cwd = cwd.resolve()
        self._rows: dict[str, RowState] = {}
        self._table: DataTable | None = None
        self._toast: Static | None = None

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        self._table = DataTable(cursor_type="row", zebra_stripes=False)
        self._table.add_column("Branch", key="branch", width=40)
        self._table.add_column("Status", key="status", width=12)
        self._table.add_column("URL", key="url", width=26)
        self._table.add_column("Path", key="path")
        yield self._table
        self._toast = Static("", id="toast")
        self._toast.display = False
        yield self._toast
        yield Footer()

    async def on_mount(self) -> None:
        self.title = f"wt — {self._repo_root.name}"
        await self._reconcile_worktrees()
        self.refresh_states()
        self.set_interval(2.0, self.refresh_states)

    async def _reconcile_worktrees(self) -> None:
        """Sync the table to current `git worktree list` output.

        Adds rows for new worktrees. Removes rows whose worktree has
        disappeared, except for rows currently locked by an in-flight
        action — those are kept so the running worker can finish.
        Surviving rows keep their cached status / url / lock / error state.
        """
        try:
            wts = await asyncio.to_thread(worktrees.list_worktrees, self._cwd)
        except Exception:
            return
        assert self._table is not None
        new_keys = {str(wt.path) for wt in wts}
        for key in list(self._rows):
            if key in new_keys or self._rows[key].locked:
                continue
            self._remove_row(key)
        for wt in wts:
            key = str(wt.path)
            if key in self._rows:
                continue
            label = wt.branch or f"(detached {wt.head[:7]})"
            self._rows[key] = RowState(wt)
            self._table.add_row(label, "…", "—", _abbrev_path(wt.path), key=key)
        self.sub_title = f"{len(self._rows)} worktrees"

    @work(exclusive=True, group="refresh")
    async def refresh_states(self) -> None:
        await self._reconcile_worktrees()
        tasks = [self._refresh_row(key) for key, info in self._rows.items() if not info.locked]
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _refresh_row(self, key: str) -> None:
        info = self._rows[key]
        state = await compose.get_state(info.wt.path)
        info.status = state.status
        info.url = state.webapp_url
        self._render_row(key)

    def _render_row(self, key: str) -> None:
        info = self._rows[key]
        assert self._table is not None
        status = info.status or Status.NO_COMPOSE
        text, color = STATUS_DISPLAY[status]
        self._table.update_cell(key, "status", Text(text, style=color))
        if info.url:
            self._table.update_cell(
                key,
                "url",
                Text(info.url, style=f"link={info.url} underline cyan"),
            )
        else:
            self._table.update_cell(key, "url", Text("—", style="dim"))

    def _remove_row(self, key: str) -> None:
        """Drop a row from the table and forget its state, keeping the cursor on
        the same logical worktree (see `_cursor_after_removal`)."""
        assert self._table is not None
        try:
            deleted_idx = self._table.get_row_index(key)
        except Exception:
            deleted_idx = None
        cursor_row = self._table.cursor_coordinate.row
        with contextlib.suppress(Exception):
            self._table.remove_row(key)
        self._rows.pop(key, None)
        if deleted_idx is not None and self._table.row_count:
            self._table.move_cursor(
                row=_cursor_after_removal(deleted_idx, cursor_row, self._table.row_count)
            )

    def _set_row_spinner(self, key: str, label: str) -> None:
        assert self._table is not None
        self._table.update_cell(key, "status", Text(f"⠹ {label}", style="bold cyan"))

    def _show_toast(self, message: str) -> None:
        assert self._toast is not None
        self._toast.update(message)
        self._toast.display = True
        self.set_timer(5.0, self._hide_toast)

    def _hide_toast(self) -> None:
        assert self._toast is not None
        self._toast.display = False

    def _selected_row_key(self) -> str | None:
        assert self._table is not None
        try:
            row_key, _ = self._table.coordinate_to_cell_key(self._table.cursor_coordinate)
            return None if row_key is None else str(row_key.value)
        except Exception:
            return None

    def action_start_selected(self) -> None:
        key = self._selected_row_key()
        if key is None:
            return
        info = self._rows[key]
        if info.status is Status.NO_COMPOSE or info.locked:
            return
        self.run_worker(self._run_action(key, "starting", compose.start), exclusive=False)

    def action_stop_selected(self) -> None:
        key = self._selected_row_key()
        if key is None:
            return
        info = self._rows[key]
        if info.status is Status.NO_COMPOSE or info.locked:
            return
        self.run_worker(self._run_action(key, "stopping", compose.stop), exclusive=False)

    async def _run_action(self, key: str, label: str, fn) -> None:
        info = self._rows[key]
        info.locked = True
        self._set_row_spinner(key, label)
        rc, output = await fn(info.wt.path)
        info.locked = False
        if rc != 0:
            info.last_error = output
            self._render_error_status(key, output)
        else:
            await self._refresh_row(key)

    def _render_error_status(self, key: str, output: str) -> None:
        assert self._table is not None
        self._table.update_cell(key, "status", Text("✗ error", style="bold red"))
        lines = [ln for ln in output.strip().splitlines() if ln.strip()]
        snippet = " | ".join(lines[-3:]) if lines else "command failed"
        self._show_toast(f"action failed: {snippet}")

    def action_teardown_selected(self) -> None:
        key = self._selected_row_key()
        if key is None:
            return
        info = self._rows[key]
        if info.locked:
            return
        if info.wt.is_main:
            self._show_toast("main worktree cannot be torn down")
            return
        if info.resolved_path == self._cwd or self._cwd.is_relative_to(info.resolved_path):
            self._show_toast("cd out of this worktree first — your shell is inside it")
            return

        def proceed(confirmed: bool | None) -> None:
            if confirmed:
                self.run_worker(self._do_teardown(key), exclusive=False)

        self.push_screen(
            ConfirmTeardownModal(info.wt.branch or info.wt.head[:7]),
            proceed,
        )

    async def _do_teardown(self, key: str) -> None:
        info = self._rows[key]
        info.locked = True
        self._set_row_spinner(key, "tearing down")

        rc, output = await compose.down(info.wt.path)
        if rc != 0:
            info.locked = False
            info.last_error = output
            self._render_error_status(key, output)
            return

        rc2, output2 = await worktrees.remove_worktree(info.wt.path)
        if rc2 != 0:
            info.locked = False
            info.last_error = output2
            self._render_error_status(key, output2)
            return

        self._remove_row(key)

    def action_show_error(self) -> None:
        key = self._selected_row_key()
        if key is None:
            return
        info = self._rows[key]
        if not info.last_error:
            return
        self.push_screen(ErrorModal(f"Error: {info.wt.branch or info.wt.path}", info.last_error))

    def action_refresh(self) -> None:
        self.refresh_states()


def _cursor_after_removal(deleted_idx: int, cursor_row: int, remaining: int) -> int:
    """Row index the cursor should occupy after the row at `deleted_idx` is removed.

    `cursor_row` is the cursor's index before removal; `remaining` is the number
    of rows left afterwards. Keeps the cursor on the same logical worktree: a
    deletion below the cursor leaves it put, a deletion at-or-above it shifts the
    cursor up one so it tracks the same row (and, when the selected row itself is
    torn down, lands on the row above rather than silently inheriting whatever
    slid up). The result is always clamped into `[0, remaining - 1]`.
    """
    if remaining <= 0:
        return 0
    target = cursor_row - 1 if deleted_idx <= cursor_row else cursor_row
    return max(0, min(target, remaining - 1))


def _abbrev_path(path: Path) -> str:
    home = Path.home()
    try:
        rel = path.relative_to(home)
        return f"~/{rel}"
    except ValueError:
        return str(path)
