from __future__ import annotations

import asyncio
import subprocess
from dataclasses import dataclass
from pathlib import Path


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
