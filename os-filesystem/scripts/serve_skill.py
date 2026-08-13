#!/usr/bin/env python3
from __future__ import annotations

"""Browse a directory over HTTP, with this skill's SKILL.md rendered at /skill
and a script-runner landing page at /home.html."""

"""This is required by the assignment specs to allow the marker to view the docs.
TODO: If required they will be also required to run each file individually for marking
"""


import argparse
import html
import os
import shlex
import subprocess
import sys
from http.server import (
    BaseHTTPRequestHandler,
    SimpleHTTPRequestHandler,
    ThreadingHTTPServer,
)
from pathlib import Path
from typing import Sequence
from urllib.parse import parse_qs, urlsplit

# Replaced by the standard library http.server implementation below.
# from flask import Flask, jsonify

# Initialize the Flask application
# app = Flask(__name__)

DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 8000
SCRIPT_SKILL_FILE = Path(__file__).resolve().parent.parent / "SKILL.md"
SCRIPT_DIR = Path(__file__).resolve().parent
COMMAND_TIMEOUT = 30.0
# Scripts the /home.html demo page must not run: the server itself (it would
# block forever) and the Cloudflare tunnel helper, which is not a CLI script.
BLOCKED_SCRIPTS = {"serve_skill.py", "cloudflare_setup.py"}


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
    <p><a href="/">&larr; Back to the directory listing</a> &middot; <a href="/home.html">Run the skill scripts</a></p>
    <pre>{escaped}</pre>
  </main>
