#!/usr/bin/env python3
"""Rename a file or directory without changing its parent directory."""

import argparse
import json
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("new_name")
    args = parser.parse_args()

    try:
        source = args.source.expanduser().resolve(strict=True)
        if not args.new_name or Path(args.new_name).name != args.new_name or args.new_name in (".", ".."):
            raise ValueError("new_name must be one filename without directory components")
        target = source.with_name(args.new_name)
        if target.exists():
            raise FileExistsError(f"destination already exists: {target}")
        source.rename(target)
        print(json.dumps({"operation": "rename", "path": str(target), "renamed": True}))
    except (OSError, ValueError) as exc:
        print(f"rename_entry: error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
