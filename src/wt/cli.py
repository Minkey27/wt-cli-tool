from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from wt import __version__
from wt.app import WtApp
from wt.worktrees import repo_root


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="wt",
        description="TUI for managing git worktrees and their docker compose stacks.",
    )
    parser.add_argument("--version", action="version", version=f"wt {__version__}")
    parser.parse_args(argv)

    cwd = Path.cwd()
    try:
        root = repo_root(cwd)
    except FileNotFoundError:
        print("wt: 'git' binary not found on PATH", file=sys.stderr)
        return 2
    except subprocess.CalledProcessError:
        print("wt: not inside a git repository", file=sys.stderr)
        return 2

    WtApp(repo_root=root, cwd=cwd).run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
