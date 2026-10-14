"""Fixed, versioned instructions for one frozen Codex Exec assignment."""
from pathlib import Path


PROMPT_VERSION = "plotloom.codex-exec-assignment.v3"


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
    image_call_contract = (
        "Make exactly one ImageGen call for this serial attempt, as one direct top-level awaited expression: "
        "`await tools.image_gen__imagegen({prompt: <literal string>, images: <literal package paths when needed>, "
        "transparent_background: <literal boolean>})`. Keep the call arguments literal. Do not put it in a branch, "
        "function, helper, template, conditional, or a JavaScript snippet containing other statements; the host "
        "can only bind the native completion event to this exact source shape. Stop if that shape cannot express the task. "
        if domain == "image" else ""
    )
    source_runtime_contract = (
        "Text-stage validators are available only through the read-only source resources named by the package. "
        "Keep the working directory in the assigned delivery. For upstream commands templated with `{baseDir}`, "
        "use the parent directory of the pinned `upstreamSkillPath` in request.json. For Shuohao stages, this is "
        "the skill directory, not the checkout root. For Plotloom validators, address scripts with absolute paths under "
        "`$PLOTLOOM_SOURCE_ROOT`; for Node validators use `\"$PLOTLOOM_NODE\"`, and for Python validators use "
        "`\"$PLOTLOOM_UV\" run --project \"$PLOTLOOM_SOURCE_ROOT\" "
        "--locked --no-sync` so the locked existing environment is used without changing it. Do not `cd` into "
        "or write to the source checkout. "
        if domain == "text" else ""
    )
    return (
        f"{PROMPT_VERSION}\n"
        f"This is the single frozen Plotloom job {job_id}. Read the complete package at "
        f"{package_path} and obey its COPY_ASSIGNMENT.txt and pinned source instructions. "
        + delivery_authority
        + image_call_contract
        + source_runtime_contract
        + "Do not edit package files, project canon, approvals, selections, settings, or user data. "
        "Use only the built-in Codex tools enabled by this invocation. Do not start another job, "
        "use another provider, or contact services outside those enabled tools. Do not claim completion without the exact "
        "files and trusted completion manifest required by the package. The result remains a candidate "
        "for Plotloom validation and human review."
    )
