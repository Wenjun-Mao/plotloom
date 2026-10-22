"""Receiving instructions for global context in native automatic image work."""

IMAGE_CONTENT_OWNERSHIP_CONTRACT = "plotloom.autopilot.image-content-ownership.v1"


IMAGE_CONTENT_OWNERSHIP_INSTRUCTION = (
    f"IMAGE CONTENT OWNERSHIP CONTRACT ({IMAGE_CONTENT_OWNERSHIP_CONTRACT}): "
    "In this automatic package, visualDirection, renderDirection or creatorDirection.presentationChange "
    "contains a task-purpose label and may append global Brief visual direction. That global direction is "
    "rendering-treatment context, not a per-image entity inventory or a new creator content override. "
    "Honor the style authority frozen in the accepted Cast/Art: saved-Brief direction or an explicitly selected "
    "preset. Do not assume a preset-authoritative stage translated the saved Brief as its style authority. "
    "When global direction is absent, retain that frozen style authority; an empty saved-Brief direction "
    "allows story-informed visual judgment without inventing a preset. "
    "For a character reference, the frozen accepted Cast character owns included and excluded entities. "
    "For an art reference, the frozen accepted Art subject, including its prompt, sheet and negative prompt, "
    "owns included and excluded entities. For a shot image, the frozen canonical shot and resolved physical "
    "presentation own visible content, action and composition. Reference images supply only their declared "
    "identity/appearance roles; do not transfer a reference study's framing or entity exclusions into the shot. "
    "Apply global rendering treatment to the content owned by that task. A subject mentioned in global "
    "context does not require adding it to a reference or shot that excludes it. Preserve the raw direction; "
    "do not strip or rewrite its subject words. If requirements within the actual content owner contradict "
    "each other, or the rendering treatment cannot be applied faithfully under the frozen style authority, "
    "stop and report the exact conflict. This contract does not authorize silently overriding a genuine contradiction. "
)
