"""Advisory Spark headroom checks, not a cross-service GPU scheduler."""

import json
from pathlib import Path
from urllib.request import urlopen


def available_gib() -> float | None:
    info = Path("/proc/meminfo")
    if not info.is_file():
        return None
    for line in info.read_text().splitlines():
        if line.startswith("MemAvailable:"):
            return int(line.split()[1]) / 1024**2
    raise ValueError("resource.memory_unavailable")


def admission(runtime: dict) -> str | None:
    available = available_gib()
    if available is None or available < runtime["minAvailableGiB"]:
        return "resource.memory_headroom"
    queue_url = runtime.get("comfyQueueUrl")
    if queue_url:
        try:
            with urlopen(queue_url, timeout=2) as response:
                queue = json.load(response)
            if queue.get("queue_running") or queue.get("queue_pending"):
                return "resource.other_generation_active"
        except (OSError, ValueError):
            return "resource.activity_unavailable"
    return None
