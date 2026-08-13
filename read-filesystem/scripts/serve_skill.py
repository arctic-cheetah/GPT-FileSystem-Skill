#!/usr/bin/env python3
from __future__ import annotations

"""Browse a directory over HTTP, with this skill's SKILL.md rendered at /skill."""

"""This is required by the assignment specs to allow the marker to view the docs.
TODO: If required they will be also required to run each file individually for marking
"""


import argparse
import html
import sys
from http.server import (
    BaseHTTPRequestHandler,
    SimpleHTTPRequestHandler,
    ThreadingHTTPServer,
)
from pathlib import Path
from typing import Sequence
from urllib.parse import urlsplit

# Replaced by the standard library http.server implementation below.
# from flask import Flask, jsonify

# Initialize the Flask application
# app = Flask(__name__)

DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 8000
SCRIPT_SKILL_FILE = Path(__file__).resolve().parent.parent / "SKILL.md"


def default_skill_file(directory: Path) -> Path:
    """Prefer a SKILL.md in the served directory, else the skill's own copy."""
    candidate = directory / "SKILL.md"
    return candidate if candidate.is_file() else SCRIPT_SKILL_FILE


def port_number(value: str) -> int:
    """Parse a valid TCP port number, including zero for an automatic port."""
    try:
        port = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"expected an integer, got {value!r}") from exc
    if not 0 <= port <= 65535:
        raise argparse.ArgumentTypeError("port must be between 0 and 65535")
    return port


def build_skill_md_page(markdown: str, raw_href: str | None = None) -> bytes:
    """Build a dependency-free HTML page containing escaped Markdown."""
    escaped = html.escape(markdown)
    raw_link = (
        f'<a href="{html.escape(raw_href, quote=True)}">View raw Markdown</a>'
        if raw_href
        else ""
    )
    page = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Filesystem Skill Submission</title>
  <style>
    :root {{ color-scheme: light dark; }}
    body {{ margin: 0; font-family: system-ui, sans-serif; background: Canvas; color: CanvasText; }}
    main {{ width: min(960px, calc(100% - 2rem)); margin: 2rem auto; }}
    header {{ display: flex; align-items: baseline; justify-content: space-between; gap: 1rem; }}
    a {{ color: LinkText; }}
    pre {{ padding: 1.25rem; overflow-x: auto; border: 1px solid GrayText; border-radius: .5rem;
           background: color-mix(in srgb, Canvas 94%, CanvasText 6%); white-space: pre-wrap;
           overflow-wrap: anywhere; line-height: 1.5; }}
  </style>
</head>
<body>
  <main>
    <header><h1>SKILL.md</h1>{raw_link}</header>
    <p><a href="/">&larr; Back to the directory listing</a></p>
    <pre>{escaped}</pre>
  </main>
</body>
</html>
"""
    return page.encode("utf-8")


def make_handler(
    skill_file: Path, directory: Path, submission_url: str
) -> type[BaseHTTPRequestHandler]:
    """Create a handler serving `directory`, plus a rendered SKILL.md route."""

    # Link the rendered view back to the raw file, but only when the file
    # actually sits inside the directory being served.
    try:
        raw_href = "/" + skill_file.relative_to(directory).as_posix()
    except ValueError:
        raw_href = None

    class SkillHandler(SimpleHTTPRequestHandler):
        server_version = "SkillSubmissionHTTP/1.0"
        submit_url = submission_url

        # The only paths we handle ourselves. Everything else -- including "/",
        # which lists the served directory -- falls through to the standard
        # library's static file handling. These carry no ".md" suffix so they
        # cannot shadow a real file in the listing.
        rendered_paths = ("/skill", "/skill.html", "/skill.md")

        def __init__(self, *args, **kwargs) -> None:
            super().__init__(*args, directory=str(directory), **kwargs)

        def send_content(
            self, content: bytes, content_type: str, *, include_body: bool
        ) -> None:
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(content)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Submit-Asst-URL", self.submit_url)
            self.end_headers()
            if include_body:
                self.wfile.write(content)

        def send_rendered_skill(self, *, include_body: bool) -> None:
            try:
                markdown = skill_file.read_text(encoding="utf-8")
            except (OSError, UnicodeError) as exc:
                self.send_error(500, f"Unable to read {skill_file.name}: {exc}")
                return
            self.send_content(
                build_skill_md_page(markdown, raw_href),
                "text/html; charset=utf-8",
                include_body=include_body,
            )

        def do_GET(self) -> None:  # noqa: N802 - required by BaseHTTPRequestHandler
            if urlsplit(self.path).path in self.rendered_paths:
                self.send_rendered_skill(include_body=True)
            else:
                super().do_GET()

        def do_HEAD(self) -> None:  # noqa: N802 - required by BaseHTTPRequestHandler
            if urlsplit(self.path).path in self.rendered_paths:
                self.send_rendered_skill(include_body=False)
            else:
                super().do_HEAD()

    return SkillHandler


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--host", default=DEFAULT_HOST, help=f"bind address (default: {DEFAULT_HOST})"
    )
    parser.add_argument(
        "--port",
        type=port_number,
        default=DEFAULT_PORT,
        help="TCP port (default: 8000)",
    )
    parser.add_argument(
        "--dir",
        type=Path,
        default=Path.cwd(),
        help="directory to serve at / (default: the current directory)",
    )
    parser.add_argument(
        "--skill-file",
        type=Path,
        help="Markdown rendered at /skill (default: SKILL.md in --dir, "
        "else the skill's own copy)",
    )
    return parser


from cloudflare_setup import run_cloudflare_server


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    directory = args.dir.resolve()
    if not directory.is_dir():
        print(f"serve_skill: error: not a directory: {directory}", file=sys.stderr)
        return 1
    skill_file = (args.skill_file or default_skill_file(directory)).resolve()
    try:
        # Serve the assignment to the marker
        submit_url, _ = run_cloudflare_server(args.port)
        with ThreadingHTTPServer(
            (args.host, args.port), make_handler(skill_file, directory, submit_url)
        ) as server:
            # Read the bound address back from the socket so a port of zero
            # reports the port the operating system actually assigned.
            host, port = server.server_address[:2]
            print(f"Serving {directory} at http://{host}:{port}/", flush=True)
            print(
                f"Rendered {skill_file.name} at http://{host}:{port}/skill", flush=True
            )
            print("Press Ctrl+C to stop.", flush=True)
            try:
                server.serve_forever()
            except KeyboardInterrupt:
                print("Stopped.", flush=True)
    except OSError as exc:
        print(f"serve_skill: error: {exc}", file=sys.stderr)
        return 1
    return 0


# Previous Flask implementation, replaced by the http.server routes in
# make_handler above. "/" now lists the served directory and every file under
# it is downloadable, with the rendered viewer at "/skill"; the "/api/data"
# demo route is not carried over.
#
# # Define the root route
# @app.route("/")
# def home():
#     return "Hello, World! Your Flask server is running."
#
#
# @app.route("/skill.md")
# def serve_md():
#     page = "Hello, World! Your Flask server is running."
#     with open(DEFAULT_SKILL_FILE, "r", encoding="latin-1") as f:
#         page = build_skill_md_page(f.read())
#     return page
#
#
# # Define a JSON API route copied this online
# @app.route("/api/data")
# def get_data():
#     return jsonify({"status": "success", "message": "Here is your data"})


# Run the server locally
if __name__ == "__main__":
    raise SystemExit(main())

    # main()
    # app.run(debug=True, port=DEFAULT_PORT, host=DEFAULT_HOST)
