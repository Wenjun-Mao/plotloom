"""One owned namespace; complete payload bytes precede empty commit authority."""
import hashlib
import json
import os
import stat
from pathlib import Path


def require(value, message):
    if not value:
        raise RuntimeError(message)


def canonical(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True,
        separators=(",", ":"), allow_nan=False) + "\n").encode()


def digest(value):
    return hashlib.sha256(value).hexdigest()


def identity(info):
    return (info.st_dev, info.st_ino, info.st_uid, info.st_mode,
        info.st_nlink, info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def owned_root(root):
    root = Path(root)
    require(root.is_absolute(), "absolute namespace required")
    for parent in [*reversed(root.parents), root]:
        info = parent.lstat()
        require(stat.S_ISDIR(info.st_mode), "linked or nondirectory namespace")
    info = root.lstat()
    require(info.st_uid == os.getuid() and stat.S_IMODE(info.st_mode) == 0o700,
        "namespace must be owned and private")
    return root


def read_owned(path, *, private=True, limit=1_000_000):
    path = Path(path)
    before = path.lstat()
    require(stat.S_ISREG(before.st_mode) and before.st_uid == os.getuid()
        and before.st_nlink == 1 and before.st_size <= limit
        and (stat.S_IMODE(before.st_mode) == 0o600 if private else not before.st_mode & 0o022),
        "unsafe owned regular file")
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, "rb") as stream:
        require(identity(before) == identity(os.fstat(stream.fileno())), "open identity changed")
        content = stream.read(limit + 1)
        require(len(content) <= limit and identity(before) == identity(os.fstat(stream.fileno()))
            and identity(before) == identity(path.lstat()), "read identity changed")
    return content


def parse(content):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, "duplicate JSON field")
            result[key] = value
        return result
    value = json.loads(content, object_pairs_hook=pairs,
        parse_constant=lambda _value: require(False, "invalid JSON number"))
    require(canonical(value) == content, "noncanonical JSON")
    return value


def sync_directory(root):
    fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def exclusive_bytes(root, name, content):
    root = owned_root(root)
    require(Path(name).name == name, "unbound record path")
    path = root / name
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "wb") as stream:
        before = os.fstat(stream.fileno())
        stream.write(content)
        stream.flush()
        os.fsync(stream.fileno())
    sync_directory(root)
    after = path.lstat()
    require((before.st_dev, before.st_ino) == (after.st_dev, after.st_ino)
        and read_owned(path) == content, "publication readback changed")
    return digest(content)


def publish_record(root, name, value):
    content = canonical(value)
    sha = exclusive_bytes(root, name, content)
    exclusive_bytes(root, name + ".ready-" + sha, b"")
    return sha


def read_record(root, name, *, gate=lambda: None):
    root = owned_root(root)
    gate()
    prefix = name + ".ready-"
    markers = [entry.name for entry in root.iterdir() if entry.name.startswith(prefix)]
    gate()
    if not markers:
        return None
    require(len(markers) == 1, "multiple record authorities")
    marker = markers[0]
    suffix = marker[len(prefix):]
    require(len(suffix) == 64 and all(c in "0123456789abcdef" for c in suffix), "malformed record marker")
    marker_identity = identity((root / marker).lstat())
    require(read_owned(root / marker) == b"", "record marker must be empty")
    content = read_owned(root / name)
    require(digest(content) == suffix, "record hash mismatch")
    value = parse(content)
    final_markers = [entry.name for entry in root.iterdir() if entry.name.startswith(prefix)]
    require(final_markers == markers, "record authority set changed during payload read")
    require(marker_identity == identity((root / marker).lstat()), "record marker identity changed")
    gate()
    return value, suffix
