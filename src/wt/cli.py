from __future__ import annotations

import argparse
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
    except Exception as e:
        print(f"wt: not inside a git repository ({e.__class__.__name__})", file=sys.stderr)
        return 2

    WtApp(repo_root=root, cwd=cwd).run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
