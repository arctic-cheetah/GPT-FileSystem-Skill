#!/usr/bin/env python3
"""Apply an octal permission mode to one regular file."""

from __future__ import annotations

import argparse
import json
import os
import stat
import sys
from pathlib import Path


def octal_mode(value: str) -> int:
    """Parse a three- or four-digit octal permission mode."""
    normalized = value.removeprefix("0o")
    if len(normalized) not in (3, 4) or any(character not in "01234567" for character in normalized):
        raise argparse.ArgumentTypeError(
            "mode must contain three or four octal digits, for example 444, 644, or 0755"
        )
    mode = int(normalized, 8)
    if mode > 0o7777:
        raise argparse.ArgumentTypeError("mode must be between 0000 and 07777")
    return mode


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path)
    parser.add_argument("mode", type=octal_mode)
    args = parser.parse_args()

    try:
        target = args.path.expanduser().resolve(strict=True)
        if not target.is_file():
            raise ValueError(f"path is not a regular file: {target}")
        os.chmod(target, args.mode)
        effective_mode = stat.S_IMODE(target.stat().st_mode)
        print(
            json.dumps(
                {
                    "operation": "chmod",
                    "path": str(target),
                    "requested_mode": format(args.mode, "04o"),
                    "effective_mode": format(effective_mode, "04o"),
                }
            )
        )
    except (OSError, ValueError) as exc:
        print(f"chmod_file: error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
