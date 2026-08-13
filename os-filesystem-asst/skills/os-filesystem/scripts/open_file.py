#!/usr/bin/env python3
"""Open a regular file read-only and report its metadata."""

import argparse
import json
import os
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
        with target.open("rb") as stream:
            stat = os.fstat(stream.fileno())
            result = {"operation": "open", "path": str(target), "size": stat.st_size}
        print(json.dumps(result))
    except (OSError, ValueError) as exc:
        print(f"open_file: error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
