import { useEffect, useRef, useState } from "react";
import { Button, Field, Spinner } from "../../components";
import { plotloomApi } from "../../api";
import { ScriptContentReview } from "../graph/ScriptContentReview";
import { autopilotApi } from "./api";
import type { AutopilotRun, ReviewMaterial } from "./contracts";
import { bulkHandoff, galleryDraft, galleryFrameReady, type GalleryDraft } from "./bulkMaterialReview";
import { GalleryFrameReview } from "./GalleryFrameReview";
import { deliveryDisclosure } from "./deliveryEvidence";
import { useDeliveryEvidence } from "./useDeliveryEvidence";
import { DeliveryDisclosure } from "./DeliveryDisclosure";

export function MaterialReview({ projectId, readOnly = false, onClose, onAccepted, onUncertain }: { projectId: string; readOnly?: boolean; onClose: () => void; onAccepted: (run: AutopilotRun) => Promise<void>; onUncertain: (message: string) => void }) {
  const dialog = useRef<HTMLDialogElement>(null);
  const [material, setMaterial] = useState<ReviewMaterial | null>(null); const [error, setError] = useState("");
  const [drafts, setDrafts] = useState<GalleryDraft[]>([]); const [notes, setNotes] = useState("");
  const [busy, setBusy] = useState(false); const [retry, setRetry] = useState(0); const [imageEpoch, setImageEpoch] = useState(0);
  const [pixels, setPixels] = useState<Record<string, "ready" | "failed">>({});
  const [imageFailures, setImageFailures] = useState<Record<string, true>>({});
  const command = useRef(false); const active = useRef(true); const identity = useRef(projectId); identity.current = projectId;
  const deliveries = useDeliveryEvidence(projectId, material?.bundleHash);
  const disclosure = (assetId: string, originalHash: string, geometryPreparation?: import("./geometryContracts").GeometryPreparation) => deliveries.state?.status === "ready"
    ? deliveryDisclosure(projectId, { assetId, originalHash, geometryPreparation }, deliveries.state.value)
    : { status: "unknown" as const, message: deliveries.state?.status === "failed" ? "原始交付读取失败；可重试读取。" : "正在读取原始交付说明。" };
  useEffect(() => {
    active.current = true; dialog.current?.showModal(); const abort = new AbortController();
    setMaterial(null); setDrafts([]); setPixels({}); setImageFailures({}); setError(""); setNotes("");
    autopilotApi.review(projectId, abort.signal).then(value => { if (abort.signal.aborted) return;
      if (value.bundle.frames.some(frame => !frame.intentContext)) throw new Error("当前素材缺少已保存意图；请重新读取。");
      setMaterial(value); setDrafts(value.bundle.frames.map(galleryDraft));
    }).catch(failure => { if (!abort.signal.aborted) setError(failure instanceof Error ? failure.message : String(failure)); });
    return () => { active.current = false; abort.abort(); };
  }, [projectId, retry]);
  const imageEvents = (id: string) => ({ onLoad: () => setPixels(value => ({ ...value, [id]: "ready" as const })), onError: () => setPixels(value => ({ ...value, [id]: "failed" as const })) });
  const requiredPixels = material ? [...material.bundle.references.flatMap(item => item.assets.map(asset => asset.assetId)), ...material.bundle.frames.map(frame => frame.assetId)] : [];
  const pixelsReady = requiredPixels.length > 0 && requiredPixels.every(id => pixels[id] === "ready");
  const failedPixels = Object.keys(imageFailures);
  const contextReady = material && material.bundle.references.every(reference => reference.assets.every(asset => disclosure(asset.assetId, asset.originalHash).status !== "unknown")) &&
    material.bundle.frames.every(frame => disclosure(frame.assetId, frame.originalHash, frame.geometryPreparation).status !== "unknown");
  const problems = material?.bundle.frames.filter((_, index) => drafts[index] && !galleryFrameReady(drafts[index])) || [];
  const valid = material && pixelsReady && failedPixels.length === 0 && contextReady && deliveries.state?.status === "ready" && drafts.length === material.bundle.frames.length && problems.length === 0;
  const submit = async () => {
    if (!material || !valid || command.current || readOnly) return;
    command.current = true; setBusy(true); setError(""); const submittedProject = projectId;
    try { const result = await autopilotApi.handoff(projectId, bulkHandoff(material, drafts, notes));
      if (active.current && identity.current === submittedProject) await onAccepted(result);
    } catch (failure) { if (active.current && identity.current === submittedProject) {
      const message = failure instanceof Error ? failure.message : String(failure); setError(message); onUncertain(message);
    } }
    finally { command.current = false; if (active.current && identity.current === submittedProject) setBusy(false); }
  };
  return <dialog ref={dialog} className="autopilot-review-dialog" aria-labelledby="material-review-title"
    onErrorCapture={event => { if (event.target instanceof HTMLImageElement) { const src = event.target.src; setImageFailures(value => ({ ...value, [src]: true })); } }}
    onLoadCapture={event => { if (event.target instanceof HTMLImageElement) { const src = event.target.src; setImageFailures(value => { if (!value[src]) return value; const next = { ...value }; delete next[src]; return next; }); } }}
    onCancel={event => { event.preventDefault(); if (!busy) onClose(); }}>
    <header><div><h2 id="material-review-title">审阅完整素材</h2><p>查看参考图与全部首帧。满意时一次确认整包；有问题可打开该镜头的详情处理。自动准备的素材仍是 AI 初稿。</p></div><Button autoFocus disabled={busy} onClick={onClose}>关闭审阅</Button></header>
    {!material && !error && <Spinner label="读取当前完整素材" />}
    {error && <p role="alert">{error}</p>}
    {!material && error && <Button disabled={busy} onClick={() => setRetry(value => value + 1)}>重新读取当前素材</Button>}
    {material && <><p>{material.bundle.inventory.routeCount} 条完整路线 · {material.bundle.references.length} 项参考（{material.bundle.references.reduce((count, item) => count + item.assets.length, 0)} 张图片） · {material.bundle.frames.length} 个镜头首帧</p>
      {deliveries.state?.status === "failed" && <p role="status">图片交付说明读取失败，已有编辑仍保留。<Button variant="quiet" disabled={busy} onClick={deliveries.retry}>重试读取图片交付说明</Button></p>}
      {failedPixels.length > 0 && <p role="alert">有 {failedPixels.length} 张当前图片或保留原图无法读取，整包确认已暂停。<Button disabled={busy} onClick={() => { setPixels({}); setImageFailures({}); setImageEpoch(value => value + 1); }}>重试读取图片</Button></p>}
      <details><summary>完整故事与全部路线</summary>
        {material.bundle.story.graph.nodes.map(node => <article key={node.id}><h3>{node.title}</h3><p>{node.summary}</p></article>)}
        <ol>{material.bundle.story.routes?.map((route, index) => <li key={index}>{route.map(id => material.bundle.story.graph.nodes.find(node => node.id === id)?.title || id).join(" → ")}</li>)}</ol>
        <ScriptContentReview title="当前完整剧本" script={material.bundle.story.script} binding={material.bundle.story.scriptBinding} />
        <div className="button-row">{material.bundle.story.reports?.map(report => <a key={report.url} href={report.url} target="_blank" rel="noreferrer">阅读原始报告 · {report.name}</a>)}</div>
      </details>
      <h3>角色与美术参考</h3><p>整包确认包含这里的全部主参考与补充视图。角色参考用于身份比较；场景与道具图片作为图库参考。</p>
      <div className="autopilot-gallery">{material.bundle.references.map(reference => <article key={reference.decisionId}>
        <h4>{reference.name} · {reference.assets.length} 张参考</h4>
        <div className="autopilot-reference-set">{reference.assets.map((asset, index) => <figure key={`${asset.assetId}:${imageEpoch}`}>
          <a href={plotloomApi.managedAssetUrl(projectId, asset.assetId, "original")} target="_blank" rel="noreferrer"><img {...imageEvents(asset.assetId)} src={plotloomApi.managedAssetUrl(projectId, asset.assetId)} alt={`${reference.name}${index ? `补充参考 ${index}` : "主参考"}`} /></a>
          <figcaption>{index ? `补充参考 ${index}` : "主参考"}</figcaption>
          <DeliveryDisclosure projectId={projectId} value={disclosure(asset.assetId, asset.originalHash)} />
        </figure>)}</div>
      </article>)}</div>
      <h3>按场景审阅全部首帧</h3><p>确认将认可已保存的画面意图及人物身份与状态。无法判断身份时须单独填写原因并选择是否授权。失败或未解决标记会阻止整包继续。</p>
      {problems.length > 0 && <nav aria-label="待解决镜头"><strong>{problems.length} 个镜头待处理：</strong>{problems.map(frame => <a key={frame.shotId} href={`#review-${frame.shotId}`} onClick={() => { const detail = document.getElementById(`review-${frame.shotId}`)?.querySelector("details"); if (detail) detail.open = true; }}>{frame.title} · {frame.shotId} </a>)}</nav>}
      {Array.from(new Set(material.bundle.frames.map(frame => frame.sceneId))).map(sceneId => <section key={sceneId} aria-label={`场景 ${sceneId}`}>
        <h4>场景 · {material.bundle.frames.find(frame => frame.sceneId === sceneId)?.sceneName}</h4>
        <div className="autopilot-frame-gallery">{material.bundle.frames.map((frame, index) => frame.sceneId === sceneId && <GalleryFrameReview key={`${frame.shotId}:${imageEpoch}`} projectId={projectId} frame={frame} draft={drafts[index]} characters={material.bundle.story.characters} disabled={busy || readOnly}
          imageEvents={imageEvents(frame.assetId)} onChange={next => setDrafts(values => values.map((value, slot) => slot === index ? next : value))}
          disclosure={<DeliveryDisclosure projectId={projectId} value={disclosure(frame.assetId, frame.originalHash, frame.geometryPreparation)} />} />)}</div>
      </section>)}
      <Field label="备注（可选）"><textarea value={notes} disabled={busy || readOnly} onChange={event => setNotes(event.target.value)} /></Field>
      <footer><p>点击即确认以上 {material.bundle.references.length} 项完整参考集与 {material.bundle.frames.length} 个首帧适合已显示的意图，且每位可见人物的身份与状态符合参考；单独授权的无法判断项保持不确定。此操作保存整包人工确认。之后可从工作台打开手动视频制作，设置参数并开始制作。</p>
        {!contextReady && deliveries.state?.status === "ready" && <p role="status">有素材来源说明尚待核实，请重新读取当前素材。<Button disabled={busy} onClick={deliveries.retry}>重新核对素材来源</Button></p>}
        {!pixelsReady && !failedPixels.length && <p role="status">正在核对当前图片是否可读取…</p>}
        <Button variant="primary" busy={busy} disabled={busy || readOnly || !valid} onClick={() => void submit()}>确认全部素材并继续</Button></footer>
    </>}
  </dialog>;
}
