"""Provenance for machine adoption, never an author review flag."""
from pydantic import Field
from plotloom.domain_base import CamelModel


class MachineAdoption(CamelModel):
    run_id: str
    decision_id: str
    policy_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    proposal_revision: int = Field(ge=1)
    proposal_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    job_id: str
    request_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    delivery_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
