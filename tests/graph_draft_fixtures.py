"""Current shared graph acknowledgment for disposable source journey fixtures."""
from plotloom.graph_draft_creation import create_graph_draft
from plotloom.persistence.project.graph_workbench import GraphDraftRebaseRequest
from plotloom.source_outline_contracts import SectionMapSaveRequest


def save_graph_mapping(store, mapping):
    state = store.graph_workbench_state()
    draft = create_graph_draft(binding_hash=state.binding_hash, seed=mapping.seed_topology,
        mapping=mapping.model_dump(mode="json", by_alias=True))
    if state.draft and state.draft.payload["bindingHash"] != state.binding_hash:
        store.rebase_graph_draft(GraphDraftRebaseRequest(expected_draft_revision=state.draft.draft_revision,
            expected_binding_hash=state.binding_hash, payload=None))
        state = store.graph_workbench_state()
    return store.save_authoring_draft(editor_scope="story_graph", entity_id="root",
        base_canonical_revision=state.base_canonical_revision,
        expected_draft_revision=state.draft.draft_revision if state.draft else 0,
        payload=draft.model_dump(mode="json", by_alias=True))


def graph_map_save_request(store, **kwargs):
    receipt = save_graph_mapping(store, kwargs["mapping"])
    return SectionMapSaveRequest(expected_graph_draft_revision=receipt.draft_revision, **kwargs)


def graph_draft_revision(store):
    return store.graph_workbench_state().draft.draft_revision
