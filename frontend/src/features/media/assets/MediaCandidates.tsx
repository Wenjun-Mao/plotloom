import type { ManagedAsset } from "../../../types";
import { plotloomApi } from "../../../api";
import { Button } from "../../../components";
import { ManagedAssetProvenanceFields } from "./ManagedAssetProvenanceFields";

export function CandidateCard({
  asset,
  projectId,
  selected,
  kept,
  onPick,
  onKeep,
}: {
  asset: ManagedAsset;
  projectId?: string;
  selected: boolean;
  kept: boolean;
  onPick: () => void;
  onKeep: () => void;
}) {
  return (
    <article className={`media-candidate ${selected ? "selected" : ""}`}>
      <button onClick={onPick} aria-pressed={selected}>
        {projectId && (
          <img
            src={plotloomApi.managedAssetUrl(projectId, asset.id)}
            alt={`候选图片 ${asset.id}`}
          />
        )}
        <strong>
          {asset.width}×{asset.height} · {Math.ceil(asset.byteSize / 1024)} KB
        </strong>
        <small>{asset.provenance?.origin || "来源信息不可用"}</small>
        {asset.provenance?.declaredAdditions.length ? (
          <small>已知新增：{asset.provenance.declaredAdditions.join("、")}</small>
        ) : null}
      </button>
      <details className="reference-technical">
        <summary>查看候选来源与技术详情</summary>
        <dl><div><dt>资产</dt><dd>{asset.id}</dd></div><ManagedAssetProvenanceFields provenance={asset.provenance} /></dl>
      </details>
      <Button
        data-testid={`keep-candidate-${asset.id}`}
        variant="quiet"
        aria-pressed={kept}
        className="selection-toggle"
        onClick={onKeep}
      >
        {kept ? "当前待审关键帧候选" : "用此图审阅关键帧"}
      </Button>
    </article>
  );
}
