#!/usr/bin/env python3
"""Explicitly open and close a regular file handle."""

import argparse
import json
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path)
    args = parser.parse_args()

    try:
        target = args.path.expanduser().resolve(strict=True)
        if not target.is_file():
            raise ValueError(f"path is not a regular file: {target}")
        stream = target.open("rb")
        stream.close()
        print(json.dumps({"operation": "close", "path": str(target), "closed": stream.closed}))
    except (OSError, ValueError) as exc:
        print(f"close_file: error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
