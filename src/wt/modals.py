from __future__ import annotations

from textual import events
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Label, Static


class ConfirmTeardownModal(ModalScreen[bool]):
    """Yes/no modal. Returns True if user pressed 'y'."""

    DEFAULT_CSS = """
    ConfirmTeardownModal {
        align: center middle;
    }
    ConfirmTeardownModal > Vertical {
        background: $surface;
        border: thick $warning;
        padding: 1 2;
        width: 60;
        height: auto;
    }
    """

    def __init__(self, branch: str) -> None:
        super().__init__()
        self._branch = branch

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label(f"Teardown branch '{self._branch}'?", id="confirm-title")
            yield Static("This drops volumes and removes the worktree.")
            yield Static("")
            yield Static("[y] yes    [any other key] cancel")

    def on_key(self, event: events.Key) -> None:
        self.dismiss(event.key.lower() == "y")


class ErrorModal(ModalScreen[None]):
    """Scrollable error-detail modal. Esc closes."""

    DEFAULT_CSS = """
    ErrorModal {
        align: center middle;
    }
    ErrorModal > Vertical {
        background: $surface;
        border: thick $error;
        padding: 1 2;
        width: 90%;
        height: 80%;
    }
    ErrorModal Static#error-body {
        height: 1fr;
        overflow-y: scroll;
    }
    """

    def __init__(self, title: str, body: str) -> None:
        super().__init__()
        self._title = title
        self._body = body

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label(self._title, id="error-title")
            yield Static(self._body, id="error-body")
            yield Static("[esc] close")

    def on_key(self, event: events.Key) -> None:
        if event.key == "escape":
            self.dismiss()
