#!/usr/bin/env python3
"""Run an executable as a child process."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Sequence


DEFAULT_TIMEOUT_SECONDS = 60.0
FAILURE_EXIT_CODE = 1
TIMEOUT_EXIT_CODE = 124
SIGNAL_EXIT_CODE_BASE = 128
OUTPUT_ENCODING = "utf-8"
OUTPUT_ERROR_POLICY = "replace"


def positive_number(value: str) -> float:
    """Parse a positive timeout value."""
    try:
        number = float(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"expected a number, got {value!r}") from exc
    if number <= 0:
        raise argparse.ArgumentTypeError("value must be greater than zero")
    return number


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("program", type=Path, help="path to an executable file")
    parser.add_argument(
        "arguments", nargs="*", help="arguments passed directly to the program"
    )
    parser.add_argument(
        "--cwd", type=Path, help="working directory for the child process"
    )
    parser.add_argument(
        "--timeout",
        type=positive_number,
        default=DEFAULT_TIMEOUT_SECONDS,
        help=f"timeout in seconds (default: {DEFAULT_TIMEOUT_SECONDS})",
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="print the launch details only"
    )
    return parser


def resolve_program(path: Path, *, require_exists: bool) -> Path:
    program = path.expanduser().resolve(strict=require_exists)
    if require_exists and not program.is_file():
        raise ValueError(f"program is not a regular file: {program}")
    return program


def resolve_working_directory(
    path: Path | None, program: Path, *, require_exists: bool
) -> Path:
    directory = (
        (path if path is not None else program.parent)
        .expanduser()
        .resolve(strict=require_exists)
    )
    if require_exists and not directory.is_dir():
        raise ValueError(f"working directory is not a directory: {directory}")
    return directory


def normalize_exit_code(returncode: int) -> int:
    """Map a POSIX signal termination onto a portable exit code."""
    if returncode < 0:
        return SIGNAL_EXIT_CODE_BASE - returncode
    return returncode


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        program = resolve_program(args.program, require_exists=not args.dry_run)
        working_directory = resolve_working_directory(
            args.cwd, program, require_exists=not args.dry_run
        )
        command = [str(program), *args.arguments]
        launch_details = {
            "operation": "run",
            "command": command,
            "cwd": str(working_directory),
            "timeout": args.timeout,
            "dry_run": args.dry_run,
        }

        if args.dry_run:
            print(json.dumps(launch_details, ensure_ascii=False))
            return 0

        # An argument list with shell=False is the one launch form that behaves
        # identically on every platform. POSIX passes the list straight to
        # execvp as argv; Windows joins it with subprocess.list2cmdline and the
        # child's runtime parses it back into argv. With shell=True a POSIX
        # shell would instead swallow the arguments as its own positional
        # parameters, and cmd.exe would reinterpret shell metacharacters.
        completed = subprocess.run(
            command,
            cwd=working_directory,
            env=os.environ.copy(),
            check=False,
            capture_output=True,
            encoding=OUTPUT_ENCODING,
            errors=OUTPUT_ERROR_POLICY,
            timeout=args.timeout,
            shell=False,
        )
        sys.stdout.write(completed.stdout)
        sys.stderr.write(completed.stderr)
        return normalize_exit_code(completed.returncode)
    except subprocess.TimeoutExpired as exc:
        print(
            f"run_file: error: process timed out after {exc.timeout} seconds",
            file=sys.stderr,
        )
        return TIMEOUT_EXIT_CODE
    except (OSError, UnicodeError, ValueError) as exc:
        # The operating system decides whether a file can be executed, so a
        # rejected launch is reported exactly as the OS raised it.
        print(f"run_file: error: {exc}", file=sys.stderr)
        return FAILURE_EXIT_CODE


if __name__ == "__main__":
    raise SystemExit(main())
