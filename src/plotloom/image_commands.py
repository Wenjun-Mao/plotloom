"""Repository-bound image transport/admission shared by the native controller."""
from hashlib import sha256
from pathlib import Path
from .image_job_contracts import ImageJobError, NativeTaskBinding
from .codex_exec_contracts import CodexExecAttempt, CodexExecProfile, CodexExecReceipt
from .image_job_exchange import PackageReference
from .managed_media import publish_import

IMAGE_METHODS = {
    "image": ("image_job", "job", "image_job"),
    "character-reference": ("character_reference_proposal", "proposal", "character_reference_proposal"),
    "art-reference": ("art_reference_proposal", "proposal", "art_reference_proposal"),
}


def image_context(store, owner, job_id):
    name = IMAGE_METHODS[owner][0]
    return getattr(store.media, f"{name}_delivery_context")(store.manifest.project_id, job_id)


def frozen_references(context):
    values = []
    for index, reference in enumerate(context["request"]["frozenSnapshot"].get("references", [])):
        role = reference["role"]
        if role == "character_identity":
            role += ":" + reference["characterId"]
        suffix = ".png" if reference["mimeType"] == "image/png" else ".jpg"
        values.append((role, f"reference-{index + 1}-{reference['originalHash'][:16]}{suffix}", reference["originalHash"]))
    return values


def image_package(store, owner, job_id, *, native_task_binding: NativeTaskBinding | None = None):
    name, key, _target = IMAGE_METHODS[owner]
    sources = getattr(store.media, f"{name}_package_sources")(store.manifest.project_id, job_id)
    context = sources[key]
    references = []
    for index, source in enumerate(sources["references"]):
        content = store.artifacts.get(source["originalUri"])
        if sha256(content).hexdigest() != source["contentHash"]:
            raise ImageJobError("reference_integrity", "frozen reference bytes changed")
        role = source["role"]
        if role == "character_identity":
            role += ":" + source["characterId"]
        suffix = ".png" if source["mimeType"] == "image/png" else ".jpg"
        references.append(PackageReference(role=role, filename=f"reference-{index + 1}-{source['contentHash'][:16]}{suffix}",
            content_hash=source["contentHash"], content=content))
    if context["request"].get("executionContract") == "codex_exec.v1" and native_task_binding is not None:
        raise ImageJobError("image_native_task_binding_invalid", "Codex Exec image packages cannot bind a native chat task")
    if context["request"].get("executionContract") != "codex_exec.v1" and native_task_binding is None:
        raise ImageJobError("image_native_task_binding_missing", "specialist image packages require their native task binding")
    return store.image_exchange_for(context).write_package(job_id=job_id, request=context["request"],
        request_hash=context["requestHash"], references=references, native_task_binding=native_task_binding)


def send_image(store, registry, owner, job_id, *, policy, before_send):
    native_task_binding = NativeTaskBinding(mode="configured_task", task_id=policy.specialist_bindings["image"])
    registry.bind_delivery(job_id, native_task_binding)
    paths = image_package(store, owner, job_id, native_task_binding=native_task_binding)
    delivery_path = Path(paths["deliveryPath"])
    if delivery_path.exists() or delivery_path.is_symlink():
        raise ImageJobError("delivery_conflict", "existing delivery or execution staging must be inspected, never resent")
    root = Path(__file__).resolve().parents[2]
    registry.dispatch("image", job_id=job_id, context={"projectId": store.manifest.project_id, "stage": owner},
        package_path=paths["packagePath"], delivery_path=paths["deliveryPath"], before_send=before_send,
        expected_task_id=policy.specialist_bindings["image"], expected_bindings=policy.specialist_bindings,
        assignment=(f"Execute exactly one frozen Plotloom image job {job_id} with one output. "
            f"Use checkout {root} at frozen revision {policy.code_revision}; read {root}/.agents/skills/plotloom-image-specialist/SKILL.md "
            f"and {paths['packagePath']}/request.json and COPY_ASSIGNMENT.txt. The package alone owns this assignment. "
            f"Write only its delivery under {paths['deliveryPath']}. Run its execution pin before ImageGen. "
            "Do not edit code, package, canon, references, selections or approvals. No video or other providers."))


def read_image(
    store,
    owner,
    job_id,
    context,
    *,
    native_task_binding: NativeTaskBinding | None = None,
    executor_attempt: CodexExecAttempt | None = None,
    executor_profile: CodexExecProfile | None = None,
    executor_receipt: CodexExecReceipt | None = None,
):
    exchange = store.image_exchange_for(context)
    request = context["request"]
    is_codex_exec = request.get("executionContract") == "codex_exec.v1"
    if is_codex_exec and native_task_binding is not None:
        raise ImageJobError("image_native_task_binding_invalid", "Codex Exec delivery cannot use a native chat binding")
    if not is_codex_exec and native_task_binding is None:
        raise ImageJobError("image_native_task_binding_missing", "specialist delivery requires its native task binding")
    exchange.verify_package(job_id=job_id, request=request, request_hash=context["requestHash"],
        references=frozen_references(context), native_task_binding=native_task_binding)
    preflight = request.get("specialistPreflight", {})
    if is_codex_exec:
        if executor_attempt is None or executor_profile is None or executor_receipt is None:
            raise ImageJobError("delivery_executor_evidence_missing", "Codex Exec delivery requires its exact project attempt and receipt")
        all_reference_hashes = tuple(
            item["originalHash"] for item in request.get("frozenSnapshot", {}).get("references", [])
        )
        output_role = (
            "art_reference" if request.get("target") == "art_reference_proposal"
            else "keyframe_adaptation" if request.get("kind") == "keyframe_adaptation"
            else "refinement" if request.get("kind") == "refinement"
            else "original"
        )
        return exchange.read_delivery(
            job_id=job_id,
            request_hash=context["requestHash"],
            require_executor_provenance=True,
            expected_executor_contract="codex_exec.v1",
            required_reference_hashes=[item["originalHash"] for item in request.get("frozenSnapshot", {}).get("references", [])
                if item["role"] == "character_identity"],
            expected_codex_attempt=executor_attempt,
            expected_codex_profile=executor_profile,
            expected_codex_receipt=executor_receipt,
            expected_codex_reference_hashes=all_reference_hashes,
            expected_codex_execution_pin=preflight,
            expected_codex_output_role=output_role,
        )
    return exchange.read_delivery(job_id=job_id, request_hash=context["requestHash"], require_executor_provenance=True,
        required_reference_hashes=[item["originalHash"] for item in request["frozenSnapshot"].get("references", []) if item["role"] == "character_identity"],
        require_executor_pin=True, expected_executor_skill_version=preflight["skillVersion"],
        expected_executor_contract=preflight["executionContract"],
        expected_native_task_binding=native_task_binding)


def ingest_image(store, owner, job_id, delivery):
    name = IMAGE_METHODS[owner][0]
    outputs = [{"filename": item.filename, "role": item.role, "originalHash": item.observed.content_hash,
        "displayHash": item.observed.display_hash, "mimeType": item.observed.mime_type, "byteSize": item.observed.byte_size,
        "width": item.observed.width, "height": item.observed.height, "content": item.content, "observed": item.observed}
        for item in delivery.outputs]
    return getattr(store.media, f"record_{name}_delivery")(store.manifest.project_id, job_id,
        delivery_id=delivery.manifest.delivery_id, manifest=delivery.manifest.canonical_payload(),
        manifest_hash=delivery.manifest_hash, outputs=outputs,
        publish=lambda output: publish_import(store.artifacts, output["content"], output["observed"]))
