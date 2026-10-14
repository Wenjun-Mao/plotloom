"""Fixed, versioned instructions for one frozen Codex Exec assignment."""
from pathlib import Path


PROMPT_VERSION = "plotloom.codex-exec-assignment.v2"


def assignment_prompt(*, job_id: str, package_path: Path, delivery_path: Path, domain: str) -> str:
    """Tell one attempt worker how its trusted package and delivery are owned."""
    if domain not in {"text", "image"}:
        raise ValueError("Codex Exec assignment requires a supported delivery domain")
    delivery_authority = (
        f"Write only the requested candidate and report files to {delivery_path}. The trusted host publishes "
        "the completion manifest after validating their exact bytes. "
        if domain == "text" else
        f"Do not write image files or completion markers into {delivery_path}. Use only the built-in ImageGen "
        "tool described by the frozen package; the trusted host copies its exact completed session output and "
        "publishes the completion manifest after validating the event, arguments and bytes. "
    )
    return (
        f"{PROMPT_VERSION}\n"
        f"This is the single frozen Plotloom job {job_id}. Read the complete package at "
        f"{package_path} and obey its COPY_ASSIGNMENT.txt and pinned skill instructions. "
        + delivery_authority
        + "Do not edit package files, project canon, approvals, selections, settings, or user data. "
        "Use only the built-in Codex tools enabled by this invocation. Do not start another job, "
        "use another provider, or contact services outside those enabled tools. Do not claim completion without the exact "
        "files and trusted completion manifest required by the package. The result remains a candidate "
        "for Plotloom validation and human review."
    )
