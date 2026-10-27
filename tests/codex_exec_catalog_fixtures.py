"""Exact observed empty-catalog envelopes for provider-free consumer contracts."""


def empty_catalog_pair(tool="list_mcp_resources", item_id="catalog_1"):
    key = "resources" if tool == "list_mcp_resources" else "resourceTemplates"
    item = {"id": item_id, "type": "mcp_tool_call", "server": "codex", "tool": tool,
            "arguments": {}, "result": None, "error": None, "status": "in_progress"}
    return [{"type": "item.started", "item": item},
            {"type": "item.completed", "item": item | {"status": "completed",
             "result": {"content": [{"type": "text", "text": '{"' + key + '":[]}'}],
                        "structured_content": None}}}]
