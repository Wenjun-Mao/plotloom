import type { ReviewedKeyframe, VisualIntent } from "../../../types";

/** A historical shared ordinary intent is not a shot-specific editing stream. */
export function ownsOrdinaryIntent(
  intent: VisualIntent | undefined,
  shotId: string | undefined,
  bindings: ReviewedKeyframe[],
): boolean {
  return !!intent && !intent.intent.targetUse
    && bindings.some((binding) => binding.shotId === shotId && binding.visualIntentId === intent.id)
    && !bindings.some((binding) => binding.shotId !== shotId && binding.visualIntentId === intent.id);
}
