"""Source-owned exact uv parent and PPID-linked QA Python child observations."""
import hashlib
import os
import re
import subprocess

from handoff_files import require


def parse_rows(output):
    rows = []
    for line in output.strip().splitlines():
        match = re.fullmatch(r"\s*(\d+)\s+(\d+)\s+(\d+)\s+(\w+\s+\w+\s+\d+\s+\d+:\d+:\d+\s+\d+)\s+(.+)", line)
        require(match is not None, "incomplete original process row")
        rows.append({"pid": int(match[1]), "ppid": int(match[2]), "pgid": int(match[3]),
            "birthStart": " ".join(match[4].split()),
            "commandSha256": hashlib.sha256(match[5].encode()).hexdigest()})
    return rows


def observe(pids):
    require(all(type(pid) is int and pid > 0 for pid in pids), "exact positive PIDs required")
    output = subprocess.check_output(["ps", "-p", ",".join(map(str, pids)),
        "-o", "pid=,ppid=,pgid=,lstart=,command="], text=True, timeout=2)
    rows = parse_rows(output)
    require(len(rows) == len(pids) and {row["pid"] for row in rows} == set(pids), "missing process")
    return {row["pid"]: row for row in rows}


def current():
    return observe([os.getpid()])[os.getpid()]


def validate_tree(launch, tree):
    require(set(tree) == {"launcher", "driver", "launchSha256"}, "unexpected process tree fields")
    a, b = tree["launcher"], tree["driver"]
    for row in (a, b):
        require(set(row) == {"pid", "ppid", "pgid", "birthStart", "commandSha256"}
            and type(row["birthStart"]) is str and bool(row["birthStart"])
            and type(row["commandSha256"]) is str
            and re.fullmatch(r"[0-9a-f]{64}", row["commandSha256"]) is not None, "invalid process identity fields")
    require(all(type(v) is int and v > 0 for v in
        (a["pid"], a["ppid"], a["pgid"], b["pid"], b["ppid"], b["pgid"])), "invalid process identities")
    require(a["pid"] == launch["pid"] and a["pgid"] == a["pid"] == launch["pgid"]
        and a["birthStart"] == launch["birthStart"] and b["pid"] != a["pid"]
        and b["ppid"] == a["pid"] and b["pgid"] == a["pgid"], "wrong original parent/child topology")


def child_tree(launch, launch_sha, pin):
    rows = observe([launch["pid"], os.getpid()])
    tree = {"launcher": rows[launch["pid"]], "driver": rows[os.getpid()], "launchSha256": launch_sha}
    validate_tree(launch, tree)
    parent_command = " ".join(launch["execArgv"])
    require(tree["launcher"]["commandSha256"] == hashlib.sha256(parent_command.encode()).hexdigest(),
        "original parent is not exact declared uv command")
    child_commands = [" ".join([exe, *launch["execArgv"][5:]]) for exe in pin["allowedInnerExecutables"]]
    require(tree["driver"]["commandSha256"] in
        {hashlib.sha256(command.encode()).hexdigest() for command in child_commands}, "wrong QA Python child command")
    return tree
