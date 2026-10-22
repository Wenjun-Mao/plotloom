import type { CharacterReferenceDecision, CharacterReferencesResponse } from "../../../types";

/** Cast selection is not a selection against the installed production character. */
export function currentProductionReferences(references: CharacterReferencesResponse): Map<string, CharacterReferenceDecision> {
  return new Map(references.decisions.filter(decision =>
    decision.current && decision.characterContext.authority === "story_bible" &&
    references.states.some(state => state.characterId === decision.characterId &&
      state.current && state.activeDecisionId === decision.id),
  ).map(decision => [decision.characterId, decision]));
}
