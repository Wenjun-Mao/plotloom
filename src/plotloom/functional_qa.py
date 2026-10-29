"""The owner's functional-only amendment applies to two disposable examples."""
from .exceptions import InvalidTransitionError

FUNCTIONAL_QA_SCOPES = (
    ("2458559c-b6cf-4d98-9921-bd169e2b6769", "project-language-zh-native-20261029"),
    ("a278ed7d-6244-4775-88cf-97250d0ebb22", "project-language-en-native-20261029"),
)


def functional_qa_authorized(project_id, actor):
    return (isinstance(actor, dict) and set(actor) == {"kind", "scopeId"}
        and actor["kind"] == "agent_operated_qa"
        and (project_id, actor["scopeId"]) in FUNCTIONAL_QA_SCOPES)


def assert_functional_qa(project_id, actor):
    if not functional_qa_authorized(project_id, actor):
        raise InvalidTransitionError("functional-only acceptance requires the exact owner-authorized disposable QA actor")
