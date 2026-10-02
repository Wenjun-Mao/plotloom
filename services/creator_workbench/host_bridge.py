"""Mac-only, authenticated adapter for the supported native queue CLI."""

import argparse
import hmac
import json
import subprocess
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from uuid import UUID


class QueueBridge:
    def __init__(self, executable: Path, settings: Path, token: str):
        self.executable = executable
        self.settings = settings
        self.token = token

    def queue(self, payload):
        if not isinstance(payload, dict) or set(payload) != {"thread", "message"}:
            raise ValueError("invalid queue request")
        if not isinstance(payload["thread"], str):
            raise TypeError("invalid thread ID")
        thread = str(UUID(payload["thread"]))
        settings = json.loads(self.settings.read_text())["settings"]
        allowed = {settings[role].get("taskId") for role in ("text", "image")}
        message = payload["message"]
        if (
            thread not in allowed
            or not isinstance(message, str)
            or not 1 <= len(message) <= 262144
        ):
            raise ValueError("queue request is not bound to a configured specialist")
        try:
            result = subprocess.run(
                [
                    str(self.executable),
                    "queue",
                    "--thread",
                    thread,
                    "--message",
                    message,
                ],
                capture_output=True,
                timeout=25,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            return {"returncode": 1}
        # CLI stdout/stderr can include the message; neither is logged or returned.
        return {"returncode": result.returncode}


def handler_for(bridge: QueueBridge):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            pass

        def reply(self, status, payload):
            body = json.dumps(payload).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def authenticated(self):
            supplied = self.headers.get("Authorization", "")
            if not hmac.compare_digest(supplied, f"Bearer {bridge.token}"):
                self.reply(401, {"error": "unauthorized"})
                return False
            return True

        def do_GET(self):
            if not self.authenticated():
                return
            if self.path != "/healthz":
                self.reply(404, {"error": "not_found"})
                return
            self.reply(200 if bridge.executable.is_file() else 503, {"status": "ok"})

        def do_POST(self):
            if not self.authenticated():
                return
            if self.path != "/queue":
                self.reply(404, {"error": "not_found"})
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if not 1 <= length <= 1048576:
                    raise ValueError("invalid request size")
                self.connection.settimeout(5)
                payload = json.loads(self.rfile.read(length))
                result = bridge.queue(payload)
            except (ValueError, TypeError, KeyError, OSError):
                self.reply(400, {"error": "invalid_queue_request"})
                return
            self.reply(200, result)

    return Handler


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--executable", type=Path, required=True)
    parser.add_argument("--settings", type=Path, required=True)
    parser.add_argument("--token-file", type=Path, required=True)
    args = parser.parse_args()
    token = args.token_file.read_text().strip()
    if len(token) < 32:
        raise ValueError("bridge token must contain at least 32 characters")
    bridge = QueueBridge(args.executable, args.settings, token)
    ThreadingHTTPServer(("127.0.0.1", 8842), handler_for(bridge)).serve_forever()


if __name__ == "__main__":
    main()
