from pathlib import Path

from wt.worktrees import parse_porcelain

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
    assert hash(worktrees[0]) != hash(worktrees[1])
