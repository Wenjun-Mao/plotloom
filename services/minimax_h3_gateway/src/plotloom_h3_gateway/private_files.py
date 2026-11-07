"""Exclusive private media writes shared by reference-image and voice intake."""
import os
from pathlib import Path


def write_new(path: Path, content: bytes, *, owner: tuple[int, int] | None = None) -> None:
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(content)
            if owner is not None:
                os.fchown(stream.fileno(), *owner)
    except OSError:
        path.unlink(missing_ok=True)
        raise
