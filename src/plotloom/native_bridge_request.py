"""Finite complete-file admission, independent of the API prompt budget."""
from .creative_handoff_contracts import CreativeHandoffRequest
from .creative_handoff_exchange import canonical_json
from .exceptions import InvalidTransitionError

MAX_NATIVE_BRIDGE_REQUEST_BYTES = 1_048_576
MAX_NATIVE_BRIDGE_PACKAGE_JSON_BYTES = 2_000_000


def assert_native_bridge_request_size(request: CreativeHandoffRequest) -> None:
    if request.stage not in {"bridge-intent", "bridge-presentation"}:
        raise ValueError("native bridge budget requires an intent or presentation request")
    # Bind the complete request, not a thinner prompt view that omits schemas,
    # identity or trusted evidence. This bound does not promise model capacity.
    encoded = canonical_json(request.model_dump(mode="json", by_alias=True))
    if len(encoded) > MAX_NATIVE_BRIDGE_REQUEST_BYTES:
        raise InvalidTransitionError("native bridge request exceeds the bounded one-package request limit")
