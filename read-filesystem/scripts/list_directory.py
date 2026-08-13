#!/usr/bin/env python3
"""List a directory's immediate entries and basic attributes."""

import argparse
import json
import sys
from pathlib import Path


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
    parser.add_argument("path", type=Path)
    args = parser.parse_args()

    try:
        directory = args.path.expanduser().resolve(strict=True)
        if not directory.is_dir():
            raise ValueError(f"path is not a directory: {directory}")
        entries = [metadata(item) for item in sorted(directory.iterdir(), key=lambda item: item.name.lower())]
        print(json.dumps(entries, ensure_ascii=False))
    except (OSError, ValueError) as exc:
        print(f"list_directory: error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
