import { useState, type ReactNode } from "react";

import { plotloomApi } from "../../../api";
import { Button } from "../../../components";
import type { ManagedAsset } from "../../../types";

/** Shared display-only primitives. Domain owners keep their own actions and labels. */
export function ManagedAssetImage({ projectId, subjectId, asset, assetId, alt, unavailableLabel, imageUrl }: {
  projectId: string; subjectId: string; asset: ManagedAsset | undefined | null; assetId: string;
  alt: string; unavailableLabel: string; imageUrl?: string;
}) {
  const identity = `${projectId}:${subjectId}:${assetId}`;
  const [failedIdentity, setFailedIdentity] = useState<string | null>(null);
  if (!asset || failedIdentity === identity) {
    return <div className="reference-missing-asset" data-testid={`reference-image-unavailable-${assetId}`}><strong>{unavailableLabel}</strong><small>保留资产 {assetId.slice(0, 12)} 缺失、HTTP 读取失败或无法解码。</small></div>;
  }
  return <img src={imageUrl || plotloomApi.managedAssetUrl(projectId, asset.id)} alt={alt} onError={() => setFailedIdentity(identity)} />;
}

export function AssetZoomDialog({ open, onClose, label, children }: { open: boolean; onClose: () => void; label: string; children: ReactNode }) {
  if (!open) return null;
  return <div className="appearance-dialog" role="dialog" aria-modal="true" aria-label={label}><div><Button variant="quiet" onClick={onClose}>关闭</Button>{children}</div></div>;
}

/** A review set is deliberately local and bounded; it never expresses selection. */
export function useBoundedAssetComparison<T extends { assetId: string }>(candidates: T[]) {
  const [assetIds, setAssetIds] = useState<string[]>([]);
  const comparisonCandidates = assetIds.flatMap((assetId) => {
    const candidate = candidates.find((item) => item.assetId === assetId);
    return candidate ? [candidate] : [];
  });
  const atCapacity = comparisonCandidates.length >= 4;
  const toggle = (assetId: string) => setAssetIds((current) => current.includes(assetId)
    ? current.filter((item) => item !== assetId)
    : current.length < 4 ? [...current, assetId] : current);
  return { comparisonCandidates, comparisonAssetIds: assetIds, comparisonAtCapacity: atCapacity, toggleComparison: toggle, clearComparison: () => setAssetIds([]) };
}
