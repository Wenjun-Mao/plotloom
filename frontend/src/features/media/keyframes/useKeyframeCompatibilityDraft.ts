import { useEffect, useState, type Dispatch, type SetStateAction } from "react";
import type { ApprovalDecision, ManagedAsset, Shot, VisualIntent } from "../../../types";
import type { MediaReadPhase } from "../useMediaWorkbenchData";

/** Reviewer observations belong to one candidate and approved source, not the panel. */
export function useKeyframeCompatibilityDraft({
  projectId, shot, assetId, approval, storyboardRevision, intent, asset, mediaReadPhase,
}: {
  projectId?: string;
  shot?: Shot;
  assetId: string;
  approval?: ApprovalDecision;
  storyboardRevision?: number;
  intent?: VisualIntent;
  asset?: ManagedAsset;
  mediaReadPhase: MediaReadPhase;
}) {
  const scopeKey = JSON.stringify([
    projectId, shot?.id, shot?.sceneId, assetId,
    approval?.id, approval?.subjectRevision, storyboardRevision,
  ]);
  // Snapshot withdrawal is unknown, not evidence that the source changed.
  const basisKey = mediaReadPhase === "ready"
    ? JSON.stringify([intent?.id, intent?.revision, asset?.originalHash, asset?.displayHash])
    : undefined;
  const [draft, setDraft] = useState({ scopeKey, basisKey, value: "" });
  const matches = draft.scopeKey === scopeKey
    && (basisKey === undefined || draft.basisKey === basisKey);
  // Never render or submit the previous target's note, even before effects run.
  const compatibility = matches ? draft.value : "";

  useEffect(() => {
    setDraft((current) => {
      if (current.scopeKey === scopeKey
        && (basisKey === undefined || current.basisKey === basisKey)) return current;
      return { scopeKey, basisKey, value: "" };
    });
  }, [scopeKey, basisKey]);

  const setCompatibility: Dispatch<SetStateAction<string>> = (next) => {
    setDraft((current) => {
      const sameScope = current.scopeKey === scopeKey;
      const currentValue = sameScope
        && (basisKey === undefined || current.basisKey === basisKey) ? current.value : "";
      return {
        scopeKey,
        basisKey: basisKey ?? (sameScope ? current.basisKey : undefined),
        value: typeof next === "function" ? next(currentValue) : next,
      };
    });
  };
  return { compatibility, setCompatibility };
}
