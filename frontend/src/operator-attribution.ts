/** Operator identity is provenance, never a generation or QA permission. */
export type CodexTaskAttribution = { kind: "codex_task"; taskId: string };

function canonicalOperator(value: unknown): value is CodexTaskAttribution {
  if (!value || typeof value !== "object" || Array.isArray(value)) return false;
  const actor = value as Record<string, unknown>;
  return Object.keys(actor).length === 2 && actor.kind === "codex_task" && typeof actor.taskId === "string"
    && /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/.test(actor.taskId);
}

export function sameCodexOperator(actual: unknown, expected: unknown): boolean {
  if (actual === undefined && expected === undefined) return true;
  return canonicalOperator(actual) && canonicalOperator(expected) && actual.taskId === expected.taskId;
}
