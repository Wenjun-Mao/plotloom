"""Private one-job entrypoint installed into each engine environment."""

from __future__ import annotations

import importlib.metadata
import json
import os
import random
import subprocess
import sys
from pathlib import Path

from .protocol import RunnerRequest, RunnerEvent
from ..media import file_sha256


def failure_code(error: Exception) -> str:
    if isinstance(error, FileNotFoundError):
        return 'model.unavailable'
    torch = sys.modules.get('torch')
    if torch is not None:
        oom_type = getattr(torch, 'OutOfMemoryError', None)
        accelerator_type = getattr(torch, 'AcceleratorError', None)
        if isinstance(oom_type, type) and isinstance(error, oom_type):
            return 'generation.oom'
        if isinstance(accelerator_type, type) and isinstance(error, accelerator_type) and 'out of memory' in str(error).lower():
            return 'generation.oom'
    return str(error) if str(error) in {'model.integrity_failed', 'audio.invalid'} else 'generation.failed'


def main() -> None:
    request = RunnerRequest.model_validate_json(Path(sys.argv[1]).read_text())
    events = Path(request.events)

    def emit(kind, **fields):
        value = RunnerEvent(kind=kind, **fields)
        with events.open("a", encoding="utf-8") as stream:
            stream.write(value.model_dump_json(exclude_none=True) + "\n")
            stream.flush()
            os.fsync(stream.fileno())

    try:
        for file, digest in request.runtime["fileChecks"].items():
            if file_sha256(Path(file)) != digest:
                raise ValueError("model.integrity_failed")
        source = request.runtime.get("sourceDir")
        if source and subprocess.check_output(["git", "-C", source, "rev-parse", "HEAD"], text=True).strip() != request.snapshot["sourceRevision"]:
            raise ValueError("model.integrity_failed")
        for package, version in request.runtime["packages"].items():
            if importlib.metadata.version(package) != version:
                raise ValueError("model.integrity_failed")
        import numpy as np
        import torch
        if not torch.cuda.is_available():
            raise FileNotFoundError('model.unavailable')
        random.seed(request.seed)
        np.random.seed(request.seed)
        torch.manual_seed(request.seed)
        torch.cuda.manual_seed_all(request.seed)
        emit("phase", phase="loading_model")
        engine = request.snapshot["engineId"]
        if engine.startswith("qwen_"):
            from .qwen import generate
        elif engine == "moss_design":
            from .moss import generate
        else:
            from .index import generate
        generate(request, emit)
        emit("complete", peakTorchGiB=round(torch.cuda.max_memory_allocated() / 1024**3, 3))
    except Exception as error:
        import traceback
        traceback.print_exc()
        emit("failure", errorCode=failure_code(error))
        raise SystemExit(1)


if __name__ == "__main__":
    main()
