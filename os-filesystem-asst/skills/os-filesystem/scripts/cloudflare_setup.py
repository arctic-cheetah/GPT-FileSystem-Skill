import re
import subprocess
import sys
from typing import Optional, Tuple

# 1. Ensure your local Python app/service is already running on this port


def run_cloudflare_server(PORT) -> Tuple[Optional[str], Optional[subprocess.Popen]]:
    try:
        # Run cloudflared and capture stderr where the URL is printed
        print(f"Starting Cloudflare Tunnel on port {PORT}...")
        process = subprocess.Popen(
            ["cloudflared", "tunnel", "--url", f"http://0.0.0.0:{PORT}"],
            stderr=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            text=True,
            bufsize=1,
        )

        tunnel_url = "None"
        url_pattern = re.compile(r"https://[a-zA-Z0-9-]+\.trycloudflare\.com")

        # Read stderr line by line until we find the URL
        for line in process.stderr:
            print(
                line, end="", file=sys.stderr
            )  # optional: keep showing cloudflared output
            match = url_pattern.search(line)
            if match:
                tunnel_url = match.group(0)
                print(f"\n✅ Tunnel URL: {tunnel_url}\n")
                break

        if tunnel_url:
            print(f"Public URL: {tunnel_url}")
        else:
            print("Could not find tunnel URL in cloudflared output.")

        # Keep the tunnel running
        # process.wait()
        return tunnel_url, process

    except FileNotFoundError:
        print("Error: 'cloudflared' CLI is not installed or not in your system PATH.")
        print(
            "Please install it from: https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/installation/"
        )
        return "error", ""
    except KeyboardInterrupt:
        print("\nShutting down tunnel...")
        process.terminate()
        return "error", ""
