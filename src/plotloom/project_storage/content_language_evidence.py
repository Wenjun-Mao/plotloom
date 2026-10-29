"""Checker attempts participate in native inventory, recovery and quiescence."""
import json
from types import SimpleNamespace

from ..content_language_contract import CHECK_OPERATION
from ..content_language_persistence import verified_check
from .format import ProjectStorageCorruptionError


def retained_language_checks(connection):
    if not connection.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='v2_source_outline_candidates'").fetchone():
        return []
    cursor = connection.execute("SELECT * FROM v2_source_outline_candidates WHERE json_extract(request,'$.source.operation')=?",
                                (CHECK_OPERATION,))
    names = [column[0] for column in cursor.description]
    result = []
    for row in cursor:
        values = dict(zip(names, row, strict=True))
        for name in ("request", "outline"):
            values[name] = json.loads(values[name])
        try:
            request, data, attempt, profile, receipt, _result = verified_check(SimpleNamespace(**values))
        except (ValueError, TypeError, KeyError) as error:
            raise ProjectStorageCorruptionError("retained native language checking evidence changed") from error
        result.append((request, data, attempt, profile, receipt))
    return result
