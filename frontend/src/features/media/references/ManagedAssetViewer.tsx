import { useState } from "react";

import type { ManagedAsset } from "../../../types";
import { AssetZoomDialog, ManagedAssetImage } from "./AppearanceReviewPrimitives";

type ViewerProps = {
  projectId: string;
  subjectId: string;
  asset: ManagedAsset;
  alt: string;
  trigger?: "button" | "image";
};

/** Viewing original framing is local presentation, never a review or selection. */
export function ManagedAssetViewer(props: ViewerProps) {
  // Remount the modal owner when its evidence changes, including same-ID bytes.
  // Merely hiding a stale modal would let it reopen when returning to a Shot.
  return <ScopedViewer key={JSON.stringify([
    props.projectId, props.subjectId, props.asset.id,
    props.asset.originalHash, props.asset.displayHash,
  ])} {...props} />;
}

function ScopedViewer({ projectId, subjectId, asset, alt, trigger = "button" }: ViewerProps) {
  const [open, setOpen] = useState(false);
  const imageProps = {
    projectId, subjectId, asset, assetId: asset.id, alt,
    unavailableLabel: "无法读取完整图片",
  };
  return <>
    {trigger === "image"
      ? <ManagedAssetImage {...imageProps} onZoom={() => setOpen(true)} />
      : <button type="button" className="button quiet" onClick={() => setOpen(true)}
          data-testid={`view-asset-${asset.id}`} aria-label={`查看完整图片 · ${alt}`}>
          查看完整图片
        </button>}
    <AssetZoomDialog open={open} onClose={() => setOpen(false)} label={`完整图片 · ${alt}`}>
      <strong>{alt}</strong>
      <ManagedAssetImage {...imageProps} />
      <small>{asset.width}×{asset.height} · {asset.id.slice(0, 12)}。仅查看，不改变候选、关键帧或审核决定。</small>
    </AssetZoomDialog>
  </>;
}
