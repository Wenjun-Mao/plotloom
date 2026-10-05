"""Project-specific native execution admission, independent of publication state."""
from pathlib import Path


def project_execution_blockers(application_root: Path, project_id: str, retained_jobs: set[str]) -> list[str]:
    from .specialist_settings import SpecialistRegistry
    from .image_job_contracts import ImageJobError

    settings = application_root / "specialists" / "settings.json"
    if not settings.exists():
        # Lifecycle reads must not bootstrap empty settings ahead of the actual
        # transport configuration. Lost metadata with retained dispatch is unsafe.
        if (settings.parent / "dispatch").exists():
            raise ImageJobError("specialist_dispatch_identity", "无法验证助手所有权记录，保留项目。")
        return []
    registry = SpecialistRegistry(application_root)
    # Callers hold the project's exclusive lease. Dispatch holds its shared lease
    # before this registry lock; no registry operation acquires a project lease.
    with registry.lock():
        data = registry._read()
        contexts = data.get("jobs", {})
        owned = {job for job, context in contexts.items()
                 if isinstance(context, dict) and context.get("projectId") == project_id}
        # Retained project job identity also protects pre-context image attempts
        # and damaged/missing ownership metadata; it never guesses from global busy.
        owned.update(retained_jobs)
        for task_id, root_value in data["roots"].items():
            root = Path(root_value)
            active = root / "inflight.json"
            if active.exists() or active.is_symlink():
                lease = registry._dispatch_record(active)
                if lease.get("jobId") in owned:
                    return ["native_specialist_execution_unresolved"]
            for job in owned:
                directory = root / job
                if not directory.exists() and not directory.is_symlink():
                    continue
                # Absence of a receipt is the crash window after reservation;
                # absence of the lease is the crash window before tombstoning.
                receipt = directory / "receipt.json"
                if directory.is_symlink() or not receipt.exists():
                    return ["native_specialist_execution_unresolved"]
                value = registry._dispatch_record(receipt)
                if (value.get("jobId") != job or value.get("taskId") != task_id
                        or value.get("state") != "completed"):
                    return ["native_specialist_execution_unresolved"]
        return []
