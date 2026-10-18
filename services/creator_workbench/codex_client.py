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
    parser.add_argument(
        "command",
        choices=["queue", "bridge-health", "exec-profile", "exec-readiness", "exec-admit", "exec-status", "exec-cancel", "exec-suspend", "exec-resume", "exec-abandonment-preview", "exec-project-revoke"],
    )
    parser.add_argument("--thread")
    parser.add_argument("--message")
    parser.add_argument("--attempt-json")
    parser.add_argument("--attempt-id")
    parser.add_argument("--packet-json")
    args = parser.parse_args(argv)
    if args.command == "queue" and (not args.thread or not args.message):
        parser.error("queue requires --thread and --message")
    if args.command != "queue" and (args.thread or args.message):
        parser.error("thread and message are only valid for queue")
    if args.command in {"exec-admit", "exec-cancel", "exec-suspend", "exec-resume"} and (not args.attempt_json or args.attempt_id):
        parser.error(f"{args.command} requires --attempt-json")
    if args.command == "exec-status" and (not args.attempt_id or args.attempt_json):
        parser.error("exec-status requires --attempt-id")
    if args.command not in {"exec-admit", "exec-status", "exec-cancel", "exec-suspend", "exec-resume"} and (args.attempt_json or args.attempt_id):
        parser.error("attempt arguments are only valid for Codex Exec commands")
    token = Path(os.environ["PLOTLOOM_CODEX_BRIDGE_TOKEN_FILE"]).read_text().strip()
    url = os.environ["PLOTLOOM_CODEX_BRIDGE_URL"].rstrip("/")
    payload = None
    if args.command in {"exec-abandonment-preview", "exec-project-revoke"}:
        try:
            from plotloom.project_abandonment_contracts import AbandonmentPacket
            payload = AbandonmentPacket.model_validate_json(args.packet_json).model_dump(mode="json", by_alias=True)
        except (TypeError, ValueError):
            parser.error("--packet-json must bind one exact project abandonment")
    elif args.packet_json:
        parser.error("packet arguments are only valid for project abandonment")
    elif args.command == "queue":
        payload = {"thread": args.thread, "message": args.message}
    elif args.command == "exec-admit":
        try:
            payload = {"attempt": json.loads(args.attempt_json)}
        except json.JSONDecodeError:
            parser.error("--attempt-json must be valid JSON")
    elif args.command in {"exec-cancel", "exec-suspend", "exec-resume"}:
        try:
            from plotloom.codex_exec_contracts import CodexExecAttempt
            attempt = CodexExecAttempt.model_validate_json(args.attempt_json)
            payload = {"attempt": attempt.model_dump(mode="json", by_alias=True)}
        except (ImportError, TypeError, ValueError):
            parser.error("--attempt-json must be a valid Codex Exec attempt")
    if args.command in {"exec-cancel", "exec-suspend", "exec-resume"}:
        endpoint = f"/{args.command}/{payload['attempt']['attemptId']}"
    else:
        endpoint = {
            "queue": "/queue",
            "bridge-health": "/healthz",
            "exec-profile": "/exec-profile",
            "exec-readiness": "/exec-readiness",
            "exec-admit": "/exec-admit",
            "exec-status": f"/exec-status/{args.attempt_id}" if args.attempt_id else "",
            "exec-abandonment-preview": "/exec-abandonment-preview",
            "exec-project-revoke": "/exec-project-revoke",
        }[args.command]
    request = Request(
        url + endpoint,
        data=json.dumps(payload).encode() if payload is not None else None,
        method="POST" if payload is not None else "GET",
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
    if args.command in {"exec-abandonment-preview", "exec-project-revoke"}:
        try:
            from plotloom.project_abandonment_contracts import AbandonmentPreview
            context = AbandonmentPreview.model_validate(result)
        except (TypeError, ValueError):
            print("Project abandonment acknowledgement is invalid.", file=sys.stderr)
            return 1
        print(context.model_dump_json(by_alias=True))
        return 0
    if args.command == "exec-profile":
        try:
            from plotloom.codex_exec_contracts import CodexExecProfile
            profile = CodexExecProfile.model_validate(result)
        except (ImportError, TypeError, ValueError):
            print("Codex Exec profile acknowledgement is invalid.", file=sys.stderr)
            return 1
        print(profile.model_dump_json(by_alias=True))
        return 0
    if args.command == "exec-readiness":
        try:
            from plotloom.codex_exec_contracts import CodexExecReadiness
            readiness = CodexExecReadiness.model_validate(result)
        except (ImportError, TypeError, ValueError):
            print("Codex Exec readiness acknowledgement is invalid.", file=sys.stderr)
            return 1
        print(readiness.model_dump_json(by_alias=True))
        return 0
    if args.command in {"exec-admit", "exec-status", "exec-cancel", "exec-suspend", "exec-resume"}:
        try:
            from plotloom.codex_exec_contracts import CodexExecHostStatus
            status = CodexExecHostStatus.model_validate(result)
        except (ImportError, TypeError, ValueError):
            print("Codex Exec status acknowledgement is invalid.", file=sys.stderr)
            return 1
        print(status.model_dump_json(by_alias=True))
        return 0
    if not isinstance(result, dict) or type(result.get("returncode")) is not int:
        print("Native Codex bridge acknowledgement is invalid.", file=sys.stderr)
        return 1
    if result["returncode"] == 0:
        if result.get("wakeState") not in ("open_requested", "open_unconfirmed"):
            print(
                "Native Codex bridge wake acknowledgement is invalid.", file=sys.stderr
            )
            return 1
        print(
            json.dumps(
                {
                    "protocol": "plotloom.native-queue.v1",
                    "wakeState": result["wakeState"],
                }
            )
        )
    return result["returncode"]


if __name__ == "__main__":
    raise SystemExit(main())
