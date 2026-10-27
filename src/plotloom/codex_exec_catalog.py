"""Pure pairing of the current CLI's two observed empty catalog observations."""
from dataclasses import dataclass
from hashlib import sha256
import json


EMPTY_CATALOG_RESULTS = {
    "list_mcp_resources": '{"resources":[]}',
    "list_mcp_resource_templates": '{"resourceTemplates":[]}',
}
MAX_CATALOG_CALLS = 128
MAX_CATALOG_RECORD_BYTES = 16_384
MAX_CATALOG_ID_BYTES = 128


def _unique_fields(pairs):
    result = {}
    for name, value in pairs:
        if name in result:
            raise ValueError("catalog JSON repeats a field")
        result[name] = value
    return result


@dataclass(frozen=True)
class ExecEmptyCatalogCall:
    item_id: str
    tool: str
    started_ordinal: int
    started_sha256: str
    started_size_bytes: int
    completed_ordinal: int
    completed_sha256: str
    completed_size_bytes: int


class EmptyCatalogItems:
    """Only completed, exact empty catalogs can leave this local reader state."""

    def __init__(self):
        self.item_ids: set[str] = set()
        self.pending: dict[str, tuple[str, int, str, int]] = {}
        self.calls: list[ExecEmptyCatalogCall] = []

    def accept(self, record, raw, ordinal, foreign_ids):
        if set(record) != {"type", "item"} or len(raw) > MAX_CATALOG_RECORD_BYTES:
            raise ValueError("catalog envelope is not the bounded observed shape")
        if json.loads(raw, object_pairs_hook=_unique_fields) != record:
            raise ValueError("catalog bytes differ from the inspected envelope")
        item = record["item"]
        if set(item) != {"id", "type", "server", "tool", "arguments", "result", "error", "status"}:
            raise ValueError("catalog item fields differ from the observed shape")
        item_id, tool = item["id"], item["tool"]
        if (not isinstance(item_id, str) or not item_id or len(item_id.encode("utf-8")) > MAX_CATALOG_ID_BYTES
                or item["type"] != "mcp_tool_call" or item["server"] != "codex"
                or not isinstance(tool, str) or tool not in EMPTY_CATALOG_RESULTS
                or item["arguments"] != {} or item["error"] is not None):
            raise ValueError("catalog identity, tool, arguments or error is not qualified")
        digest = sha256(raw).hexdigest()
        if record["type"] == "item.started":
            if (item_id in self.item_ids or item_id in foreign_ids
                    or len(self.item_ids) >= MAX_CATALOG_CALLS
                    or item["status"] != "in_progress" or item["result"] is not None):
                raise ValueError("catalog start is repeated, unbounded or not empty")
            self.item_ids.add(item_id)
            self.pending[item_id] = (tool, ordinal, digest, len(raw))
        elif record["type"] == "item.completed":
            expected = {"content": [{"type": "text", "text": EMPTY_CATALOG_RESULTS[tool]}],
                        "structured_content": None}
            started = self.pending.get(item_id)
            if (started is None or started[0] != tool or item["status"] != "completed"
                    or item["result"] != expected):
                raise ValueError("catalog completion is unmatched or not the exact empty result")
            self.pending.pop(item_id)
            self.calls.append(ExecEmptyCatalogCall(item_id, tool, *started[1:], ordinal, digest, len(raw)))
        else:
            raise ValueError("catalog event is not a started/completed pair")
