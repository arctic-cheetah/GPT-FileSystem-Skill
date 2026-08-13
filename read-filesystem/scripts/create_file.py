#!/usr/bin/env python3
"""Create a new empty file without overwriting an existing entry."""

import argparse
import json
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path)
    parser.add_argument("--parents", action="store_true")
    args = parser.parse_args()

    try:
        target = args.path.expanduser().resolve(strict=False)
        if args.parents:
            target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("xb"):
            pass
        print(json.dumps({"operation": "create", "path": str(target), "created": True}))
    except OSError as exc:
        print(f"create_file: error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
