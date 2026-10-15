"""Mac-only, authenticated adapter for the supported native queue CLI."""

import argparse
import hmac
import json
import os
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from uuid import UUID


class QueueBridge:
    def __init__(
        self,
        executable: Path,
        settings: Path,
        token: str,
        *,
        source_root: Path | None = None,
        outputs_root: Path | None = None,
        private_root: Path | None = None,
        pool_limits=None,
    ):
        self.executable = executable
        self.settings = settings
        self.token = token
        self.source_root = source_root
        self.outputs_root = outputs_root
        self.private_root = private_root
        self._exec_pool_limits = pool_limits
        self._exec_supervisor = None
        self._exec_supervisor_lock = threading.Lock()

    def exec_supervisor(self):
        if self.source_root is None or self.outputs_root is None or self.private_root is None:
            raise RuntimeError("Codex Exec host roots are not configured")
        with self._exec_supervisor_lock:
            if self._exec_supervisor is None:
                sys.path.insert(0, str(self.source_root / "src"))
                from codex_exec_supervisor import CodexExecSupervisor
                self._exec_supervisor = CodexExecSupervisor(
                    self.executable,
                    source_root=self.source_root,
                    outputs_root=self.outputs_root,
                    private_root=self.private_root,
                    pool_limits=self._exec_pool_limits,
                )
            return self._exec_supervisor

    def exec_profile(self):
        """Observe the exact persisted installation capacity without dispatch."""
        profile = self.exec_supervisor().profile()
        return profile.model_dump(mode="json", by_alias=True)

    def exec_readiness(self):
        """Return safe local login readiness without including CLI output."""
        if any(root is None for root in (self.source_root, self.outputs_root, self.private_root)):
            from plotloom.codex_exec_contracts import CodexExecReadiness
            return CodexExecReadiness(state="unavailable").model_dump(mode="json", by_alias=True)
        import sys
        sys.path.insert(0, str(self.source_root / "src"))
        from plotloom.codex_exec_auth import check_codex_exec_readiness

        readiness = check_codex_exec_readiness(
            self.executable,
            source_root=self.source_root,
            environment=os.environ.copy(),
            forbidden_roots=(self.source_root, self.outputs_root, self.private_root),
        )
        return readiness.model_dump(mode="json", by_alias=True)

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
        if result.returncode != 0:
            return {"returncode": result.returncode}
        try:
            opened = subprocess.run(
                ["/usr/bin/open", f"codex://threads/{thread}"],
                capture_output=True,
                timeout=2,
                check=False,
            )
            wake_state = (
                "open_requested" if opened.returncode == 0 else "open_unconfirmed"
            )
        except (OSError, subprocess.TimeoutExpired):
            wake_state = "open_unconfirmed"
        # Opening is navigation, not a second submission. Never turn an already
        # acknowledged queue into a retryable failure when the open step fails.
        return {"returncode": 0, "wakeState": wake_state}


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
                if self.path == "/exec-profile":
                    try:
                        self.reply(200, bridge.exec_profile())
                    except (OSError, RuntimeError, ValueError, ImportError):
                        self.reply(503, {"error": "codex_exec_profile_unavailable"})
                    return
                if self.path == "/exec-readiness":
                    try:
                        self.reply(200, bridge.exec_readiness())
                    except Exception:
                        self.reply(200, {"state": "unavailable"})
                    return
                if self.path.startswith("/exec-status/"):
                    try:
                        attempt_id = UUID(self.path.removeprefix("/exec-status/"))
                        status = bridge.exec_supervisor().status(attempt_id)
                        self.reply(200, status.model_dump(mode="json", by_alias=True))
                    except (TypeError, ValueError):
                        self.reply(400, {"error": "invalid_codex_exec_status_request"})
                    except Exception:
                        self.reply(503, {"error": "codex_exec_status_unavailable"})
                    return
                self.reply(404, {"error": "not_found"})
                return
            self.reply(200 if bridge.executable.is_file() else 503, {"status": "ok"})

        def do_POST(self):
            if not self.authenticated():
                return
            if self.path == "/exec-admit":
                try:
                    length = int(self.headers.get("Content-Length", "0"))
                    if not 1 <= length <= 1048576:
                        raise ValueError("invalid request size")
                    self.connection.settimeout(5)
                    payload = json.loads(self.rfile.read(length))
                    if not isinstance(payload, dict) or set(payload) != {"attempt"}:
                        raise ValueError("invalid attempt envelope")
                    status = bridge.exec_supervisor().admit(payload["attempt"])
                    self.reply(200, status.model_dump(mode="json", by_alias=True))
                except (ValueError, TypeError, KeyError, OSError):
                    self.reply(409, {"error": "codex_exec_attempt_not_admitted"})
                except Exception:
                    self.reply(503, {"error": "codex_exec_admission_unavailable"})
                return
            control = next((name for name in ("cancel", "suspend", "resume") if self.path.startswith(f"/exec-{name}/")), None)
            if control is not None:
                try:
                    attempt_id = UUID(self.path.removeprefix(f"/exec-{control}/"))
                    length = int(self.headers.get("Content-Length", "0"))
                    if not 1 <= length <= 1048576:
                        raise ValueError("cancel request has an invalid size")
                    self.connection.settimeout(5)
                    payload = json.loads(self.rfile.read(length))
                    if not isinstance(payload, dict) or set(payload) != {"attempt"}:
                        raise ValueError("cancel request must contain one attempt snapshot")
                    attempt = payload["attempt"]
                    if not isinstance(attempt, dict) or str(UUID(str(attempt.get("attemptId")))) != str(attempt_id):
                        raise ValueError("cancel route and attempt identity differ")
                    status = getattr(bridge.exec_supervisor(), control)(attempt)
                    self.reply(200, status.model_dump(mode="json", by_alias=True))
                except (TypeError, ValueError):
                    self.reply(400, {"error": f"invalid_codex_exec_{control}_request"})
                except Exception:
                    self.reply(503, {"error": f"codex_exec_{control}_unavailable"})
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
    parser.add_argument("--source-root", type=Path)
    parser.add_argument("--outputs-root", type=Path)
    parser.add_argument("--private-root", type=Path)
    args = parser.parse_args()
    token = args.token_file.read_text().strip()
    if len(token) < 32:
        raise ValueError("bridge token must contain at least 32 characters")
    bridge = QueueBridge(
        args.executable,
        args.settings,
        token,
        source_root=args.source_root,
        outputs_root=args.outputs_root,
        private_root=args.private_root,
    )
    ThreadingHTTPServer(("127.0.0.1", 8842), handler_for(bridge)).serve_forever()


if __name__ == "__main__":
    main()
