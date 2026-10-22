import type { ManagedAsset } from "../../../types";

/** Display persisted declarations only; rights status is not creator approval. */
export function ManagedAssetProvenanceFields({ provenance }: { provenance: ManagedAsset["provenance"] | undefined }) {
  return <>
    <div><dt>来源</dt><dd>{provenance?.origin || "来源信息不可用"}</dd></div>
    <div><dt>权利</dt><dd>{provenance?.rights ?? "权利信息不可用"}</dd></div>
    {provenance?.rightsNote && <div><dt>权利说明</dt><dd>{provenance.rightsNote}</dd></div>}
  </>;
}
