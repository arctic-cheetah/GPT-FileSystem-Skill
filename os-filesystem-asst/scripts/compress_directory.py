#!/usr/bin/env python3
"""Compress a directory into a new ZIP archive without overwriting files."""

from __future__ import annotations

import argparse
import json
import os
import sys
import zipfile
from pathlib import Path


def archive_directory(source: Path, destination: Path) -> tuple[int, int]:
    """Create an archive and return its file and directory entry counts."""
    destination_created = False
    file_count = 0
    directory_count = 0

    try:
        with destination.open("xb") as output:
            destination_created = True
            with zipfile.ZipFile(
                output,
                mode="w",
                compression=zipfile.ZIP_DEFLATED,
                allowZip64=True,
            ) as archive:
                for current_root, directory_names, file_names in os.walk(source):
                    directory_names.sort(key=str.lower)
                    file_names.sort(key=str.lower)
                    current = Path(current_root)
                    included_files = [
                        name for name in file_names if (current / name) != destination
                    ]
                    relative_directory = current.relative_to(source.parent)

                    if not directory_names and not included_files:
                        archive.writestr(
                            relative_directory.as_posix().rstrip("/") + "/", b""
                        )
                        directory_count += 1

                    for file_name in included_files:
                        file_path = current / file_name
                        archive.write(
                            file_path, file_path.relative_to(source.parent).as_posix()
                        )
                        file_count += 1

        destination_created = False
        return file_count, directory_count
    finally:
        if destination_created:
            destination.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="directory to compress")
    parser.add_argument("destination", type=Path, help="new .zip archive path")
    args = parser.parse_args()

    try:
        source = args.source.expanduser().resolve(strict=True)
        if not source.is_dir():
            raise ValueError(f"source is not a directory: {source}")

        destination = args.destination.expanduser().resolve(strict=False)
        if destination.suffix.lower() != ".zip":
            raise ValueError(f"destination must end in .zip: {destination}")
        if not destination.parent.is_dir():
            raise FileNotFoundError(f"destination parent does not exist: {destination.parent}")
        if destination.exists():
            raise FileExistsError(f"destination already exists: {destination}")
        file_count, directory_count = archive_directory(source, destination)
        print(
            json.dumps(
                {
                    "operation": "compress",
                    "source": str(source),
                    "destination": str(destination),
                    "files": file_count,
                    "empty_directories": directory_count,
                    "bytes": destination.stat().st_size,
                }
            )
        )
    except (OSError, ValueError, zipfile.BadZipFile) as exc:
        print(f"compress_directory: error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
