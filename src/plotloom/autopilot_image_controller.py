"""Serial native initial images and separately authorized local geometry."""
from sqlalchemy import select
from .autopilot_contracts import CheckpointEvidence, CommandAuthority, OperationScope
from .autopilot_launch import assert_frozen_execution, assert_frozen_pins, require_job_capacity
from .autopilot_materials import MaterialInventory, initial_inventory, inventory_hash
from .autopilot_image_selection import select_image, publish_bundle
from .exceptions import InvalidTransitionError
from .image_commands import IMAGE_METHODS, image_context, image_package, read_image, send_image, ingest_image
from .image_job_contracts import NativeTaskBinding
from .brief_contracts import ProjectBrief
from .autopilot_brief_style import image_style_guidance
from .persistence.schema import AutopilotCheckpointRow, AutopilotDecisionRow


class AutopilotImageController:
    def __init__(self, registry):
        self.registry = registry

    @staticmethod
    def checkpoint(view, key):
        return next((item for item in view.checkpoints if item["operationKey"] == key), None)

    @staticmethod
    def command(store, view, claim, scope):
        return store.repository.autopilot_command(CommandAuthority(view.id, claim, scope))

    @staticmethod
    def native_task_binding(view):
        return NativeTaskBinding(mode="configured_task", task_id=view.policy.specialist_bindings["image"])

    def advance(self, store, view, claim):
        self.settle_delivered(view)
        if view.state not in {"running", "waiting"}:
            self.reconcile_inactive(store, view, claim)
            return
        assert_frozen_execution(store, self.registry, view.policy)
        inventory = initial_inventory(store, view.policy)
        prior = self.checkpoint(view, "material.inventory")
        if prior is None:
            with self.command(store, view, claim, OperationScope.SELECT):
                record = store.repository.autopilot.checkpoint("material.inventory", state="adopted",
                    evidence=CheckpointEvidence(owner="bundle", subject_id=inventory.entity_revision_id,
                        result={"contentHash": inventory.storyboard_hash, "inventory": inventory.model_dump(mode="json", by_alias=True)}))
                store.repository.autopilot.decide(record, subject={"inventoryHash": inventory_hash(inventory)},
                    rationale="完整采用人物、美术与所有完整路线的唯一拍摄镜头；资源上限在图片发送前核对。")
            return
        frozen = MaterialInventory.model_validate(prior["evidence"]["result"]["inventory"])
        if inventory != frozen:
            raise InvalidTransitionError("frozen complete image inventory changed")
        for subject in inventory.subjects:
            checkpoint = self.checkpoint(view, subject.operation_key)
            if checkpoint is None:
                self.prepare(store, view, claim, subject, inventory, subject.operation_key)
                return
            if checkpoint["state"] != "adopted":
                self.native_step(store, view, claim, subject, inventory, checkpoint)
                return
            if subject.owner == "image" and not checkpoint["evidence"]["result"].get("geometryCompatible") and not any(frame.shot_id == subject.id for frame in view.frames):
                from .autopilot_geometry_preparation import prepare_first_frame_geometry
                prepare_first_frame_geometry(store, view, claim, subject, inventory, checkpoint)
                # One bounded material operation per controller advance. A later
                # step revalidates authority before preparing another native job.
                return

        with self.command(store, view, claim, OperationScope.SELECT):
            publish_bundle(store, view, inventory)

    def prepare(self, store, view, claim, subject, inventory, key):
        require_job_capacity(view)
        image_count = sum(item["evidence"]["owner"] in IMAGE_METHODS for item in view.checkpoints)
        if image_count >= view.policy.max_images:
            raise InvalidTransitionError("达到冻结图片上限；不能新增适配，请接管已保留的素材。")
        with self.command(store, view, claim, OperationScope.IMAGE):
            frozen_brief = ProjectBrief.model_validate(view.policy.brief)
            direction = frozen_brief.visual_direction
            style_guidance = image_style_guidance(direction, follows_brief=view.policy.effective_style_authority == "brief")
            if subject.owner == "character-reference":
                context = store.media.prepare_character_reference_proposal(view.project_id, character_id=subject.id,
                    cast_revision=inventory.cast_revision, visual_direction="按冻结人物形象生成一张清晰身份参考图；" + style_guidance,
                    parent_candidate_asset_id=None)["proposal"]
            elif subject.owner == "art-reference":
                context = store.media.prepare_art_reference_proposal(view.project_id, subject_type=subject.subject_type,
                    subject_id=subject.id, render_direction="按冻结美术方案生成一张独立参考图；" + style_guidance)["proposal"]
            else:
                with store.repository._read() as session:
                    install = session.scalar(select(AutopilotCheckpointRow).where(AutopilotCheckpointRow.run_id == view.id,
                        AutopilotCheckpointRow.operation_key == "installation"))
                    decision = store.repository.autopilot.decide(install, subject={"entityRevisionId": inventory.entity_revision_id,
                        "revision": inventory.storyboard_revision, "contentHash": inventory.storyboard_hash, "productionHash": inventory.production_hash},
                        rationale="通过当前规范门槛的安装仅授权首帧生成；不等同于人类分镜批准。")
                context = store.media.prepare_image_job(view.project_id, machine_decision_id=decision, shot_id=subject.id,
                    storyboard_revision=inventory.storyboard_revision,
                    presentation_change="按冻结镜头动作与构图生成一张首帧；" + style_guidance, contract_version=3)["job"]
            evidence = CheckpointEvidence(owner=subject.owner, subject_id=subject.id, job_id=context["id"],
                request_hash=context["requestHash"], execution_pin=context["request"]["specialistPreflight"],
                result={})
            if evidence.execution_pin != view.policy.execution_pins["image"]:
                raise InvalidTransitionError("prepared image execution differs from launch")
            store.repository.autopilot.checkpoint(key, state="prepared", evidence=evidence)
            store.repository.autopilot.progress("first-frames" if subject.owner == "image" else "references")
        native_task_binding = self.native_task_binding(view)
        self.registry.bind_delivery(context["id"], native_task_binding)
        image_package(store, subject.owner, context["id"], native_task_binding=native_task_binding)

    def native_step(self, store, view, claim, subject, inventory, checkpoint):
        if checkpoint["state"] == "delivered":
            with self.command(store, view, claim, OperationScope.SELECT):
                select_image(store, view, subject, checkpoint, inventory)
            return
        evidence = CheckpointEvidence.model_validate(checkpoint["evidence"])
        transport = self.registry.status(evidence.job_id)
        context = image_context(store, subject.owner, evidence.job_id)
        if checkpoint["state"] == "prepared" and transport["state"] == "prepared":
            native_task_binding = self.native_task_binding(view)
            self.registry.bind_delivery(evidence.job_id, native_task_binding)
            image_package(store, subject.owner, evidence.job_id, native_task_binding=native_task_binding)
        delivery = read_image(store, subject.owner, evidence.job_id, context,
            native_task_binding=self.native_task_binding(view))
        if delivery is not None:
            self.retain_delivery(store, view, claim, checkpoint, evidence, context, delivery)
            return
        if checkpoint["state"] == "prepared" and transport["state"] == "prepared":
            def before_send():
                with self.command(store, view, claim, OperationScope.IMAGE):
                    assert_frozen_pins(store, view.policy)
                    name = IMAGE_METHODS[subject.owner][0]
                    getattr(store.media, f"mark_{name}_exported")(view.project_id, evidence.job_id, require_prepared=True)
                    store.repository.autopilot.checkpoint(checkpoint["operationKey"], state="sent", expected_revision=checkpoint["revision"],
                        evidence=evidence.model_copy(update={"result": evidence.result | {"dispatchAttempted": True}}))
            send_image(store, self.registry, subject.owner, evidence.job_id, policy=view.policy, before_send=before_send)
            return
        target = "outcome_unknown" if transport["state"] in {"prepared", "outcome_unknown"} or checkpoint["state"] == "outcome_unknown" else "sent"
        if checkpoint["state"] != target:
            with self.command(store, view, claim, OperationScope.EVIDENCE):
                facts = evidence.result | {"dispatchAttempted": True}
                if target == "outcome_unknown":
                    facts["dispatchOutcomeUnknown"] = True
                store.repository.autopilot.checkpoint(checkpoint["operationKey"], state=target, expected_revision=checkpoint["revision"],
                    evidence=evidence.model_copy(update={"result": facts}))

    def retain_delivery(self, store, view, claim, checkpoint, evidence, context, delivery):
        provenance = delivery.manifest.executor_provenance
        expected = view.policy.execution_pins["image"]
        native_task_identity = delivery.manifest.native_task_identity
        if (provenance.code_revision != expected["codeRevision"] or provenance.skill_hash != expected["skillHash"]
                or native_task_identity != view.policy.specialist_bindings["image"]):
            raise InvalidTransitionError("image receipt execution differs from frozen policy")
        target = IMAGE_METHODS[evidence.owner][2]
        self.registry.assert_image_terminal_identity(evidence.job_id, view.policy.specialist_bindings["image"], project_id=view.project_id, target=target)
        with self.command(store, view, claim, OperationScope.EVIDENCE):
            if view.state in {"cancelled", "taken_over", "stale"}:
                name = IMAGE_METHODS[evidence.owner][0]
                getattr(store.media, f"cancel_{name}")(view.project_id, evidence.job_id, "原自动运行已停止；仅保留晚到证据。")
            result = ingest_image(store, evidence.owner, evidence.job_id, delivery)
            facts = evidence.result | {"deliveryState": result["state"], "candidateAssetIds": [item["assetId"] for item in result["candidates"]],
                "outputRoles": [item.role for item in delivery.outputs]}
            store.repository.autopilot.checkpoint(checkpoint["operationKey"], state="delivered", expected_revision=checkpoint["revision"],
                evidence=evidence.model_copy(update={"delivery_hash": delivery.manifest_hash, "result": facts}))
        self.registry.complete(evidence.job_id)

    def settle_delivered(self, view):
        for checkpoint in view.checkpoints:
            evidence = checkpoint["evidence"]
            if evidence["owner"] in IMAGE_METHODS and checkpoint["state"] in {"delivered", "adopted"} and self.registry.status(evidence["jobId"])["state"] != "completed":
                self.registry.assert_image_terminal_identity(evidence["jobId"], view.policy.specialist_bindings["image"], project_id=view.project_id, target=IMAGE_METHODS[evidence["owner"]][2])
                self.registry.complete(evidence["jobId"])

    def reconcile_inactive(self, store, view, claim):
        for checkpoint in view.checkpoints:
            evidence = CheckpointEvidence.model_validate(checkpoint["evidence"])
            if evidence.owner not in IMAGE_METHODS or checkpoint["state"] in {"delivered", "adopted"} or self.registry.status(evidence.job_id)["state"] == "prepared":
                continue
            context = image_context(store, evidence.owner, evidence.job_id)
            delivery = read_image(store, evidence.owner, evidence.job_id, context,
                native_task_binding=self.native_task_binding(view))
            if delivery is not None:
                self.retain_delivery(store, view, claim, checkpoint, evidence, context, delivery)

    @staticmethod
    def cancel_pending(store, view):
        for checkpoint in view.checkpoints:
            evidence = checkpoint["evidence"]
            if evidence["owner"] in IMAGE_METHODS and checkpoint["state"] not in {"delivered", "adopted"} and image_context(store, evidence["owner"], evidence["jobId"])["state"] != "delivered":
                getattr(store.media, f"cancel_{IMAGE_METHODS[evidence['owner']][0]}")(view.project_id, evidence["jobId"], "自动运行已取消或接管。")
