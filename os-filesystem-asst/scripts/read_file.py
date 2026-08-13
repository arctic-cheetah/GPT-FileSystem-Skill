#!/usr/bin/env python3
"""Read an authorized local text file without modifying it."""

from __future__ import annotations

import argparse
import codecs
import sys
from pathlib import Path
from typing import Sequence


DEFAULT_MAX_BYTES = 1_048_576
BINARY_SAMPLE_BYTES = 8_192


def positive_int(value: str) -> int:
    """Parse a strictly positive command-line integer."""
    try:
        number = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"expected an integer, got {value!r}") from exc
    if number < 1:
        raise argparse.ArgumentTypeError("value must be at least 1")
    return number


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Read a local text file and write its contents to standard output."
    )
    parser.add_argument("path", type=Path, help="Path to the text file to read")
    parser.add_argument(
        "--encoding",
        default="utf-8",
        help="Text encoding to use (default: utf-8)",
    )
    parser.add_argument(
        "--errors",
        choices=("strict", "replace", "ignore"),
        default="strict",
        help="Decoding error policy (default: strict)",
    )
    parser.add_argument(
        "--start-line",
        type=positive_int,
        default=1,
        help="First 1-based line to output (default: 1)",
    )
    parser.add_argument(
        "--end-line",
        type=positive_int,
        help="Last 1-based line to output, inclusive",
    )
    parser.add_argument(
        "--max-bytes",
        type=positive_int,
        default=DEFAULT_MAX_BYTES,
        help=f"Maximum accepted file size (default: {DEFAULT_MAX_BYTES})",
    )
    return parser


def validate_path(path: Path, max_bytes: int, encoding: str) -> Path:
    resolved = path.expanduser().resolve(strict=True)
    if not resolved.is_file():
        raise ValueError(f"path is not a regular file: {resolved}")

    size = resolved.stat().st_size
    if size > max_bytes:
        raise ValueError(
            f"file is {size} bytes, exceeding --max-bytes {max_bytes}; "
            "raise the limit only if the file is authorized"
        )

    normalized_encoding = codecs.lookup(encoding).name
    null_bytes_are_expected = normalized_encoding.startswith(("utf-16", "utf-32"))
    with resolved.open("rb") as stream:
        if not null_bytes_are_expected and b"\x00" in stream.read(BINARY_SAMPLE_BYTES):
            raise ValueError(f"file appears to be binary: {resolved}")
    return resolved


def output_lines(
    path: Path,
    *,
    encoding: str,
    errors: str,
    start_line: int,
    end_line: int | None,
) -> None:
    if end_line is not None and end_line < start_line:
        raise ValueError("--end-line must be greater than or equal to --start-line")

    with path.open("r", encoding=encoding, errors=errors, newline="") as stream:
        for line_number, line in enumerate(stream, start=1):
            if line_number < start_line:
                continue
            if end_line is not None and line_number > end_line:
                break
            sys.stdout.write(line)


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        path = validate_path(args.path, args.max_bytes, args.encoding)
        output_lines(
            path,
            encoding=args.encoding,
            errors=args.errors,
            start_line=args.start_line,
            end_line=args.end_line,
        )
    except (LookupError, OSError, UnicodeError, ValueError) as exc:
        print(f"read_file: error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
