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
    def __init__(self, root: Path, image: NativeCodexImageDispatcher | None = None):
        self.root = root / "specialists"
        self.root.mkdir(parents=True, exist_ok=True)
        self.path = self.root / "settings.json"
        self.bootstrap = image
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
        executable = self.bootstrap.executable if self.bootstrap and task_id == self.bootstrap.task_id else "codex"
        return NativeCodexImageDispatcher(task_id, root, executable)

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
            for task_id, root in data["roots"].items():
                receipt = Path(root) / job_id / "receipt.json"
                if receipt.exists():
                    self._dispatcher(data, task_id).complete(job_id)
                    value = json.loads(receipt.read_text())
                    value["state"] = "completed"
                    receipt.write_text(json.dumps(value), encoding="utf-8")


class ImageSpecialist:
    """Dynamic binding adapter used by existing image package routes."""
    def __init__(self, registry: SpecialistRegistry):
        self.registry = registry

    def dispatch(self, **kwargs):
        self.registry.dispatch("image", **kwargs)

    def complete(self, job_id):
        self.registry.complete(job_id)
