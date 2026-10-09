import type { SamePersonComparison } from "../../../types";

/** Review evidence belongs to the reviewer, never to a prefilled assertion. */
export function newSamePersonComparisons(
  identities: readonly { characterId: string }[],
): SamePersonComparison[] {
  return identities.map(({ characterId }) => ({
    characterId,
    judgment: "pass",
    identityNotes: "",
    stateNotes: "",
  }));
}
