from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class StoryboardObservation:
    """One ordered observation, without evaluator identity or hash authority."""

    gate_id: str
    passed: bool | None
    path: tuple[str | int, ...] = ()
    reason: str = ""
    evidence: tuple[tuple[str, object], ...] = ()
    required: bool = True

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "evidence", tuple((key, str(value)) for key, value in self.evidence)
        )
