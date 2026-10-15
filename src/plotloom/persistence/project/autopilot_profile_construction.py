"""Private structural construction reuse within one ordinary validation pass."""

from ...codex_exec_contracts import CodexExecProfile


class _ProfileConstruction:
    """One successful profile, guarded by the freshly selected exact policy TEXT.

    This owns no database observations or authority. Its caller still selects,
    decodes and checks every row at the original point (ADR 0177).
    """

    __slots__ = ("_policy_text", "_profile")

    def __init__(self):
        self._policy_text = None
        self._profile = None

    def resolve(self, raw_policy, policy) -> CodexExecProfile:
        previous_text, previous_profile = self._policy_text, self._profile
        # Clear first so extraction or replacement failure cannot retain success.
        self._policy_text = self._profile = None
        binding = policy.get("executorBinding", {})
        is_text = type(raw_policy) is str
        if is_text and raw_policy == previous_text and previous_profile is not None:
            profile = previous_profile
        else:
            profile = CodexExecProfile.model_validate(binding)
        if is_text:
            self._policy_text, self._profile = raw_policy, profile
        return profile
