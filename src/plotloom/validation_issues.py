from __future__ import annotations

from collections.abc import Iterable

class ValidationIssue(dict):
    """JSON-ready validation issue with a stable code and data path."""

    def __init__(self, code: str, path: str, message: str) -> None:
        super().__init__(code=code, path=path, message=message)


class DomainValidationError(ValueError):
    def __init__(self, issues: Iterable[ValidationIssue]) -> None:
        self.issues = list(issues)
        message = "; ".join(issue["message"] for issue in self.issues)
        super().__init__(message or "domain validation failed")


def _duplicates(values: Iterable[str]) -> set[str]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for value in values:
        if value in seen:
            duplicates.add(value)
        seen.add(value)
    return duplicates


def _issue(code: str, path: str, message: str) -> ValidationIssue:
    return ValidationIssue(code=code, path=path, message=message)
