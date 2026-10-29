export type ContentLanguageStage = "outline" | "branches" | "characters" | "art" | "script" | "storyboard" | "bridge-intent" | "bridge-presentation";
export type ContentLanguageStatus = {
  candidateJobId: string; checkJobId: string | null; candidateHash?: string; bindingHash?: string;
  state: "required" | "spawn_intent" | "queued" | "running" | "validating" | "outcome_unknown" | "cancel_requested" | "completed" | "failed" | "settled";
  retry?: import("../generation-retry/contracts").GenerationRetryStatus;
  verdict: "pass" | "reject" | "uncertain" | null; blocker: string | null;
  coverage?: { path: string; sha256: string; role: "authored_prose" | "exact_source" | "provider_technical" | "stable_identity";
    verdict: "pass" | "reject" | "uncertain" | "not_applicable"; exceptions: unknown[] }[];
  findings?: { code: string; span: { path: string; start: number; end: number; text: string }; explanation: string }[];
  issues?: { code: "content_language_mismatch"; fieldPaths: string[]; repairFacts: { contentLocale: "zh-CN" | "en-US" } }[];
};
export const languageCheckPending = (status?: ContentLanguageStatus | null) => !!status && ["spawn_intent", "queued", "running", "validating", "outcome_unknown", "cancel_requested"].includes(status.state);
export const languageCheckPassed = (status?: ContentLanguageStatus | null) => !!status && status.state === "completed" && status.verdict === "pass"
  && !!status.checkJobId && /^[a-f0-9]{64}$/.test(status.candidateHash || "") && /^[a-f0-9]{64}$/.test(status.bindingHash || "") && !status.findings?.length;
/** Local response ownership only; trusted server hashes remain authoritative. */
export function candidateIdentity(value: unknown): string {
  return JSON.stringify(value, (_key, item) => item && typeof item === "object" && !Array.isArray(item)
    ? Object.fromEntries(Object.entries(item).filter(([, value]) => value !== undefined).sort(([a], [b]) => a.localeCompare(b))) : item) ?? "";
}

/** A stable logical anchor must never be rolled back to an earlier physical child. */
export function olderLanguageObservation(previous: ContentLanguageStatus | undefined, next: ContentLanguageStatus): boolean {
  if (!previous || previous.checkJobId !== next.checkJobId) return false;
  const before = previous.retry?.retryCount ?? 0, after = next.retry?.retryCount ?? 0;
  return before > after || before === after && previous.state === "completed" && next.state !== "completed";
}
