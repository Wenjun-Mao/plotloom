"""Operation-scoped reads of already ingested selected media, never admission."""
from contextlib import contextmanager
from contextvars import ContextVar
from hashlib import sha256
import re

_SELECTED = ContextVar("plotloom_selected_playback_project", default=None)


def selected_playback_read(project_id=None):
    current = _SELECTED.get()
    return current is not None and (project_id is None or current == project_id)


@contextmanager
def selected_playback_policy(project_id):
    """Used only by the selected-media read owner; reset on every exit path."""
    token = _SELECTED.set(project_id)
    try:
        yield
    finally:
        _SELECTED.reset(token)


def retained_style_matches(contract, direction):
    """Frozen style integrity + actual author direction, independent of code files."""
    if not isinstance(contract, dict):
        return False
    if contract.get("authority") == "saved_brief":
        from ...codex_exec_retained_visual import _assert_frozen_brief
        try:
            _assert_frozen_brief(contract)
        except (ValueError, TypeError, KeyError):
            return False
        return contract["direction"] == direction
    hash_key = "implementationHash" if "implementationHash" in contract else "adapterHash"
    return (set(contract) == {"version","style","authorDirection","preset",hash_key}
        and contract["version"] == 1 and contract["authorDirection"] == direction
        and contract["style"] in {"live-action","realistic","ghibli"}
        and isinstance(contract[hash_key],str) and re.fullmatch(r"[a-f0-9]{64}",contract[hash_key]) is not None
        and isinstance(contract["preset"],dict))


def retained_timing_matches(contract, script, script_hash, language):
    """Verify original scalar/coordinate hashes; never estimate old speech anew."""
    if contract is None or contract.script_content_hash != script_hash or contract.language != language:
        return False
    rows=[]
    for episode in script.get("episodes",[]):
        for si,scene in enumerate(episode.get("scenes",[]),1):
            for fi,flow in enumerate(scene.get("flow",[]),1):
                if isinstance(flow.get("line"),str):
                    pace=flow.get("delivery") if flow.get("delivery") in ("measured","natural","brisk") else "natural"
                    rows.append((episode["ep"],si,fi,sha256(flow["line"].encode()).hexdigest(),pace))
    return rows == [(line.episode,line.scene_index,line.flow_index,line.text_hash,line.delivery.value) for line in contract.lines]


def selected_dialogue_timing(session, project_id, script, script_hash, language):
    """Use the accepted timing evidence for selected reads, without new estimates."""
    if not selected_playback_read(project_id):
        return None
    from ..schema import StoryboardReviewHeadRow, StoryboardReviewRevisionRow
    from ...storyboard_review_contracts import StoryboardReviewBinding
    from sqlalchemy import select
    head = session.get(StoryboardReviewHeadRow, project_id)
    row = session.scalar(select(StoryboardReviewRevisionRow).where(
        StoryboardReviewRevisionRow.project_id == project_id,
        StoryboardReviewRevisionRow.revision == head.revision)) if head is not None and head.status == "accepted" else None
    frozen = StoryboardReviewBinding.model_validate(row.binding).dialogue_timing_contract if row is not None else None
    if not retained_timing_matches(frozen, script, script_hash, language):
        raise ValueError("recorded selected timing differs from actual accepted source")
    return frozen
