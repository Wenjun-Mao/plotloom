"""Installation-local specialist bindings and serialized dispatch ownership."""
from __future__ import annotations

import fcntl
import json
import subprocess
from contextlib import contextmanager
from pathlib import Path
from typing import Literal
from uuid import UUID

from pydantic import Field, field_validator, model_validator

from .codex_exec_contracts import (
    CodexExecAttempt,
    CodexExecHostStatus,
    CodexExecProfile,
    CodexExecReadiness,
)
from .codex_image_dispatch import NativeCodexImageDispatcher
from .domain import CamelModel
from .image_job_contracts import ImageJobError, NativeTaskBinding

Role = Literal["text", "image"]


class SpecialistBinding(CamelModel):
    name: str = Field(min_length=1, max_length=80)
    task_id: str | None = None

    @field_validator("task_id")
    @classmethod
    def chat_uuid(cls, value: str | None) -> str | None:
        return str(UUID(value.strip())) if value and value.strip() else None


class SpecialistSettings(CamelModel):
    text: SpecialistBinding = Field(default_factory=lambda: SpecialistBinding(name="文字创作助手"))
    image: SpecialistBinding = Field(default_factory=lambda: SpecialistBinding(name="图像生成助手"))

    @model_validator(mode="after")
    def distinct_chats(self):
        if self.text.task_id and self.text.task_id == self.image.task_id:
            raise ValueError("文字与图像助手必须使用不同的聊天 ID。")
        return self


