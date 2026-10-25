import { plotloomApi } from "../../api";
import { sameDraftPayload } from "../../app/workspace/contracts";

/** Reconcile a lost response only; never reset CAS or replay a mutation. */
export async function saveWorkingDraft(projectId: string, request: Parameters<typeof plotloomApi.saveAuthoringDraft>[1]) {
  try { return await plotloomApi.saveAuthoringDraft(projectId, request); }
  catch (failure) {
    try {
      const observed = (await plotloomApi.getAuthoringDrafts(projectId)).find(draft => draft.editorScope === request.editorScope && draft.entityId === request.entityId);
      if (observed && observed.baseCanonicalRevision === request.baseCanonicalRevision && observed.draftRevision === request.expectedDraftRevision + 1
        && sameDraftPayload(observed.payload, request.payload)) return observed;
    } catch { /* The original failure owns error/status, with local input retained. */ }
    throw failure;
  }
}
