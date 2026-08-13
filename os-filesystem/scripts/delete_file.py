#!/usr/bin/env python3
"""Delete one regular file without deleting directories."""

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
        target.unlink()
        print(json.dumps({"operation": "delete", "path": str(target), "deleted": True}))
    except (OSError, ValueError) as exc:
        print(f"delete_file: error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
