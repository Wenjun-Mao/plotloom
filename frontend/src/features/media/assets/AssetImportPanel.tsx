import type { ManagedAsset } from "../../../types";
import { Button, Field } from "../../../components";
import { CandidateCard } from "./MediaCandidates";

export function AssetImportPanel({
  projectId,
  assets,
  origin,
  declaredAdditions,
  candidates,
  keptAssetId,
  readOnly,
  busy,
  onOrigin,
  onDeclaredAdditions,
  onImport,
  onChooseCandidate,
  onKeepCandidate,
  onClear,
}: {
  projectId?: string;
  assets: ManagedAsset[];
  origin: string;
  declaredAdditions: string;
  candidates: string[];
  keptAssetId: string;
  readOnly: boolean;
  busy: boolean;
  onOrigin: (value: string) => void;
  onDeclaredAdditions: (value: string) => void;
  onImport: (file: File | undefined) => void;
  onChooseCandidate: (assetId: string) => void;
  onKeepCandidate: (assetId: string) => void;
  onClear: () => void;
}) {
  return (
    <>
      <div className="field-grid two compact">
        <Field label="来源声明">
          <input
            value={origin}
            disabled={readOnly || busy}
            onChange={(event) => onOrigin(event.target.value)}
          />
        </Field>
        <Field label="已知新增内容（每行一项）">
          <input
            value={declaredAdditions}
            disabled={readOnly || busy}
            onChange={(event) => onDeclaredAdditions(event.target.value)}
          />
        </Field>
        <Field label="导入 JPEG / PNG">
          <input
            data-testid="managed-image-upload"
            type="file"
            accept="image/jpeg,image/png"
            disabled={readOnly || busy}
            onChange={(event) => void onImport(event.target.files?.[0])}
          />
        </Field>
      </div>
      <div className="media-candidate-grid" aria-label="候选图像比较">
        {assets.map((asset) => (
          <CandidateCard
            key={asset.id}
            asset={asset}
            projectId={projectId}
            selected={candidates.includes(asset.id)}
            kept={keptAssetId === asset.id}
            onPick={() => onChooseCandidate(asset.id)}
            onKeep={() => onKeepCandidate(asset.id)}
          />
        ))}
        {!assets.length && (
          <small>导入真实 JPEG/PNG 后，在这里比较两个候选。</small>
        )}
      </div>
      <div className="button-row">
        <small>
          {candidates.length === 2
            ? "正在比较两个候选：显式保留一个、都不选，或细化其意图。"
            : "最多选择两个候选进行对比。"}
        </small>
        <Button
          variant="quiet"
          disabled={!candidates.length && !keptAssetId}
          onClick={onClear}
        >
          两者都不选
        </Button>
      </div>
    </>
  );
}
