import pytest

from wt import state


@pytest.fixture(autouse=True)
def state_path(tmp_path, monkeypatch):
    """Keep tests off the real ~/.local/state/wt/state.json."""
    path = tmp_path / "state.json"
    monkeypatch.setattr(state, "STATE_PATH", path)
    return path
