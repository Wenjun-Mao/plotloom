"""One-shot CLI transport; all dispatch ownership stays in Plotloom."""

import argparse
import json
import os
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["queue", "bridge-health"])
    parser.add_argument("--thread")
    parser.add_argument("--message")
    args = parser.parse_args(argv)
    if args.command == "queue" and (not args.thread or not args.message):
        parser.error("queue requires --thread and --message")
    token = Path(os.environ["PLOTLOOM_CODEX_BRIDGE_TOKEN_FILE"]).read_text().strip()
    url = os.environ["PLOTLOOM_CODEX_BRIDGE_URL"].rstrip("/")
    payload = {"thread": args.thread, "message": args.message}
    request = Request(
        url + ("/queue" if args.command == "queue" else "/healthz"),
        data=json.dumps(payload).encode() if args.command == "queue" else None,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )
    try:
        # Never retry: a lost response may follow a successful native queue.
        with urlopen(request, timeout=28) as response:
            result = json.load(response)
    except (HTTPError, URLError, TimeoutError, OSError, ValueError):
        print("Native Codex bridge did not acknowledge the request.", file=sys.stderr)
        return 1
    if args.command == "bridge-health":
        print("Native Codex bridge is available.")
        return 0
    return int(result["returncode"])


if __name__ == "__main__":
    raise SystemExit(main())