class SpecialistRegistry:
    def __init__(
        self, root: Path, image: NativeCodexImageDispatcher | None = None, *,
        executable: str | None = None, environment: dict[str, str] | None = None,
    ):
        self.root = root / "specialists"
        self.root.mkdir(parents=True, exist_ok=True)
        self.path = self.root / "settings.json"
        self.bootstrap = image
        self.executable = executable
        self.environment = environment
        with self.lock():
            if not self.path.exists():
                settings = SpecialistSettings()
                roots = {}
                if image:
                    # Existing transport leases are authoritative, including unknown outcomes.
                    settings.image = SpecialistBinding(name="图像生成助手", task_id=image.task_id)
                    roots[image.task_id] = str(image.state_root.resolve())
                self._write({"settings": settings.model_dump(by_alias=True), "roots": roots})

    @contextmanager
    def lock(self):
        with (self.root / "settings.lock").open("a+") as lock:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(lock.fileno(), fcntl.LOCK_UN)

    def _read(self):
        return json.loads(self.path.read_text(encoding="utf-8"))

    def _write(self, value):
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
        temporary.replace(self.path)

    def view(self):
        with self.lock():
            data = self._read()
            active = []
            for root in data["roots"].values():
                path = Path(root) / "inflight.json"
                if path.exists():
                    lease = json.loads(path.read_text())
                    active.append(lease | data.get("jobs", {}).get(lease["jobId"], {}))
            return data["settings"] | {"busy": bool(active), "activeTasks": active}

    def codex_exec_profile(self) -> CodexExecProfile:
        """Read the source and CLI profile from the authenticated Mac host."""
        if not self.executable:
            raise ImageJobError(
                "codex_exec_unavailable",
                "Codex Exec is unavailable because the authenticated Mac host is not configured.",
            )
        try:
            result = subprocess.run(
                [self.executable, "exec-profile"],
                capture_output=True,
                timeout=20,
                check=False,
                env=self.environment,
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            raise ImageJobError(
                "codex_exec_profile_unavailable",
                "The Mac host could not report its qualified Codex Exec profile.",
            ) from error
        if result.returncode != 0 or result.stderr:
            raise ImageJobError(
                "codex_exec_profile_unavailable",
                "The Mac host could not report its qualified Codex Exec profile.",
            )
        try:
            profile = CodexExecProfile.model_validate_json(result.stdout)
        except (TypeError, ValueError) as error:
            raise ImageJobError(
                "codex_exec_profile_invalid",
                "The Mac host returned an unsupported Codex Exec profile.",
            ) from error
        return profile

    def codex_exec_readiness(self) -> CodexExecReadiness:
        """Read the host's dynamic login readiness without freezing it into policy."""
        if not self.executable:
            raise ImageJobError(
                "codex_exec_unavailable",
                "Codex Exec is unavailable because the authenticated Mac host is not configured.",
            )
        try:
            result = subprocess.run(
                [self.executable, "exec-readiness"],
                capture_output=True,
                timeout=20,
                check=False,
                env=self.environment,
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            raise ImageJobError(
                "codex_exec_readiness_unavailable",
                "The Mac host could not report Codex Exec login readiness.",
            ) from error
        if result.returncode != 0 or result.stderr:
            raise ImageJobError(
                "codex_exec_readiness_unavailable",
                "The Mac host could not report Codex Exec login readiness.",
            )
        try:
            return CodexExecReadiness.model_validate_json(result.stdout)
        except (TypeError, ValueError) as error:
            raise ImageJobError(
                "codex_exec_readiness_invalid",
                "The Mac host returned an unsupported Codex Exec readiness state.",
            ) from error

    def require_codex_exec_readiness(self) -> CodexExecReadiness:
        readiness = self.codex_exec_readiness()
        if not readiness.ready:
            raise ImageJobError(
                "codex_exec_not_ready",
                "Codex Exec has no usable local file-store login. Sign in through the existing Codex app CLI, then retry before starting a run.",
            )
        return readiness

    def codex_exec_admit(self, attempt: CodexExecAttempt) -> CodexExecHostStatus:
        """Request one idempotent initial attempt from the Mac-owned supervisor."""
        attempt = CodexExecAttempt.model_validate(attempt.model_dump(mode="python"))
        if attempt.state != "spawn_intent":
            raise ImageJobError("codex_exec_attempt_invalid", "Codex Exec admission requires a persisted spawn intent.")
        return self._codex_exec_request(
            "exec-admit",
            "--attempt-json",
            json.dumps(attempt.model_dump(mode="json", by_alias=True), separators=(",", ":")),
        )

    def codex_exec_status(self, attempt_id) -> CodexExecHostStatus:
        return self._codex_exec_request("exec-status", "--attempt-id", str(UUID(str(attempt_id))))

    def codex_exec_abandonment(self, packet, *, revoke=False):
        from .project_abandonment_contracts import AbandonmentPreview
        if not self.executable:
            raise ImageJobError("codex_exec_unavailable", "无法验证原 Codex Exec 主机；项目保留。")
        try:
            result = subprocess.run([self.executable, "exec-project-revoke" if revoke else "exec-abandonment-preview",
                "--packet-json", packet.model_dump_json(by_alias=True)], capture_output=True,
                timeout=30, check=False, env=self.environment)
            if result.returncode != 0 or result.stderr:
                raise ValueError("unacknowledged abandonment")
            return AbandonmentPreview.model_validate_json(result.stdout)
        except (OSError, subprocess.TimeoutExpired, TypeError, ValueError) as error:
            raise ImageJobError("project_abandonment_unconfirmed", "主机未确认项目放弃；项目保留，请重新核对原任务。") from error

    def codex_exec_cancel(self, attempt: CodexExecAttempt) -> CodexExecHostStatus:
        """Fence a stop against the exact attempt, including pre-admission races."""
        attempt = CodexExecAttempt.model_validate(attempt.model_dump(mode="python"))
        return self._codex_exec_request(
            "exec-cancel",
            "--attempt-json",
            json.dumps(attempt.model_dump(mode="json", by_alias=True), separators=(",", ":")),
        )

    def codex_exec_suspend(self, attempt: CodexExecAttempt) -> CodexExecHostStatus:
        return self._codex_exec_authorize("exec-suspend", attempt)

    def codex_exec_resume(self, attempt: CodexExecAttempt) -> CodexExecHostStatus:
        return self._codex_exec_authorize("exec-resume", attempt)

    def _codex_exec_authorize(self, command, attempt):
        attempt = CodexExecAttempt.model_validate(attempt.model_dump(mode="python"))
        return self._codex_exec_request(command, "--attempt-json",
            json.dumps(attempt.model_dump(mode="json", by_alias=True), separators=(",", ":")))

    def _codex_exec_request(self, command: str, *arguments: str) -> CodexExecHostStatus:
        if not self.executable:
            raise ImageJobError(
                "codex_exec_unavailable",
                "Codex Exec is unavailable because the authenticated Mac host is not configured.",
            )
        try:
            result = subprocess.run(
                [self.executable, command, *arguments],
                capture_output=True,
                timeout=30,
                check=False,
                env=self.environment,
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            raise ImageJobError(
                "codex_exec_outcome_unknown",
                "The Mac supervisor did not acknowledge this Codex Exec operation; inspect the original attempt.",
            ) from error
        if result.returncode != 0 or result.stderr:
            raise ImageJobError(
                "codex_exec_outcome_unknown",
                "The Mac supervisor did not acknowledge this Codex Exec operation; inspect the original attempt.",
            )
        try:
            return CodexExecHostStatus.model_validate_json(result.stdout)
        except (TypeError, ValueError) as error:
            raise ImageJobError(
                "codex_exec_status_invalid",
                "The Mac supervisor returned an unsupported Codex Exec status.",
            ) from error

    @contextmanager
    def idle_guard(self):
        """Hold native admission idle for an explicit preserving operation."""
        with self.lock():
            data = self._read()
            if any((Path(root) / "inflight.json").exists() or (Path(root) / "inflight.json").is_symlink() for root in data["roots"].values()):
                raise ImageJobError("specialist_busy", "原生任务尚未结束，不能升级项目。")
            for job_id in data.get("jobs", {}):
                if self._status(data, job_id)["state"] not in {"prepared", "completed"}:
                    raise ImageJobError("specialist_busy", "保留的发送结果未确定，不能升级项目。")
            yield

    def save(self, settings: SpecialistSettings):
        with self.lock():
            data = self._read()
            if any((Path(p) / "inflight.json").exists() for p in data["roots"].values()):
                raise ImageJobError("specialist_busy", "助手还有未完成的任务，暂时不能更改设置。")
            data["settings"] = settings.model_dump(by_alias=True)
            self._write(data)
        return self.view()

    def _dispatcher(self, data, task_id):
        root = Path(data["roots"].get(task_id, self.root / "dispatch" / task_id))
        data["roots"][task_id] = str(root)
        bootstrap = self.bootstrap if self.bootstrap and task_id == self.bootstrap.task_id else None
        executable = self.executable or (bootstrap.executable if bootstrap else "codex")
        environment = self.environment if self.environment is not None else (bootstrap.environment if bootstrap else None)
        return NativeCodexImageDispatcher(task_id, root, executable, environment)

    def status(self, job_id: str):
        with self.lock():
            return self._status(self._read(), job_id)

    def bind_delivery(self, job_id: str, binding: NativeTaskBinding) -> NativeTaskBinding:
        """Retain the package identity before dispatch can be refused or delayed."""

        binding = NativeTaskBinding.model_validate(binding)
        encoded = binding.model_dump(mode="json", by_alias=True, exclude_none=True)
        with self.lock():
            data = self._read()
            bindings = data.setdefault("deliveryBindings", {})
            existing = bindings.get(job_id)
            if existing is not None and NativeTaskBinding.model_validate(existing) != binding:
                raise ImageJobError(
                    "specialist_binding_changed",
                    "此图像包已冻结到另一个原生任务身份；请重新准备图像任务。",
                )
            if existing is None:
                bindings[job_id] = encoded
                self._write(data)
        return binding

    def delivery_task_binding(self, job_id: str, *, require_bound: bool = False) -> NativeTaskBinding:
        with self.lock():
            data = self._read()
            encoded = data.get("deliveryBindings", {}).get(job_id)
            if encoded is not None:
                return NativeTaskBinding.model_validate(encoded)
            if require_bound:
                raise ImageJobError(
                    "specialist_binding_missing",
                    "图像包的原生任务身份未保留，不能读取其交付。",
                )
            transport = self._status(data, job_id)
            if transport["state"] == "prepared":
                return NativeTaskBinding(mode="current_task")
            return NativeTaskBinding(mode="configured_task", task_id=transport["taskId"])

    def _status(self, data, job_id):
        for task_id, root in data["roots"].items():
            directory = Path(root) / job_id
            if directory.exists():
                receipt = directory / "receipt.json"
                result = json.loads(receipt.read_text()) if receipt.exists() else {"state": "outcome_unknown"}
                return {"state": result["state"], "taskId": task_id}
        return {"state": "prepared"}

    def dispatch(self, role: Role, *, context: dict | None = None, expected_task_id=None, expected_bindings=None, **kwargs):
        with self.lock():
            data = self._read()
            if expected_bindings is not None and expected_bindings != {name: data["settings"][name]["taskId"] for name in ("text", "image")}:
                raise ImageJobError("specialist_binding_changed", "冻结助手配置已变化；任务未发送。")
            task_id = data["settings"][role]["taskId"]
            if expected_task_id is not None and task_id != expected_task_id:
                raise ImageJobError("specialist_binding_changed", "冻结助手身份已变化；任务未发送。")
            if not task_id:
                raise ImageJobError("specialist_unconfigured", "请先在「生成助手设置」中填写助手的聊天 ID。")
            if self._status(data, kwargs["job_id"])["state"] != "prepared":
                raise ImageJobError("specialist_already_sent", "此任务已经尝试发送，请检查结果，不要重复发送。")
            dispatcher = self._dispatcher(data, task_id)
            if context:
                data.setdefault("jobs", {})[kwargs["job_id"]] = context
            self._write(data)
            dispatcher.dispatch(**kwargs)

    def complete(self, job_id: str):
        with self.lock():
            data = self._read()
            self._complete_owned(data, job_id, self._owned_dispatch(data, job_id))

    def assert_image_terminal_identity(self, job_id: str, task_id: str, *, project_id: str, target: str):
        with self.lock():
            self._image_terminal_dispatch(self._read(), job_id, task_id, project_id=project_id, target=target)

    def _image_terminal_dispatch(self, data, job_id, task_id, *, project_id, target, terminal_record=None):
        dispatch = self._owned_dispatch(data, job_id, terminal_record=terminal_record)
        stage = {"image_job": "image", "character_reference_proposal": "character-reference", "art_reference_proposal": "art-reference"}[target]
        if dispatch is None or dispatch[0] != task_id or data.get("jobs", {}).get(job_id) != {"projectId": project_id, "stage": stage}:
            raise ImageJobError("image_terminal_dispatch_identity", "终止声明不匹配保留的图像发送记录；保留预约。")
        return dispatch

    def settle_image_blocked(self, job_id: str, record: dict):
        """Persist validated proof before exact release; never infer termination."""
        with self.lock():
            data = self._read()
            dispatch = self._image_terminal_dispatch(data, job_id, record["marker"]["taskId"], project_id=record["projectId"], target=record["target"], terminal_record=record)
            task_id, receipt, value = dispatch
            prior = value.get("terminalSettlement")
            if prior is not None and prior != record:
                raise ImageJobError("image_terminal_review_changed", "已有不同的终止审核记录；保留预约。")
            if value["state"] == "completed":
                if prior != record:
                    raise ImageJobError("image_terminal_conflict", "此发送已有其他完成结果。")
                return
            active = receipt.parent.parent / "inflight.json"
            if prior == record and active.exists() and self._dispatch_record(active) != {"jobId": job_id, "taskId": task_id}:
                # The identical reviewed proof predates exact release. A later
                # owner can only acquire this cooperating dispatch slot after
                # release; finalize the old tombstone without touching it.
                value["state"] = "completed"
                temporary = receipt.with_suffix(".tmp")
                temporary.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
                temporary.replace(receipt)
                return
            value["terminalSettlement"] = record
            temporary = receipt.with_suffix(".tmp")
            temporary.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
            temporary.replace(receipt)
            # A crash after proof persistence or exact unlink is recoverable by
            # revalidating this same marker and review, without a second send.
            self._complete_owned(data, job_id, (task_id, receipt, value))

    def assert_creative_task_identity(self, job_id: str, *, project_id: str, stage: str):
        with self.lock():
            self._creative_dispatch(self._read(), job_id, project_id, stage)

    def complete_creative_task(self, job_id: str, *, project_id: str, stage: str):
        with self.lock():
            data = self._read()
            dispatch = self._creative_dispatch(data, job_id, project_id, stage)
            self._complete_owned(data, job_id, dispatch)

    def _creative_dispatch(self, data, job_id, project_id, stage):
        dispatch = self._owned_dispatch(data, job_id)
        context = data.get("jobs", {}).get(job_id)
        if (dispatch is not None or context is not None) and context != {"projectId": project_id, "stage": stage}:
            raise ImageJobError("specialist_dispatch_identity", "任务的项目或阶段与保留的发送记录不一致，保留预约。")
        # A current manual delivery has no native attempt or reservation to finish.
        return dispatch

    def _owned_dispatch(self, data, job_id, *, terminal_record=None):
        matches = [(task_id, Path(root)) for task_id, root in data["roots"].items()
                   if (Path(root) / job_id).exists() or (Path(root) / job_id).is_symlink()]
        if not matches:
            return None
        if len(matches) != 1:
            raise ImageJobError("specialist_dispatch_identity", "任务对应多个发送目录，保留预约。")
        task_id, root = matches[0]
        directory = root / job_id
        receipt = directory / "receipt.json"
        if directory.is_symlink():
            raise ImageJobError("specialist_dispatch_identity", "发送记录目录不可用于确认完成，保留预约。")
        value = self._dispatch_record(receipt)
        if value.get("jobId") != job_id or value.get("taskId") != task_id or value.get("state") not in {"queued", "outcome_unknown", "completed"}:
            raise ImageJobError("specialist_dispatch_identity", "发送回执身份不一致，保留预约。")
        active = root / "inflight.json"
        retained_identical_terminal = terminal_record is not None and value.get("terminalSettlement") == terminal_record
        if value["state"] != "completed" and not retained_identical_terminal and (active.exists() or active.is_symlink()) and self._dispatch_record(active) != {"jobId": job_id, "taskId": task_id}:
            raise ImageJobError("specialist_dispatch_identity", "预约属于其他任务，不能确认当前任务完成。")
        return task_id, receipt, value

    @staticmethod
    def _dispatch_record(path):
        try:
            if path.is_symlink() or not path.is_file():
                raise ValueError("unavailable dispatch record")
            value = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(value, dict):
                raise TypeError("invalid dispatch record")
        except (OSError, ValueError, TypeError) as error:
            raise ImageJobError("specialist_dispatch_identity", "无法验证保留的发送记录，保留预约。") from error
        return value

    def _complete_owned(self, data, job_id, dispatch):
        if dispatch is None:
            return
        task_id, receipt, value = dispatch
        if value["state"] == "completed":
            return
        self._dispatcher(data, task_id).complete(job_id)
        root = receipt.parent.parent
        if (root / "inflight.json").exists() or (root / "inflight.json").is_symlink():
            raise ImageJobError("specialist_dispatch_identity", "预约未由当前任务释放，保留发送回执。")
        value["state"] = "completed"
        temporary = receipt.with_suffix(".tmp")
        temporary.write_text(json.dumps(value), encoding="utf-8")
        temporary.replace(receipt)


class ImageSpecialist:
    """Dynamic binding adapter used by existing image package routes."""
    def __init__(self, registry: SpecialistRegistry):
        self.registry = registry

    def dispatch(self, **kwargs):
        self.registry.dispatch("image", **kwargs)

    def configured_task_binding(self) -> NativeTaskBinding:
        task_id = self.registry.view()["image"]["taskId"]
        if not task_id:
            raise ImageJobError("specialist_unconfigured", "请先在「生成助手设置」中填写助手的聊天 ID。")
        return NativeTaskBinding(mode="configured_task", task_id=task_id)

    def bind_delivery(self, job_id: str, binding: NativeTaskBinding) -> NativeTaskBinding:
        return self.registry.bind_delivery(job_id, binding)

    def delivery_task_binding(self, job_id: str, *, require_bound: bool = False) -> NativeTaskBinding:
        return self.registry.delivery_task_binding(job_id, require_bound=require_bound)

    def complete(self, job_id):
        self.registry.complete(job_id)
