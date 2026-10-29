"""Read-only validation of retained physical H3 retry lineage."""
import json

from ..provider_budgets import exceeds_budget


def assert_video_retry_evidence(connection, project_id, manifest, execution):
    history = execution.get("retryHistory", {})
    if not isinstance(history, dict) or not set(history).issubset(execution["jobs"]):
        raise ValueError("video retry target history changed")
    if not set(execution.get("cancelledTargets", [])).issubset(execution["jobs"]):
        raise ValueError("cancelled retry target changed")
    owned = set()
    for shot_id, predecessors in history.items():
        current = execution["jobs"][shot_id]
        if (not isinstance(predecessors, list) or not predecessors
                or any(not isinstance(item, str) for item in predecessors)
                or len(predecessors) != len(set(predecessors)) or current in predecessors):
            raise ValueError("video retry predecessor identity changed")
        chain = [*predecessors, current]
        if owned.intersection(chain):
            raise ValueError("video retry identity reused across targets")
        owned.update(chain)
        original, used = None, 0
        commands = set()
        for ordinal, identifier in enumerate(chain):
            row = connection.execute("SELECT project_id,snapshot FROM v2_video_jobs WHERE id=?", (identifier,)).fetchone()
            if row is None or row[0] != project_id:
                raise ValueError("video retry predecessor unavailable")
            snapshot = json.loads(row[1])
            frozen = {key: value for key, value in snapshot.items() if key != "executionRetry"}
            if ordinal == 0:
                original = frozen
                if snapshot.get("executionRetry") or snapshot["shot"]["id"] != shot_id:
                    raise ValueError("video retry root changed")
                limit = snapshot["request"].get("automaticRetryLimit")
                if type(limit) is not int or limit < 0:
                    raise ValueError("video retry has no original prospective allowance")
                continue
            link = snapshot.get("executionRetry", {})
            manual = link.get("manualCommandId")
            if manual and manual in commands:
                raise ValueError("video retry manual command was reused")
            if manual:
                commands.add(manual)
            else:
                used += 1
            if (frozen != original or link.get("ordinal") != ordinal
                    or link.get("rootJobId") != chain[0] or link.get("predecessorJobIds") != chain[:ordinal]
                    or link.get("automaticRetriesUsed") != used or used > limit
                    or link.get("localExecutionStopped") is not True):
                raise ValueError("video retry frozen source, allowance or local stop proof changed")
    if owned:
        placeholders = ",".join("?" for _ in owned)
        rows = connection.execute(f"SELECT j.requested_seconds FROM v2_project_video_dispatches d JOIN v2_video_jobs j ON j.id=d.video_job_id WHERE j.id IN ({placeholders})", tuple(owned)).fetchall()
        # The dispatch owner independently checks the complete batch union;
        # retained retry history must never exceed even that original cap.
        if (exceeds_budget(len(rows), manifest["setup"]["maxJobs"])
                or exceeds_budget(sum(row[0] for row in rows), manifest["setup"]["maxRequestedSeconds"])):
            raise ValueError("video retry history exceeds the original finite allowance")
