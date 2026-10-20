"""UI choices remembered across `wt` sessions, such as the status sort."""

from __future__ import annotations

import contextlib
import json
import os
from pathlib import Path

STATE_PATH = (
    Path(os.environ.get("XDG_STATE_HOME") or Path.home() / ".local" / "state") / "wt" / "state.json"
)


def load() -> dict:
    """Return the saved state, or {} when the file is missing or unreadable."""
    try:
        return json.loads(STATE_PATH.read_text())
    except (OSError, ValueError):
        return {}


def save(state: dict) -> None:
    """Write the state. A failed write only forgets a UI choice, so it is ignored."""
    with contextlib.suppress(OSError):
        STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        STATE_PATH.write_text(json.dumps(state, indent=2) + "\n")
