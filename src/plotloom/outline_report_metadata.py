"""Outline report metadata projection; upstream creative fields remain opaque."""
import json
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, ValidationError

from .creative_handoff_contracts import CreativeHandoffError

OUTLINE_REPORT_SCHEMA_FILENAME = "outline-report-metadata-schema.json"


class OutlineReportMetadata(BaseModel):
    model_config = ConfigDict(strict=True, extra="allow")

    lang: Literal["zh", "en"] | None = None


def outline_report_metadata_schema() -> dict[str, Any]:
    return OutlineReportMetadata.model_json_schema()


def assert_outline_report_schema_current(artifacts: dict[str, Any]) -> None:
    schema = artifacts.get(OUTLINE_REPORT_SCHEMA_FILENAME)
    if schema is None:
        raise CreativeHandoffError("outline_report_schema_missing", "outline report metadata schema is required")
    if json.dumps(schema, sort_keys=True, ensure_ascii=False) != json.dumps(
        outline_report_metadata_schema(), sort_keys=True, ensure_ascii=False,
    ):
        raise CreativeHandoffError("outline_report_schema_stale", "outline report metadata schema is not current")


def assert_outline_report_metadata(candidate: dict[str, Any]) -> None:
    try:
        # Discard the projection: the original dictionary and bytes own the delivery.
        OutlineReportMetadata.model_validate(candidate)
    except ValidationError as error:
        raise CreativeHandoffError(
            "outline_report_metadata_invalid", "Outline report lang must be omitted, null, or exactly zh/en",
        ) from error
