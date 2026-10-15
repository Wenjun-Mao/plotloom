"""Finite trusted host capacity, frozen in every current CLI profile."""
from pydantic import Field, model_validator

from .domain import CamelModel


class CodexExecPoolLimits(CamelModel):
    model_config = CamelModel.model_config | {"frozen": True}

    max_processes: int = Field(default=4, ge=1, le=4, strict=True)
    max_text_processes: int = Field(default=2, ge=1, le=2, strict=True)
    max_image_processes: int = Field(default=2, ge=1, le=2, strict=True)
    max_queued_jobs: int = Field(default=4, ge=1, le=4, strict=True)

    @model_validator(mode="after")
    def domains_fit_global_capacity(self):
        if max(self.max_text_processes, self.max_image_processes) > self.max_processes:
            raise ValueError("domain capacity cannot exceed installation capacity")
        return self

    def domain_capacity(self, domain: str) -> int:
        if domain == "text":
            return self.max_text_processes
        if domain == "image":
            return self.max_image_processes
        raise ValueError("unsupported Codex Exec capacity domain")
