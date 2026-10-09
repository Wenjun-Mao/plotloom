import { expect, it } from "vitest";
import { currentProductionReferences } from "../src/features/media/references/production-reference";
import type { CharacterReferenceDecision, CharacterReferencesResponse } from "../src/types";

function referenceFixture(authority: string): CharacterReferencesResponse {
  const decision: CharacterReferenceDecision = {
    id: "selected", projectId: "one", characterId: "C01", referenceRevision: 1,
    characterContext: { authority }, characterContextHash: "hash", primaryAssetId: "asset",
    complementaryAssetIds: [], assetHashes: [{ assetId: "asset", originalHash: "hash" }],
    reviewer: null, notes: null, current: true, revokedAt: null, revokedBy: null,
    revocationReason: null, createdAt: "2026-10-09T00:00:00Z",
  };
  return { states: [{ characterId: "C01", activeDecisionId: decision.id, revision: 1, current: true }], decisions: [decision] };
}

it.each(["cast", "unknown"])("does not admit %s-owned selections as production references", authority => {
  expect(currentProductionReferences(referenceFixture(authority)).size).toBe(0);
});

it("requires current production authority and the exact active selection", () => {
  const refs = referenceFixture("story_bible");
  expect(currentProductionReferences(refs).get("C01")?.id).toBe("selected");
  refs.states[0].current = false;
  expect(currentProductionReferences(refs).size).toBe(0);
  refs.states[0].current = true;
  refs.states[0].activeDecisionId = "superseded";
  expect(currentProductionReferences(refs).size).toBe(0);
  refs.states[0].activeDecisionId = "selected";
  refs.decisions[0].current = false;
  expect(currentProductionReferences(refs).size).toBe(0);
});
