#!/usr/bin/env python3
"""Recursively search filesystem entry names with a glob pattern."""

import argparse
import fnmatch
import json
import os
import sys
from pathlib import Path


def positive_int(value: str) -> int:
    try:
        number = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"expected an integer, got {value!r}") from exc
    if number < 1:
        raise argparse.ArgumentTypeError("value must be at least 1")
    return number


def metadata(path: Path) -> dict[str, object]:
    stat = path.stat()
    return {
        "name": path.name,
        "path": str(path),
        "type": "directory" if path.is_dir() else "file" if path.is_file() else "other",
        "size": stat.st_size,
        "modified_ns": stat.st_mtime_ns,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", type=Path)
    parser.add_argument("pattern", help="glob pattern matched against each entry name")
    parser.add_argument("--max-results", type=positive_int, default=1000)
    args = parser.parse_args()

    try:
        root = args.root.expanduser().resolve(strict=True)
        if not root.is_dir():
            raise ValueError(f"path is not a directory: {root}")
        results = []
        for current_root, directory_names, file_names in os.walk(root):
            directory_names.sort(key=str.lower)
            file_names.sort(key=str.lower)
            base = Path(current_root)
            for name in [*directory_names, *file_names]:
                if fnmatch.fnmatch(name, args.pattern):
                    results.append(metadata(base / name))
                    if len(results) >= args.max_results:
                        print(json.dumps(results, ensure_ascii=False))
                        return 0
        print(json.dumps(results, ensure_ascii=False))
    except (OSError, ValueError) as exc:
        print(f"search_directory: error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
