#!/usr/bin/env python3
"""Resize a regular file, defaulting to zero bytes."""

import argparse
import json
import os
import sys
from pathlib import Path


def nonnegative_int(value: str) -> int:
    try:
        number = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"expected an integer, got {value!r}") from exc
    if number < 0:
        raise argparse.ArgumentTypeError("value must be zero or greater")
    return number


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path)
    parser.add_argument("--size", type=nonnegative_int, default=0)
    args = parser.parse_args()

    try:
        target = args.path.expanduser().resolve(strict=True)
        if not target.is_file():
            raise ValueError(f"path is not a regular file: {target}")
        with target.open("r+b") as stream:
            stream.truncate(args.size)
            stream.flush()
            os.fsync(stream.fileno())
        print(json.dumps({"operation": "truncate", "path": str(target), "size": args.size}))
    except (OSError, ValueError) as exc:
        print(f"truncate_file: error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
