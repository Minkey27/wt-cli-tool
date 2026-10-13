import os
import subprocess
from pathlib import Path

import pytest

from wt.worktrees import last_claude_activity, last_git_activity, parse_porcelain

FIXTURE = Path(__file__).parent / "fixtures" / "porcelain_simple.txt"


def test_parse_porcelain_returns_all_worktrees():
    text = FIXTURE.read_text()
    worktrees = parse_porcelain(text)
    assert len(worktrees) == 4


def test_first_worktree_is_marked_as_main():
    text = FIXTURE.read_text()
    worktrees = parse_porcelain(text)
    assert worktrees[0].is_main is True
    assert worktrees[1].is_main is False


def test_branch_ref_is_stripped_to_short_name():
    text = FIXTURE.read_text()
    worktrees = parse_porcelain(text)
    assert worktrees[0].branch == "main"
    assert worktrees[1].branch == "bpz-580-improve-download"


def test_detached_head_has_no_branch():
    text = FIXTURE.read_text()
    worktrees = parse_porcelain(text)
    detached = worktrees[2]
    assert detached.branch is None
    assert detached.head.startswith("c5557179f")


def test_locked_flag_is_detected():
    text = FIXTURE.read_text()
    worktrees = parse_porcelain(text)
    assert worktrees[3].is_locked is True
    assert worktrees[0].is_locked is False


def test_path_is_a_pathlib_path():
    text = FIXTURE.read_text()
    worktrees = parse_porcelain(text)
    assert isinstance(worktrees[0].path, Path)
    assert worktrees[0].path == Path("/Users/yyung/Projects/deurdoor")


def test_dataclass_is_hashable():
    text = FIXTURE.read_text()
    worktrees = parse_porcelain(text)
    hash(worktrees[0])  # would raise TypeError if Worktree were unhashable


def _touch(path: Path, mtime: float) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.touch()
    os.utime(path, (mtime, mtime))


def test_last_claude_activity_is_newest_session_mtime(tmp_path):
    session_dir = tmp_path / "-Users-me-Projects-worktrees-feat-x-y"
    _touch(session_dir / "old.jsonl", 1_000)
    _touch(session_dir / "new.jsonl", 2_000)
    _touch(session_dir / "notes.txt", 3_000)  # not a session file
    wt = Path("/Users/me/Projects/worktrees/feat_x.y")
    assert last_claude_activity(wt, projects_dir=tmp_path) == 2_000


def test_last_claude_activity_is_none_without_sessions(tmp_path):
    assert last_claude_activity(Path("/never/opened"), projects_dir=tmp_path) is None


def _git(cwd: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@t", *args],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


@pytest.mark.parametrize("which", ["main", "linked", "linked-relative"])
def test_last_git_activity_is_head_reflog_mtime(tmp_path, which):
    main, linked = tmp_path / "main", tmp_path / "linked"
    _git(tmp_path, "init", "-q", str(main))
    _git(main, "commit", "-q", "--allow-empty", "-m", "init")
    relative = ["--relative-paths"] if which == "linked-relative" else []
    _git(main, "worktree", "add", "-q", *relative, "-b", "feat", str(linked))
    wt = main if which == "main" else linked
    os.utime(wt / _git(wt, "rev-parse", "--git-path", "logs/HEAD"), (1_000, 1_000))
    assert last_git_activity(wt) == 1_000


def test_last_git_activity_is_none_outside_git(tmp_path):
    assert last_git_activity(tmp_path) is None
