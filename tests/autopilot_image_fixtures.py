"""One deterministic bitmap per original native image ID, no ImageGen calls."""
from contextlib import closing
from hashlib import sha256
from io import BytesIO
import json
import re
import subprocess
from PIL import Image
from plotloom.image_commands import image_context
from tests.autopilot_controller_fixtures import environment, run_text


def deliver_image(store, view, checkpoint, *, geometry=None, output_count=1):
    evidence = checkpoint["evidence"]
    context = image_context(store, evidence["owner"], evidence["jobId"])
    request = context["request"]
    job_root = store.image_exchange_for(context)._root() / "jobs" / evidence["jobId"]
    assert (job_root / "package" / "request.json").is_file()
    delivery = job_root / "delivery"
    delivery.mkdir(exist_ok=True)
    (delivery / "outputs").mkdir(exist_ok=True)
    outputs = []
    size = geometry or (view.policy.image_width, view.policy.image_height)
    for index in range(output_count):
        buffer = BytesIO()
        Image.new("RGB", size, (110 + index, 80, 120)).save(buffer, format="PNG")
        content = buffer.getvalue()
        filename = f"fixture-{index}.png"
        (delivery / "outputs" / filename).write_bytes(content)
        outputs.append({"filename": filename, "sha256": sha256(content).hexdigest(), "role": request["kind"]})
    pin = view.policy.execution_pins["image"]
    provenance = {"codeRevision": pin["codeRevision"], "skillVersion": pin["skillVersion"], "skillHash": pin["skillHash"]}
    (delivery / "executor-pin.json").write_text(json.dumps({"jobId": evidence["jobId"], "requestHash": context["requestHash"],
        "executionContract": pin["executionContract"], **provenance}))
    manifest = {"schemaVersion": 2, "jobId": evidence["jobId"], "requestHash": context["requestHash"], "deliveryId": "fixture-image",
        "actualPrompt": "Deterministic bitmap fixture; no generation.", "outputs": outputs,
        "toolEvidence": {"tool": "codex_imagegen", "taskId": view.policy.specialist_bindings["image"], "available": True},
        "executorProvenance": provenance, "limitations": ["Offline fixture, not product acceptance."]}
    identities = [item["originalHash"] for item in request["frozenSnapshot"].get("references", []) if item["role"] == "character_identity"]
    if identities:
        manifest["referenceUse"] = {"viewedReferenceHashes": list(dict.fromkeys(identities)), "identityNotes": "Fixture attestation; no visual identity judgment."}
    (delivery / "completion.json").write_text(json.dumps(manifest))


def image_environment(tmp_path, monkeypatch, *, auto_deliver=True, geometry=None, brief=None, limits=None):
    storage, registry, service, view, text_calls = environment(tmp_path, monkeypatch, brief=brief, limits=limits)
    view = run_text(service, view)
    calls = []
    queue = subprocess.run
    def image_queue(command, **kwargs):
        if len(command) > 1 and command[1] == "queue" and re.search(r"ij_[a-z0-9]{32}", command[-1]):
            job = re.search(r"ij_[a-z0-9]{32}", command[-1]).group()
            calls.append(job)
            if auto_deliver:
                with closing(storage.projects.open(view.project_id)) as store:
                    current = store.repository.autopilot.current(view.project_id)
                    checkpoint = next(item for item in current.checkpoints if item["evidence"]["jobId"] == job)
                    deliver_image(store, current, checkpoint, geometry=geometry(context=image_context(store, checkpoint["evidence"]["owner"], job)) if callable(geometry) else geometry)
            return subprocess.CompletedProcess(command, 0, "queued")
        return queue(command, **kwargs)
    monkeypatch.setattr(subprocess, "run", image_queue)
    return storage, registry, service, view, calls, text_calls


def run_pack(storage, service, view, *, steps=400):
    for _ in range(steps):
        service.step(view.project_id)
        with closing(storage.projects.open(view.project_id)) as store:
            current = store.repository.autopilot.current(view.project_id)
        if current.state == "awaiting_review":
            return current
        assert current.state in {"running", "waiting"}, current.blocker
    raise AssertionError("bounded image pack did not reach review")
