import type { ReactNode } from "react";
import { Field } from "../../components";
import { plotloomApi } from "../../api";
import type { GalleryFrame, BulkComparison } from "./contracts";
import { galleryFrameReady, type GalleryDraft } from "./bulkMaterialReview";

export function GalleryFrameReview({ projectId, frame, draft, characters, disabled, onChange, imageEvents, disclosure }: {
  projectId: string; frame: GalleryFrame; draft: GalleryDraft; characters: Record<string, string>; disabled: boolean;
  onChange: (draft: GalleryDraft) => void; imageEvents: { onLoad: () => void; onError: () => void }; disclosure: ReactNode;
}) {
  const patch = (fields: Partial<GalleryDraft>) => onChange({ ...draft, ...fields });
  const comparison = (index: number, fields: Partial<BulkComparison>) => patch({ comparisons: draft.comparisons.map((item, slot) => slot === index ? { ...item, ...fields } : item) });
  return <article className="autopilot-frame" id={`review-${frame.shotId}`}>
    <h5>{frame.title} · {frame.shotId}</h5>
    <small>{frame.origin === "machine_provisional" ? "AI 暂选首帧" : "手动所选首帧"}</small>
    <a href={plotloomApi.managedAssetUrl(projectId, frame.assetId, "original")} target="_blank" rel="noreferrer"><img {...imageEvents} src={plotloomApi.managedAssetUrl(projectId, frame.assetId)} alt={`${frame.shotId}首帧`} /></a>
    <p>{frame.description}</p>
    <p>{galleryFrameReady(draft) ? "随整包确认；尚未批准" : "存在待解决问题"}</p>
    <details><summary>查看意图与处理例外 · {frame.shotId}</summary>
      <p>已保存{frame.intentContext.kind === "reviewed_intent" ? "画面意图" : "分镜方向"}；最终确认将认可此上下文。可在这里有意修改。</p>
      {frame.targetUse && <p>跨镜头使用：来源 {frame.targetUse.source.sourceShotId} → 当前 {frame.targetUse.targetShotId}；原始生成：{frame.targetUse.source.originShotId ?? "导入画面"}。意图与身份审核独立。</p>}
      <Field label={`${frame.shotId} 画面意图`}><textarea disabled={disabled} value={draft.intent.compositionIntent || ""} onChange={event => patch({ intent: { ...draft.intent, sourceEndorsement: undefined, compositionIntent: event.target.value } })} /></Field>
      {!draft.intent.sourceEndorsement && (draft.intent.compositionIntent?.length || 0) > 2000 && <p role="status">编辑后的画面意图最多 2000 字；未修改的已保存原文可直接随整包确认。</p>}
      {draft.intent.identityIntent && <Field label={`${frame.shotId} 身份意图`}><textarea disabled={disabled} value={draft.intent.identityIntent} onChange={event => patch({ intent: { ...draft.intent, identityIntent: event.target.value } })} /></Field>}
      {draft.intent.styleIntent && <Field label={`${frame.shotId} 风格意图`}><textarea disabled={disabled} value={draft.intent.styleIntent} onChange={event => patch({ intent: { ...draft.intent, styleIntent: event.target.value } })} /></Field>}
      <Field label={`${frame.shotId} 意图依据`}><textarea disabled={disabled} value={draft.intent.sourceRefs.join("\n")} onChange={event => patch({ intent: { ...draft.intent, sourceEndorsement: undefined, sourceRefs: event.target.value.split("\n") } })} /></Field>
      <Field label={`${frame.shotId} 画面问题`}><select disabled={disabled} value={draft.compatibility} onChange={event => patch({ compatibility: event.target.value as GalleryDraft["compatibility"] })}><option value="pass">随整包确认适合此意图</option><option value="fail">画面不适合</option><option value="hold">标记待处理</option></select></Field>
      {draft.compatibility !== "pass" && <Field required label={`${frame.shotId} 问题说明`}><textarea disabled={disabled} value={draft.comment} onChange={event => patch({ comment: event.target.value })} /></Field>}
      {!draft.comparisons.length && <p>本镜头无可见角色，不创建身份判断。</p>}
      {draft.comparisons.map((item, index) => <fieldset disabled={disabled} key={item.characterId}><legend>{characters[item.characterId] || item.characterId} · 身份与状态</legend>
        <Field label={`${frame.shotId} ${item.characterId} 身份判断`}><select value={item.judgment} onChange={event => comparison(index, { judgment: event.target.value as BulkComparison["judgment"], productionDecision: undefined, uncertaintyReason: undefined })}><option value="pass">随整包确认身份与状态符合参考</option><option value="fail">身份或状态不符合</option><option value="unassessable">当前画面无法判断身份</option></select></Field>
        {item.judgment === "fail" && <Field required label={`${frame.shotId} ${item.characterId} 问题说明`}><textarea value={item.comment || ""} onChange={event => comparison(index, { comment: event.target.value })} /></Field>}
        {item.judgment === "unassessable" && <><Field required label={`${frame.shotId} ${item.characterId} 不确定原因`}><textarea value={item.uncertaintyReason || ""} onChange={event => comparison(index, { uncertaintyReason: event.target.value })} /></Field>
          <Field required label={`${frame.shotId} ${item.characterId} 制作授权`}><select value={item.productionDecision || ""} onChange={event => comparison(index, { productionDecision: event.target.value ? event.target.value as "hold" | "authorize" : undefined })}><option value="">单独选择</option><option value="hold">暂不授权</option><option value="authorize">接受此次不确定性并授权</option></select></Field></>}
      </fieldset>)}
      <details><summary>保存上下文来源</summary><p>{frame.intentContext.sourceId} · 修订 {frame.intentContext.revision} · {frame.intentContext.contentHash}</p></details>
    </details>
    {disclosure}
  </article>;
}
