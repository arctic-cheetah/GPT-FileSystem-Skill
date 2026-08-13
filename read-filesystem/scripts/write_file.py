#!/usr/bin/env python3
"""Write encoded text at a byte offset in an existing regular file."""

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
    parser.add_argument("text")
    parser.add_argument("--offset", type=nonnegative_int, default=0)
    parser.add_argument("--encoding", default="utf-8")
    args = parser.parse_args()

    try:
        target = args.path.expanduser().resolve(strict=True)
        if not target.is_file():
            raise ValueError(f"path is not a regular file: {target}")
        data = args.text.encode(args.encoding)
        with target.open("r+b") as stream:
            stream.seek(args.offset)
            written = stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        print(json.dumps({"operation": "write", "path": str(target), "bytes_written": written}))
    except (LookupError, OSError, UnicodeError, ValueError) as exc:
        print(f"write_file: error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
