import { useEffect, useRef, useState } from "react";
import { Button, Field, Spinner } from "../../components";
import { plotloomApi } from "../../api";
import { ScriptContentReview } from "../graph/ScriptContentReview";
import type { SamePersonComparison, SamePersonComparisonDraft } from "../../same-person-review-types";
import { autopilotApi } from "./api";
import { completeFrame, type AutopilotRun, type FrameDraft, type ReviewFrame, type ReviewMaterial } from "./contracts";
import { deliveryDisclosure } from "./deliveryEvidence";
import { useDeliveryEvidence } from "./useDeliveryEvidence";
import { DeliveryDisclosure } from "./DeliveryDisclosure";

export function MaterialReview({ projectId, readOnly = false, onClose, onAccepted, onUncertain }: { projectId: string; readOnly?: boolean; onClose: () => void; onAccepted: (run: AutopilotRun) => Promise<void>; onUncertain: (message: string) => void }) {
  const dialog = useRef<HTMLDialogElement>(null);
  const [material, setMaterial] = useState<ReviewMaterial | null>(null); const [error, setError] = useState("");
  const [drafts, setDrafts] = useState<FrameDraft[]>([]); const [endorsed, setEndorsed] = useState<string[]>([]);
  const [notes, setNotes] = useState(""); const [busy, setBusy] = useState(false);
  const command = useRef(false); const active = useRef(true);
  const deliveries = useDeliveryEvidence(projectId, material?.bundleHash);
  const disclosure = (assetId: string, originalHash: string, geometryPreparation?: import("./geometryContracts").GeometryPreparation) => deliveries.state?.status === "ready"
    ? deliveryDisclosure(projectId, { assetId, originalHash, geometryPreparation }, deliveries.state.value)
    : { status: "unknown" as const, message: deliveries.state?.status === "failed" ? "原始交付读取失败；可重试读取。" : "正在读取原始交付说明。" };
  useEffect(() => { active.current = true; dialog.current?.showModal(); const abort = new AbortController();
    autopilotApi.review(projectId, abort.signal).then(value => { if (abort.signal.aborted) return; setMaterial(value);
      setDrafts(value.bundle.frames.map(frame => ({ direction: "", sources: "", compatibility: "", comparisons: frame.characterIds.map(characterId => ({ characterId, judgment: "", identityNotes: "", stateNotes: "" })) })));
    }).catch(failure => { if (!abort.signal.aborted) setError(failure instanceof Error ? failure.message : String(failure)); });
    return () => { active.current = false; abort.abort(); };
  }, [projectId]);
  const valid = material && material.bundle.references.every(item => endorsed.includes(item.decisionId)) && drafts.length === material.bundle.frames.length && drafts.every(completeFrame);
  const submit = async () => {
    if (!material || !valid || command.current || readOnly) return;
    command.current = true;
    setBusy(true); setError("");
    try { const result = await autopilotApi.handoff(projectId, { expectedRunRevision: material.runRevision, bundleHash: material.bundleHash, ...(notes.trim() ? { notes } : {}), endorsedReferenceIds: endorsed,
      frames: material.bundle.frames.map((frame, index) => ({ shotId: frame.shotId, assetId: frame.assetId,
        intent: { role: "shot_keyframe", compositionIntent: drafts[index].direction.trim(), sourceRefs: drafts[index].sources.split(/\n/).map(value => value.trim()).filter(Boolean) },
        compatibilityNote: drafts[index].compatibility.trim(), comparisons: drafts[index].comparisons as SamePersonComparison[] })) });
      if (active.current) await onAccepted(result);
    } catch (failure) { if (active.current) {
      const message = failure instanceof Error ? failure.message : String(failure);
      setError(message); onUncertain(message);
    } }
    finally { command.current = false; if (active.current) setBusy(false); }
  };
  return <dialog ref={dialog} className="autopilot-review-dialog" aria-labelledby="material-review-title" onCancel={event => { event.preventDefault(); if (!busy) onClose(); }}>
    <header><div><h2 id="material-review-title">审阅完整素材</h2><p>看看当前故事、参考图和每个镜头首帧，填写你实际看到的情况。自动准备的素材仍是 AI 初稿。</p></div><Button disabled={busy} onClick={onClose}>关闭审阅</Button></header>
    {!material && !error && <Spinner label="读取当前完整素材" />}
    {error && <p role="alert">{error}</p>}
    {material && <><p>{material.bundle.inventory.routeCount} 条完整路线 · {material.bundle.references.length} 项参考（{material.bundle.references.reduce((count, item) => count + item.assets.length, 0)} 张图片） · {material.bundle.frames.length} 个镜头首帧</p>
      {deliveries.state?.status === "failed" && <p role="status">图片交付说明读取失败，已填写观察仍保留。<Button variant="quiet" disabled={busy} onClick={deliveries.retry}>重试读取图片交付说明</Button></p>}
      <details><summary>完整故事与全部路线</summary>
        {material.bundle.story.graph.nodes.map(node => <article key={node.id}><h3>{node.title}</h3><p>{node.summary}</p></article>)}
        <ol>{material.bundle.story.routes?.map((route, index) => <li key={index}>{route.map(id => material.bundle.story.graph.nodes.find(node => node.id === id)?.title || id).join(" → ")}</li>)}</ol>
        <ScriptContentReview title="当前完整剧本" script={material.bundle.story.script} binding={material.bundle.story.scriptBinding} />
        <div className="button-row">{material.bundle.story.reports?.map(report => <a key={report.url} href={report.url} target="_blank" rel="noreferrer">阅读原始报告 · {report.name}</a>)}</div>
      </details>
      <h3>角色与美术参考</h3><p>角色参考用于首帧人物身份条件；场景与道具图片在本版本作为图库参考，镜头任务采用其文字方向。</p>
      <div className="autopilot-gallery">{material.bundle.references.map(reference => <article key={reference.decisionId}>
        <h4>{reference.name} · {reference.assets.length} 张参考</h4>
        <div className="autopilot-reference-set">{reference.assets.map((asset, index) => <figure key={asset.assetId}>
          <a href={plotloomApi.managedAssetUrl(projectId, asset.assetId, "original")} target="_blank" rel="noreferrer"><img loading="lazy" src={plotloomApi.managedAssetUrl(projectId, asset.assetId)} alt={`${reference.name}${index ? `补充参考 ${index}` : "主参考"}`} /></a>
          <figcaption>{index ? `补充参考 ${index}` : "主参考"}</figcaption>
          <DeliveryDisclosure projectId={projectId} value={disclosure(asset.assetId, asset.originalHash)} />
        </figure>)}</div>
        <label><input type="checkbox" disabled={busy || readOnly} checked={endorsed.includes(reference.decisionId)} onChange={event => setEndorsed(value => event.target.checked ? [...value, reference.decisionId] : value.filter(id => id !== reference.decisionId))} />我看过了，确认使用这些参考图 · {reference.name}</label>
      </article>)}</div>
      <h3>按场景审阅全部首帧</h3><p>人物不可辨认时，请记录原因并单独选择是否授权。失败或保留意见会阻止进入视频制作；无人镜头不需要身份通过记录。</p>
      {material.bundle.frames.map((frame, index) => <div key={frame.shotId}>
        {(index === 0 || material.bundle.frames[index - 1].sceneId !== frame.sceneId) && <h4>场景 · {frame.sceneName}</h4>}
        <FrameReview projectId={projectId} frame={frame} draft={drafts[index]} characters={material.bundle.story.characters} disabled={busy || readOnly} onChange={next => setDrafts(values => values.map((value, slot) => slot === index ? next : value))} />
        <DeliveryDisclosure projectId={projectId} value={disclosure(frame.assetId, frame.originalHash, frame.geometryPreparation)} />
      </div>)}
      <Field label="备注（可选）"><textarea value={notes} disabled={busy || readOnly} onChange={event => setNotes(event.target.value)} /></Field>
      <footer><p>确认后会保存你的素材选择。之后可从工作台打开手动视频制作，设置参数并开始制作。</p><Button variant="primary" busy={busy} disabled={busy || readOnly || !valid} onClick={() => void submit()}>确认使用这些素材</Button></footer>
    </>}
  </dialog>;
}

