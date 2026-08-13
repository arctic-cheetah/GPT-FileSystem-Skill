#!/usr/bin/env python3
"""Move a file or directory to a collision-free same-filesystem path."""

import argparse
import json
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()

    try:
        source = args.source.expanduser().resolve(strict=True)
        target = args.destination.expanduser().resolve(strict=False)
        if not target.parent.is_dir():
            raise FileNotFoundError(f"destination parent does not exist: {target.parent}")
        if target.exists():
            raise FileExistsError(f"destination already exists: {target}")
        source.rename(target)
        print(json.dumps({"operation": "move", "path": str(target), "moved": True}))
    except OSError as exc:
        print(f"move_entry: error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