</body>
</html>
"""
    return page.encode("utf-8")


def allowed_scripts() -> list[str]:
    """List the runnable skill scripts shipped next to this file."""
    return sorted(
        path.name for path in SCRIPT_DIR.glob("*.py") if path.name not in BLOCKED_SCRIPTS
    )


def run_skill_command(command_line: str) -> dict:
    """Run one skill script from a SKILL.md-style command line.

    Accepts the documented form, for example
    ``python scripts/open_file.py /path/to/file.txt``. Only scripts listed by
    allowed_scripts() may run, with shell=False so no shell syntax is
    interpreted. Returns a dict with the command plus either the exit code and
    captured output, or an "error" message.
    """
    try:
        tokens = shlex.split(command_line, posix=(os.name != "nt"))
    except ValueError as exc:
        return {"command": command_line, "error": f"Could not parse the command: {exc}"}
    if os.name == "nt":
        # shlex's non-POSIX mode keeps the quote characters, so strip them off.
        tokens = [token.strip("\"'") for token in tokens]
    # Drop a leading interpreter token such as python, python3, or py -3.
    if tokens and Path(tokens[0]).name.lower() in {
        "python",
        "python3",
        "python.exe",
        "py",
        "py.exe",
    }:
        tokens = tokens[1:]
        if tokens[:1] == ["-3"]:
            tokens = tokens[1:]
    if not tokens:
        return {"command": command_line, "error": "No script was given."}
    script_name = Path(tokens[0]).name
    if script_name not in allowed_scripts():
        return {
            "command": command_line,
            "error": (
                f"Refusing to run {tokens[0]!r}: only this skill's scripts may run "
                f"({', '.join(allowed_scripts())})."
            ),
        }
    argv = [sys.executable, str(SCRIPT_DIR / script_name), *tokens[1:]]
    try:
        completed = subprocess.run(
            argv, capture_output=True, text=True, timeout=COMMAND_TIMEOUT
        )
    except subprocess.TimeoutExpired:
        return {
            "command": command_line,
            "error": f"Timed out after {COMMAND_TIMEOUT:.0f} seconds.",
            "returncode": 124,
        }
    except OSError as exc:
        return {"command": command_line, "error": f"Launch failed: {exc}"}
    return {
        "command": command_line,
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


def build_home_page(result: dict | None = None) -> bytes:
    """Build the /home.html demo page: one input box that runs skill scripts."""
    command_value = html.escape(result["command"], quote=True) if result else ""
    script_items = "\n".join(
        f"      <li><code>python scripts/{html.escape(name)}</code></li>"
        for name in allowed_scripts()
    )
    if result is None:
        result_section = ""
    else:
        blocks = [
            "    <h2>Result</h2>",
            f"    <p><strong>Command:</strong> <code>{html.escape(result['command'])}</code></p>",
        ]
        if "returncode" in result:
            blocks.append(
                f"    <p><strong>Exit code:</strong> {result['returncode']}</p>"
            )
        if result.get("error"):
            blocks.append(
                f"    <h3>Error</h3>\n    <pre>{html.escape(str(result['error']))}</pre>"
            )
        if result.get("stdout"):
            blocks.append(
                f"    <h3>Standard output</h3>\n    <pre>{html.escape(str(result['stdout']))}</pre>"
            )
        if result.get("stderr"):
            blocks.append(
                f"    <h3>Standard error</h3>\n    <pre>{html.escape(str(result['stderr']))}</pre>"
            )
        result_section = "\n".join(blocks)
    page = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Filesystem Skill - Run the scripts</title>
  <style>
    :root {{ color-scheme: light dark; }}
    body {{ margin: 0; font-family: system-ui, sans-serif; background: Canvas; color: CanvasText; }}
    main {{ width: min(960px, calc(100% - 2rem)); margin: 2rem auto; }}
    a {{ color: LinkText; }}
    .row {{ display: flex; gap: .5rem; }}
    input[type=text] {{ flex: 1; padding: .5rem; font-family: ui-monospace, monospace; }}
    button {{ padding: .5rem 1rem; }}
    pre {{ padding: 1.25rem; overflow-x: auto; border: 1px solid GrayText; border-radius: .5rem;
           background: color-mix(in srgb, Canvas 94%, CanvasText 6%); white-space: pre-wrap;
           overflow-wrap: anywhere; line-height: 1.5; }}
  </style>
</head>
<body>
  <main>
    <h1>Filesystem Skill Demo</h1>
    <p><a href="/">&larr; Back to the directory listing</a> &middot; <a href="/skill">View SKILL.md</a></p>
    <p>Type a command in the SKILL.md format, for example
       <code>python scripts/open_file.py /path/to/file.txt</code>. Only the Python
       scripts shipped in this skill's <code>scripts/</code> directory can run, and
       each run is limited to {COMMAND_TIMEOUT:.0f} seconds.</p>
    <form method="post" action="/home.html">
      <div class="row">
        <input id="cmd" name="cmd" type="text" required autofocus
               placeholder="python scripts/open_file.py /path/to/file.txt"
               value="{command_value}">
        <button type="submit">Run</button>
      </div>
    </form>
    <h2>Available scripts</h2>
    <ul>
{script_items}
    </ul>
{result_section}
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
        # Demo landing page with an input box that runs the skill scripts and
        # prints their output back into the same page.
        home_paths = ("/home", "/home.html")

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

        def send_home_page(self, result: dict | None, *, include_body: bool) -> None:
            self.send_content(
                build_home_page(result),
                "text/html; charset=utf-8",
                include_body=include_body,
            )

        def do_GET(self) -> None:  # noqa: N802 - required by BaseHTTPRequestHandler
            path = urlsplit(self.path).path
            if path in self.rendered_paths:
                self.send_rendered_skill(include_body=True)
            elif path in self.home_paths:
                self.send_home_page(None, include_body=True)
            else:
                super().do_GET()

        def do_HEAD(self) -> None:  # noqa: N802 - required by BaseHTTPRequestHandler
            path = urlsplit(self.path).path
            if path in self.rendered_paths:
                self.send_rendered_skill(include_body=False)
            elif path in self.home_paths:
                self.send_home_page(None, include_body=False)
            else:
                super().do_HEAD()

        def do_POST(self) -> None:  # noqa: N802 - required by BaseHTTPRequestHandler
            if urlsplit(self.path).path not in self.home_paths:
                self.send_error(404, "POST is only supported on /home.html")
                return
            try:
                length = int(self.headers.get("Content-Length") or 0)
            except ValueError:
                length = 0
            form = parse_qs(self.rfile.read(max(length, 0)).decode("utf-8", "replace"))
            command = form.get("cmd", [""])[0].strip()
            result = run_skill_command(command) if command else None
            self.send_home_page(result, include_body=True)

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
