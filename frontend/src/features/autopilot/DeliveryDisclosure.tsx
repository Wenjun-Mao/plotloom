import { plotloomApi } from "../../api";
import type { DeliveryEvidence, Disclosure } from "./deliveryEvidence";

export function DeliveryDisclosure({ projectId, value }: { projectId: string; value: Disclosure }) {
  if (value.status === "unknown") return <p role="note">交付局限尚待核实：{value.message}</p>;
  if (value.status === "unlinked") return <p role="note">未关联生成交付声明；不能据此判断有无生成局限。来源声明：{value.asset.provenance?.origin}</p>;
  if (value.status === "geometry") return <section className="autopilot-delivery-disclosure" aria-label="确定性几何处理说明">
    <strong>当前所选几何处理图 · {value.asset.width}×{value.asset.height}</strong>
    <p>保留原图后，按冻结目标居中裁剪并缩放；这不是新的图像生成，不代表构图改善或人物身份通过。</p>
    <details><summary>查看裁剪与来源身份</summary><p>EXIF 方向：{value.geometry.recipe.exifOrientation} · 居中裁剪框：{value.geometry.recipe.cropBox.join(", ")}</p>
      <p>处理配方：{value.geometry.recipe.version} · <code>{value.geometry.recipeHash}</code></p>
      <p>处理记录：<code>{value.geometry.preparationId}</code> · <code>{value.geometry.preparationHash}</code></p>
      <p>来源任务：<code>{value.geometry.source.jobId}</code> · 来源候选：<code>{value.geometry.source.candidateId}</code></p>
      <p>当前图片 SHA-256：<code>{value.asset.originalHash}</code></p>
    </details>
    <Evidence projectId={projectId} value={value.source} label="保留的原始生成输出" original />
  </section>;
  return <section className="autopilot-delivery-disclosure" aria-label="图片原始交付说明">
    <Evidence projectId={projectId} value={value.current} label="当前所选输出" />
    {value.history.map((entry, index) => entry.evidence ? <Evidence key={entry.asset.id} projectId={projectId} value={entry.evidence} label={`适配来源原图 ${index + 1}（保留证据）`} original />
      : <div key={entry.asset.id}><strong>适配来源原图（原始交付说明尚待核实） · {entry.asset.width}×{entry.asset.height}</strong>
        <a href={plotloomApi.managedAssetUrl(projectId, entry.asset.id, "original")} target="_blank" rel="noreferrer"><img className="autopilot-evidence-original" src={plotloomApi.managedAssetUrl(projectId, entry.asset.id)} alt="已核实身份的适配来源原图" /></a>
        <p>原始图片 SHA-256：<code>{entry.asset.originalHash}</code></p></div>)}
    {value.history.length > 0 && <p>适配记录只说明来源关系与几何目标，不代表视觉质量改善或人工通过。</p>}
    {value.historyUnknown && <p role="note">适配来源历史尚待核实；未读入的原始局限不会视作不存在。</p>}
  </section>;
}

function Evidence({ projectId, value, label, original = false }: { projectId: string; value: DeliveryEvidence; label: string; original?: boolean }) {
  return <div><strong>{label} · {value.asset.width}×{value.asset.height}</strong>
    {original && <a href={plotloomApi.managedAssetUrl(projectId, value.asset.id, "original")} target="_blank" rel="noreferrer"><img className="autopilot-evidence-original" src={plotloomApi.managedAssetUrl(projectId, value.asset.id)} alt={`${label} · ${value.asset.id}`} /></a>}
    <p>助手声明的交付局限（原文）</p>
    {value.limitations.length ? <ul>{value.limitations.map((item, index) => <li key={index}>{item}</li>)}</ul> : <p>这份已核实交付未声明局限；这不代表质量通过。</p>}
    <details><summary>查看生成信息</summary><p>{value.owner} · <code>{value.jobId}</code> · <code>{value.deliveryId}</code></p>
      <p>原始图片 SHA-256：<code>{value.asset.originalHash}</code></p><p>请求 SHA-256：<code>{value.requestHash}</code></p>
      <p>交付声明 SHA-256：<code>{value.manifestHash}</code></p><p>输出文件：<code>{value.outputFilename}</code></p>
    </details>
  </div>;
}
