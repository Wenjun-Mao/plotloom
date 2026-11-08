"""Content binding and JSON Pointer utilities; inputs are data, not code."""
import hashlib
import json
from pathlib import Path


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def pin(path):
    p = Path(path).resolve(strict=True)
    return {"file": str(p), "sha256": digest(p)}


def pointer(obj, path):
    if not path.startswith("/"):
        raise ValueError("evidence pointer must be absolute")
    for token in path[1:].split("/"):
        token = token.replace("~1", "/").replace("~0", "~")
        obj = obj[int(token)] if isinstance(obj, list) else obj[token]
    return obj


def save(path, obj):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    if p.exists():
        raise ValueError(f"output already exists: {p}")
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def evidence(source, path, ident):
    return {"id": ident, "source": source, "pointer": path}


def verify_case(case):
    if case.get("schemaVersion") != 1 or case.get("skillVersion") != "0.1.1":
        raise ValueError("unsupported case version")
    sources = case["sources"]
    for name, row in sources.items():
        if digest(row["file"]) != row["sha256"]:
            raise ValueError(f"stale source: {name}")
    docs = {k: read(v["file"]) for k, v in sources.items()}
    ids = set()
    for row in case["evidence"]:
        if row["id"] in ids:
            raise ValueError("duplicate evidence id")
        ids.add(row["id"])
        pointer(docs[row["source"]], row["pointer"])
    if not ids:
        raise ValueError("empty evidence")
    return ids
