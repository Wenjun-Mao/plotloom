import type { ManagedAsset } from "../../../types";
import { plotloomApi } from "../../../api";
import { Button } from "../../../components";

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
            alt={`Imported candidate ${asset.id}`}
          />
        )}
        <strong>
          {asset.width}×{asset.height} · {Math.ceil(asset.byteSize / 1024)} KB
        </strong>
        <small>{asset.provenance?.origin || "来源未知"}</small>
        {asset.provenance?.declaredAdditions.length ? (
          <small>已知新增：{asset.provenance.declaredAdditions.join("、")}</small>
        ) : null}
      </button>
      <Button
        data-testid={`keep-candidate-${asset.id}`}
        variant={kept ? "primary" : "quiet"}
        onClick={onKeep}
      >
        {kept ? "已保留" : "保留此候选"}
      </Button>
    </article>
  );
}