function FrameReview({ projectId, frame, draft, characters, disabled, onChange }: { projectId: string; frame: ReviewFrame; draft: FrameDraft; characters: Record<string, string>; disabled: boolean; onChange: (value: FrameDraft) => void }) {
  const patch = (fields: Partial<FrameDraft>) => onChange({ ...draft, ...fields });
  const comparison = (index: number, fields: Partial<SamePersonComparisonDraft>) => patch({ comparisons: draft.comparisons.map((item, slot) => slot === index ? { ...item, ...fields } : item) });
  return <details className="autopilot-frame" open={!completeFrame(draft)}><summary>{frame.title} · {frame.shotId} · {completeFrame(draft) ? "观察已填写" : "等待实际观察"}</summary>
    <div className="autopilot-frame-layout"><div><small>{frame.origin === "machine_provisional" ? "AI 暂选首帧" : "手动所选首帧"}</small>{frame.targetUse && <small>跨镜头使用：来源 {frame.targetUse.source.sourceShotId} → 当前 {frame.targetUse.targetShotId}；原始生成：{frame.targetUse.source.originShotId ?? "导入画面"}。意图与身份审核独立。</small>}<a href={plotloomApi.managedAssetUrl(projectId, frame.assetId, "original")} target="_blank" rel="noreferrer"><img loading="lazy" src={plotloomApi.managedAssetUrl(projectId, frame.assetId)} alt={`${frame.shotId}首帧`} /></a><p>{frame.description}</p><p>当前分镜画面方向：{frame.direction}</p></div>
      <div><Field required label={`${frame.shotId} 画面意图`}><textarea value={draft.direction} disabled={disabled} onChange={event => patch({ direction: event.target.value })} /></Field>
        <Field required label={`${frame.shotId} 意图依据`} hint="填写实际参考的剧本、镜头或方向；每行一项。"><textarea value={draft.sources} disabled={disabled} onChange={event => patch({ sources: event.target.value })} /></Field>
        <Field required label={`${frame.shotId} 镜头兼容性观察`}><textarea value={draft.compatibility} disabled={disabled} onChange={event => patch({ compatibility: event.target.value })} /></Field>
        {!draft.comparisons.length && <p>本镜头无可见角色，无需身份判定。</p>}
        {draft.comparisons.map((item, index) => <fieldset key={item.characterId} disabled={disabled}><legend>{characters[item.characterId] || item.characterId} · 本帧实际观察</legend>
          <Field required label={`${frame.shotId} ${item.characterId} 身份判断`}><select value={item.judgment} onChange={event => comparison(index, { judgment: event.target.value as SamePersonComparisonDraft["judgment"], productionDecision: undefined, uncertaintyReason: undefined })}><option value="">请选择</option><option value="pass">符合参考身份</option><option value="fail">身份不符合</option><option value="unassessable">当前画面无法判断</option></select></Field>
          <Field required label={`${frame.shotId} ${item.characterId} 身份观察`}><textarea value={item.identityNotes} onChange={event => comparison(index, { identityNotes: event.target.value })} /></Field>
          <Field required label={`${frame.shotId} ${item.characterId} 状态观察`}><textarea value={item.stateNotes} onChange={event => comparison(index, { stateNotes: event.target.value })} /></Field>
          {item.judgment === "unassessable" && <><Field required label={`${frame.shotId} ${item.characterId} 不确定原因`}><textarea value={item.uncertaintyReason || ""} onChange={event => comparison(index, { uncertaintyReason: event.target.value })} /></Field>
            <Field required label={`${frame.shotId} ${item.characterId} 制作授权`}><select value={item.productionDecision || ""} onChange={event => comparison(index, { productionDecision: event.target.value as SamePersonComparisonDraft["productionDecision"] })}><option value="">单独选择</option><option value="hold">暂不授权</option><option value="authorize">接受此次不确定性并授权</option></select></Field></>}
        </fieldset>)}
      </div>
    </div>
  </details>;
}
