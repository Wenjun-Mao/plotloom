import type { ContentLanguageStatus } from "../src/features/content-language/contracts";
export const languagePass = (candidateJobId = "candidate"): ContentLanguageStatus => ({ candidateJobId, checkJobId: "check-original",
  candidateHash: "a".repeat(64), bindingHash: "b".repeat(64), state: "completed", verdict: "pass", blocker: null, coverage: [], findings: [], issues: [] });

export const languageRequired = (candidateJobId = "candidate"): ContentLanguageStatus => ({ candidateJobId, checkJobId: null, state: "required", verdict: null, blocker: null });
