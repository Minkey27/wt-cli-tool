import pytest

from wt.app import _activity_cell, _format_age


@pytest.mark.parametrize(
    ("seconds", "expected"),
    [
        (30, "just now"),
        (5 * 60, "5m ago"),
        (3 * 3600, "3h ago"),
        (2 * 86400, "2d ago"),
        (21 * 86400, "3w ago"),
    ],
)
def test_format_age(seconds, expected):
    assert _format_age(seconds) == expected


NOW = 1_000_000.0


def test_activity_cell_shows_claude_session_age():
    cell = _activity_cell(claude=NOW - 300, git=NOW - 60, now=NOW)
    assert (cell.plain, cell.style) == ("5m ago", "")


def test_activity_cell_falls_back_to_git_marked_as_such():
    cell = _activity_cell(claude=None, git=NOW - 7200, now=NOW)
    assert (cell.plain, cell.style) == ("git 2h ago", "dim")


def test_activity_cell_is_dash_without_any_activity():
    cell = _activity_cell(claude=None, git=None, now=NOW)
    assert (cell.plain, cell.style) == ("—", "dim")
