"""Sanitized native P01 read-only failure shape, including its omitted stdout read."""
import json


def write_readonly_turn(job, source, private, rollout, session_id):
    cwd = str(job / "delivery")
    rows = []
    def add(kind, payload):
        rows.append({"ordinal": len(rows), "type": kind, "payload": payload})
    add("session_meta", {"id": str(session_id), "cwd": cwd})
    add("event_msg", {"type": "task_started", "turn_id": "synthetic-turn"})
    add("turn_context", {"turn_id": "synthetic-turn", "cwd": cwd})
    commands = ["ls -la ../package && cat ../package/COPY_ASSIGNMENT.txt", "cat ../package/request.json",
                f"cat {source}/.agents/skills/plotloom-image-specialist/SKILL.md"]
    stdout = [{"type": "thread.started", "thread_id": str(session_id)}, {"type": "turn.started"}]
    for index, command in enumerate(commands):
        call_id = f"synthetic-call-{index}"
        add("response_item", {"type": "custom_tool_call", "name": "exec", "call_id": call_id,
            "input": 'text(await tools.exec_command({cmd:' + json.dumps(command) + ',max_output_tokens:12000}));\n'})
        if index < 2:
            add("event_msg", {"type": "item_completed", "thread_id": str(session_id), "turn_id": "synthetic-turn",
                "item": {"type": "CommandExecution", "command": ["/bin/zsh", "-lc", command],
                         "cwd": (job / "delivery").as_uri(), "status": "completed", "exit_code": 0}})
            for kind, status, code in [("item.started", "in_progress", None), ("item.completed", "completed", 0)]:
                stdout.append({"type": kind, "item": {"id": f"command-{index}", "type": "command_execution",
                    "command": "/bin/zsh -lc " + __import__('shlex').quote(command), "status": status, "exit_code": code}})
        result = {"exit_code": 1 if index == 2 else 0,
                  "output": "Operation not permitted" if index == 2 else "synthetic immutable package"}
        add("response_item", {"type": "custom_tool_call_output", "call_id": call_id,
            "output": [{"type": "input_text", "text": "Script completed"},
                       {"type": "input_text", "text": json.dumps(result)}]})
    add("event_msg", {"type": "task_complete", "turn_id": "synthetic-turn"})
    stdout.append({"type": "turn.completed"})
    private.mkdir(parents=True, exist_ok=True)
    rollout.parent.mkdir(parents=True, exist_ok=True)
    save_rows(private / "stdout.jsonl", stdout)
    save_rows(rollout, rows)
    (private / "stderr.log").write_bytes(b"")
    return rows, stdout


def save_rows(path, rows):
    path.write_text("".join(json.dumps(row) + "\n" for row in rows))
