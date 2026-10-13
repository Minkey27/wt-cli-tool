from __future__ import annotations

import asyncio
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

CLAUDE_PROJECTS_DIR = Path.home() / ".claude" / "projects"


@dataclass(frozen=True)
class Worktree:
    path: Path
    branch: str | None  # None for detached HEAD
    head: str
    is_main: bool
    is_locked: bool


def list_worktrees(cwd: Path | None = None) -> list[Worktree]:
    """Enumerate git worktrees of the repo containing ``cwd``."""
    result = subprocess.run(
        ["git", "worktree", "list", "--porcelain"],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
    )
    return parse_porcelain(result.stdout)


def parse_porcelain(text: str) -> list[Worktree]:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    blocks = [block for block in text.strip().split("\n\n") if block.strip()]
    return [_parse_block(block, is_main=(i == 0)) for i, block in enumerate(blocks)]


def _parse_block(block: str, *, is_main: bool) -> Worktree:
    fields: dict[str, str] = {}
    flags: set[str] = set()
    for line in block.splitlines():
        if " " in line:
            key, value = line.split(" ", 1)
            fields[key] = value
        elif line.strip():
            flags.add(line.strip())
    return Worktree(
        path=Path(fields["worktree"]),
        branch=_branch_short_name(fields.get("branch")),
        head=fields.get("HEAD", ""),
        is_main=is_main,
        is_locked="locked" in flags,
    )


def _branch_short_name(ref: str | None) -> str | None:
    if ref is None:
        return None
    prefix = "refs/heads/"
    return ref[len(prefix) :] if ref.startswith(prefix) else ref


def last_claude_activity(worktree: Path, projects_dir: Path = CLAUDE_PROJECTS_DIR) -> float | None:
    """Unix time of the latest Claude Code session activity in ``worktree``, if any.

    Claude Code appends each session to a JSONL file in a directory named after
    the session's working directory, with every non-alphanumeric character
    replaced by ``-``. The newest file's mtime is the last time anyone talked to
    Claude there.
    """
    session_dir = projects_dir / re.sub(r"[^A-Za-z0-9]", "-", str(worktree))
    return max((p.stat().st_mtime for p in session_dir.glob("*.jsonl")), default=None)


def last_git_activity(worktree: Path) -> float | None:
    """Unix time HEAD last moved (commit, checkout, reset) in ``worktree``, if known.

    Git appends every HEAD move to ``logs/HEAD`` in the worktree's git dir: the
    ``.git`` directory of the main worktree, or the dir a linked worktree's
    ``.git`` file points at (absolute, or relative with ``--relative-paths``).
    """
    git_dir = worktree / ".git"
    try:
        if git_dir.is_file():
            git_dir = worktree / git_dir.read_text().removeprefix("gitdir:").strip()
        return (git_dir / "logs" / "HEAD").stat().st_mtime
    except OSError:
        return None


async def remove_worktree(path: Path) -> tuple[int, str]:
    """Run `git worktree remove --force <path>` asynchronously."""
    proc = await _spawn("git", "worktree", "remove", "--force", str(path))
    out, _ = await proc.communicate()
    return proc.returncode, out.decode("utf-8", errors="replace")


async def _spawn(*args: str) -> asyncio.subprocess.Process:
    return await asyncio.create_subprocess_exec(
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )


def repo_root(cwd: Path | None = None) -> Path:
    """Return the path of the main worktree of the repo containing ``cwd``."""
    result = subprocess.run(
        ["git", "rev-parse", "--path-format=absolute", "--git-common-dir"],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
    )
    git_common_dir = Path(result.stdout.strip())
    return git_common_dir.parent
