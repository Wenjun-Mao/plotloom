"""Installation-local specialist bindings and serialized dispatch ownership."""
from __future__ import annotations

import fcntl
import json
from contextlib import contextmanager
from pathlib import Path
from typing import Literal
from uuid import UUID

from pydantic import Field, field_validator, model_validator

from .codex_image_dispatch import NativeCodexImageDispatcher
from .domain import CamelModel
from .image_job_contracts import ImageJobError

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

    def _status(self, data, job_id):
        for task_id, root in data["roots"].items():
            directory = Path(root) / job_id
            if directory.exists():
                receipt = directory / "receipt.json"
                result = json.loads(receipt.read_text()) if receipt.exists() else {"state": "outcome_unknown"}
                return {"state": result["state"], "taskId": task_id}
        return {"state": "prepared"}

    def dispatch(self, role: Role, *, context: dict | None = None, **kwargs):
        with self.lock():
            data = self._read()
            task_id = data["settings"][role]["taskId"]
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

    def _owned_dispatch(self, data, job_id):
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
        if value["state"] != "completed" and (active.exists() or active.is_symlink()) and self._dispatch_record(active) != {"jobId": job_id, "taskId": task_id}:
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

    def complete(self, job_id):
        self.registry.complete(job_id)
