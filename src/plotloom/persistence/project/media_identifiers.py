"""Namespaced identifiers for durable project-media records."""

from plotloom.contract_identity import new_id


def new_image_job_id() -> str:
    """Return the established durable identifier form for image work."""

    return f"ij_{new_id().replace('-', '')}"


def new_video_job_id() -> str:
    """Return the established durable identifier form for video work."""

    return f"vj_{new_id().replace('-', '')}"
