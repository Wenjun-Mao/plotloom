"""Immutable image package reference values."""
from dataclasses import dataclass


@dataclass(frozen=True)
class PackageReference:
    role: str
    filename: str
    content_hash: str
    content: bytes
