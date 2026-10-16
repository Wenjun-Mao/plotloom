"""Record complete real workloads and receipt timings; never normalize away content."""
from collections import Counter
from contextlib import closing
import hashlib
import json

from plotloom.codex_exec_contracts import assert_receipt_matches_attempt
from plotloom.domain import StageName
from plotloom.source_structures import complete_routes


def record_workload(runtime, project_id, snapshot, inventory, work):
    run = snapshot["run"]
    records = []
    with closing(runtime.app.state.project_folder_storage.projects.open(project_id)) as store:
        with store.repository._read() as session:
            graph = store.repository._canonical._load_stage_payload(session, project_id, StageName.STORY_GRAPH)
            routes = complete_routes(graph)
            topology = {
                "nodes": [{"id": node.id, "kind": node.kind.value, "footageMode": str(node.footage_mode)} for node in graph.nodes],
                "edges": [{"source": edge.source_node_id, "target": edge.target_node_id, "kind": edge.kind.value} for edge in graph.edges],
            }
        if (len(graph.nodes) != 4 or len(graph.join_contracts) != 0
                or any(node.footage_mode != ("route_only" if node.kind.value == "decision" else "footage") for node in graph.nodes)
                or sum(node.kind.value == "decision" for node in graph.nodes) != 1
                or sum(node.kind.value == "ending" for node in graph.nodes) != 2
                or any(sum(next(node for node in graph.nodes if node.id == identity).kind.value == "decision" for identity in route) != 1 for route in routes)):
            raise RuntimeError("actual topology differs from four nodes, one decision, two endings and no joins")
        for checkpoint in run["checkpoints"]:
            attempt, receipt = store.repository.autopilot.exec_attempt_evidence_for_operation(run["id"], checkpoint["operationKey"])
            if attempt is None:
                continue
            if receipt is None or attempt.terminal_result != "success":
                raise RuntimeError("complete workload has an unsettled or unsuccessful native attempt")
            assert_receipt_matches_attempt(attempt, receipt)
            records.append({"operationKey": attempt.operation_key, "domain": attempt.domain,
                "attemptId": str(attempt.attempt_id), "jobId": attempt.job_id, "sessionId": str(receipt.session_id),
                "requestHash": attempt.request_hash, "packageHash": attempt.package_hash,
                "outputHash": receipt.output_hash,
                "outputs": [item.model_dump(mode="json", by_alias=True) for item in receipt.outputs],
                "referenceAttachmentCount": len(receipt.reference_views),
                "imageEvidence": [item.model_dump(mode="json", by_alias=True) for item in receipt.image_evidence],
                "validationSteps": [item.model_dump(mode="json", by_alias=True) for item in receipt.text_validation.steps] if receipt.text_validation else [],
            })
    if len(routes) != inventory["routeCount"] or len(routes) != 2:
        raise RuntimeError("actual complete routes differ from the frozen two-ending topology")
    result = {
        "projectId": project_id, "runId": run["id"], "inventory": inventory,
        "topology": topology, "completeRoutes": routes,
        "filmedNodeIds": [node.id for node in graph.nodes if node.footage_mode == "footage"],
        "routeOnlyNodeIds": [node.id for node in graph.nodes if node.footage_mode == "route_only"],
        "routeCount": len(routes), "requiredImages": len(inventory["subjects"]),
        "requiredByOwner": dict(Counter(item["owner"] for item in inventory["subjects"])),
        "artBySubjectType": dict(Counter(item.get("subjectType") for item in inventory["subjects"] if item["owner"] == "art-reference")),
        "uniqueFilmedShotIds": [item["id"] for item in inventory["subjects"] if item["owner"] == "image"],
        "adoptedFrames": len(run["frames"]),
        "geometryOperations": [item["operationKey"] for item in run["checkpoints"] if item["evidence"]["owner"] == "geometry-preparation"],
        "geometryLineage": [{"shotId": frame["shotId"], "assetId": frame["assetId"], "preparation": frame.get("geometryPreparation")} for frame in run["frames"]],
        "nativeTextCalls": sum(item["domain"] == "text" for item in records),
        "nativeImageCalls": sum(item["domain"] == "image" for item in records),
        "referenceAttachmentCounts": [item["referenceAttachmentCount"] for item in records if item["domain"] == "image"],
        "imageBudgetFacts": [{key: item[key] for key in ("attemptId", "imageBudgetState", "reservedImageOutputs")} for item in snapshot["attempts"] if item["domain"] == "image"],
        "rawReceiptFacts": records, "bundleHash": run["bundleHash"], "humanHandoff": run["handoff"],
        "briefSha256": hashlib.sha256(json.dumps(run["policy"]["brief"], ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
        "summaryCounts": {"nodes": len(graph.nodes), "filmedNodes": sum(node.footage_mode == "footage" for node in graph.nodes),
            "routes": len(routes), "castReferences": sum(item["owner"] == "character-reference" for item in inventory["subjects"]),
            "artScenes": sum(item.get("subjectType") == "scene" for item in inventory["subjects"]),
            "artProps": sum(item.get("subjectType") == "prop" for item in inventory["subjects"]),
            "uniqueFilmedShots": sum(item["owner"] == "image" for item in inventory["subjects"]),
            "requiredImages": len(inventory["subjects"]), "geometryOperations": sum(item["evidence"]["owner"] == "geometry-preparation" for item in run["checkpoints"])},
        "contentEquivalenceAssumed": False, "capacityOnlySpeedupEstablished": False,
    }
    (work / "workload.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
