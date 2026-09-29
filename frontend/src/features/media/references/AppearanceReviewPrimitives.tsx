import { useEffect, useRef, useState, type ReactNode } from "react";
import { createPortal } from "react-dom";

import { plotloomApi } from "../../../api";
import type { ManagedAsset } from "../../../types";

/** Shared display-only primitives. Domain owners keep their own actions and labels. */
export function ManagedAssetImage({ projectId, subjectId, asset, assetId, alt, unavailableLabel, imageUrl, onZoom }: {
  projectId: string; subjectId: string; asset: ManagedAsset | undefined | null; assetId: string;
  alt: string; unavailableLabel: string; imageUrl?: string; onZoom?: () => void;
}) {
  const identity = `${projectId}:${subjectId}:${assetId}`;
  const [failedIdentity, setFailedIdentity] = useState<string | null>(null);
  if (!asset || failedIdentity === identity) {
    return <div className="reference-missing-asset" data-testid={`reference-image-unavailable-${assetId}`}><strong>{unavailableLabel}</strong><small>保留资产 {assetId.slice(0, 12)} 缺失、HTTP 读取失败或无法解码。</small></div>;
  }
  const image = <img src={imageUrl || plotloomApi.managedAssetUrl(projectId, asset.id)} alt={alt} onError={() => setFailedIdentity(identity)} />;
  return onZoom ? <button type="button" className="appearance-image-trigger" aria-label="放大查看" title="点击图片放大查看" onClick={onZoom}>{image}</button> : image;
}

export function AssetZoomDialog({ open, onClose, label, children }: { open: boolean; onClose: () => void; label: string; children: ReactNode }) {
  const dialog = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    if (!open || !dialog.current) return;
    const element = dialog.current;
    const trigger = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    const previousOverflow = document.body.style.overflow;
    // Native modal semantics keep keyboard focus inside and the workspace inert.
    element.showModal();
    document.body.style.overflow = "hidden";
    return () => {
      element.close();
      document.body.style.overflow = previousOverflow;
      if (trigger?.isConnected) trigger.focus();
    };
  }, [open]);
  if (!open) return null;
  return createPortal(<dialog ref={dialog} className="appearance-dialog" aria-label={label}
    onCancel={event => { event.preventDefault(); onClose(); }}
    onClick={event => { if (event.target === event.currentTarget) onClose(); }}>
    <div><button type="button" className="button quiet appearance-dialog-close" aria-label="关闭" title="关闭（Esc）" onClick={onClose}>×</button>{children}</div>
  </dialog>, document.body);
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
