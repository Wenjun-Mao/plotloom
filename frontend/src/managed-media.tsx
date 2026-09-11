import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { ApprovalDecision, ManagedAsset, Shot, StillPreview, Storyboard, StoryboardReview, VisualIntent, VisualWorkbench } from "./types";
import { plotloomApi } from "./api";
import { Badge, Button, Field, Panel } from "./components";
import { useVisualIntentDraft, type IntentDraft } from "./visual-intent-drafts";

function previewKey(projectId: string): string { return `plotloom:still-preview:${projectId}`; }
function stateTone(state: StillPreview["state"]): "ok" | "warning" | "danger" { return state === "current" ? "ok" : state === "stale" ? "warning" : "danger"; }
function stateGuidance(state: StillPreview["state"]): string | null {
  if (state === "stale") return "冻结历史仍可检查；当前选择或意图已变化，重新审核后创建新的预览。";
  if (state === "revoked") return "冻结历史仍可检查；先恢复当前 storyboard Approval，才能创建新的预览。";
  if (state === "missing") return "冻结历史引用的存储字节不可读取；不要把它当作可用关键帧。";
  if (state === "corrupt") return "冻结历史的完整性校验失败；停止使用并调查存储或 receipt。";
  return null;
}
const emptyWorkbench: VisualWorkbench = { assets: [], selectionRevision: 0, visualIntents: [], reviewedKeyframes: [], previews: [] };

function draftFor(intent: VisualIntent | undefined, shot: Shot | undefined): IntentDraft {
  return {
    identityIntent: intent?.intent.identityIntent ?? "",
    compositionIntent: intent?.intent.compositionIntent ?? shot?.composition ?? "",
    styleIntent: intent?.intent.styleIntent ?? shot?.visualIntent ?? "",
    sourceRefs: intent?.intent.sourceRefs.join("\n") ?? "",
  };
}

export function ManagedMediaWorkbench({ projectId, storyboard, selectedShot, storyboardRevision, review, readOnly, onSelectShot, onReview }: {
  projectId?: string; storyboard: Storyboard; selectedShot: Shot | undefined; storyboardRevision?: number; review: StoryboardReview | null | undefined; readOnly: boolean;
  onSelectShot?: (id: string) => void; onReview?: () => void;
}) {
  const [workbench, setWorkbench] = useState<VisualWorkbench>(emptyWorkbench);
  const [candidates, setCandidates] = useState<string[]>([]);
  const [keptAssetId, setKeptAssetId] = useState("");
  const [origin, setOrigin] = useState("Local creator import");
  const [declaredAdditions, setDeclaredAdditions] = useState("reference only");
  const [compatibility, setCompatibility] = useState("");
  const [previewLength, setPreviewLength] = useState(3);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [previewId, setPreviewId] = useState("");
  const [playing, setPlaying] = useState(false);
  const [frameIndex, setFrameIndex] = useState(0);
  const requestSequence = useRef(0);
  const priorProjectId = useRef(projectId);
  const currentApproval: ApprovalDecision | undefined = review?.activeApproval ?? undefined;

  const refresh = useCallback(async (signal?: AbortSignal) => {
    if (!projectId) return;
    const sequence = ++requestSequence.current;
    const next = await plotloomApi.getVisualWorkbench(projectId, signal);
    if (signal?.aborted || sequence !== requestSequence.current) return;
    setWorkbench(next);
    const saved = window.localStorage.getItem(previewKey(projectId));
    const preferred = next.previews.find((item) => item.id === saved) ?? next.previews[0];
    setPreviewId(preferred?.id ?? "");
  }, [projectId]);

  // Approval and authored-board changes determine preview applicability.  An
  // aborted or superseded request may never repaint a newer approval context.
  useEffect(() => {
    const controller = new AbortController();
    void refresh(controller.signal).catch((loadError) => {
      if (!controller.signal.aborted) setError(loadError instanceof Error ? loadError.message : "无法读取导入媒体");
    });
    return () => controller.abort();
  }, [refresh, currentApproval?.id, currentApproval?.subjectRevision, storyboardRevision, selectedShot?.id]);

  const sceneShots = useMemo(() => selectedShot ? storyboard.shots.filter((shot) => shot.sceneId === selectedShot.sceneId).sort((left, right) => left.order - right.order) : [], [storyboard, selectedShot]);
  const previewStart = selectedShot ? sceneShots.findIndex((shot) => shot.id === selectedShot.id) : -1;
  const maxPreviewLength = previewStart < 0 ? 0 : sceneShots.length - previewStart;
  const previewShotIds = useMemo(() => previewStart < 0 ? [] : sceneShots.slice(previewStart, previewStart + Math.min(previewLength, maxPreviewLength)).map((shot) => shot.id), [maxPreviewLength, previewLength, previewStart, sceneShots]);
  const preview = workbench.previews.find((item) => item.id === previewId);
  const reviewedShotIds = useMemo(() => new Set(workbench.reviewedKeyframes.map((binding) => binding.shotId)), [workbench.reviewedKeyframes]);
  const missingPreviewShotIds = previewShotIds.filter((shotId) => !reviewedShotIds.has(shotId));
  const selectedBinding = selectedShot ? workbench.reviewedKeyframes.find((binding) => binding.shotId === selectedShot.id) : undefined;
  const activeIntent = workbench.visualIntents.find((intent) => intent.assetId === keptAssetId && intent.intent.role === "shot_keyframe");
  const intentEditor = useVisualIntentDraft(projectId, selectedShot?.id, keptAssetId, activeIntent?.id, draftFor(activeIntent, selectedShot));
  const intentDraft = intentEditor.value;
  const setIntentDraft = intentEditor.update;

  useEffect(() => { setPreviewLength((current) => Math.max(1, Math.min(current, maxPreviewLength || 1))); }, [maxPreviewLength]);
  // A reviewed binding is durable per Shot. Restore it after a reload or a
  // parent review refresh rather than making the creator rediscover which
  // candidate and intent revision were already selected.
  useEffect(() => {
    const changedProject = priorProjectId.current !== projectId;
    priorProjectId.current = projectId;
    if (selectedBinding) setKeptAssetId(selectedBinding.assetId);
    else if (changedProject) setKeptAssetId("");
  }, [projectId, selectedBinding?.id]);
  useEffect(() => {
    if (!playing || !preview) return;
    const frame = preview.manifest.frames[frameIndex];
    if (!frame) return;
    // Frozen duration is the playback contract; do not add a UI timing floor.
    const timer = window.setTimeout(() => setFrameIndex((current) => (current + 1) % preview.manifest.frames.length), frame.durationMs);
    return () => window.clearTimeout(timer);
  }, [playing, preview, frameIndex]);

  const chooseCandidate = (id: string) => setCandidates((current) => current.includes(id) ? current.filter((candidate) => candidate !== id) : [...current.slice(-1), id]);
  const keepCandidate = (id: string) => { setKeptAssetId(id); setCandidates((current) => current.includes(id) ? current : [...current.slice(-1), id]); };
  const selectPreview = (id: string) => { setPreviewId(id); setFrameIndex(0); setPlaying(false); if (projectId) window.localStorage.setItem(previewKey(projectId), id); };
  const importFile = async (file: File | undefined) => {
    if (!projectId || !file) return;
    setBusy(true); setError("");
    try {
      await plotloomApi.importManagedAsset(projectId, file, { origin, rights: "unknown", declaredAdditions: declaredAdditions.split("\n").map((item) => item.trim()).filter(Boolean) });
      await refresh();
    } catch (importError) { setError(importError instanceof Error ? importError.message : "导入失败"); }
    finally { setBusy(false); }
  };
  const saveIntent = async () => {
    if (!projectId || !keptAssetId) return;
    if (intentEditor.stale) { setError("已保存意图已有新版本；草稿仍保留，请先检查并重新载入。"); return; }
    const sourceRefs = intentDraft.sourceRefs.split("\n").map((item) => item.trim()).filter(Boolean);
    if (!sourceRefs.length) { setError("先记录至少一个来源引用，再保存可审核意图。"); return; }
    setBusy(true); setError("");
    try {
      await plotloomApi.createVisualIntent(projectId, keptAssetId, { role: "shot_keyframe", identityIntent: intentDraft.identityIntent, compositionIntent: intentDraft.compositionIntent, styleIntent: intentDraft.styleIntent, sourceRefs });
      await refresh();
      intentEditor.clear();
    } catch (intentError) { setError(intentError instanceof Error ? intentError.message : "意图保存失败"); }
    finally { setBusy(false); }
  };
  const selectKeyframe = async () => {
    if (!projectId || !keptAssetId || !selectedShot || !currentApproval || !storyboardRevision || !activeIntent) return;
    if (intentEditor.dirty) { setError("先保存或放弃意图草稿，再审核选择。"); return; }
    if (!compatibility.trim()) { setError("请记录此关键帧与已批准镜头的兼容性说明。"); return; }
    setBusy(true); setError("");
    try {
      await plotloomApi.selectReviewedKeyframe(projectId, { assetId: keptAssetId, shotId: selectedShot.id, sceneId: selectedShot.sceneId, expectedSelectionRevision: workbench.selectionRevision, storyboardRevision, approvalId: currentApproval.id, compatibilityNote: compatibility.trim(), visualIntentId: activeIntent.id, visualIntentRevision: activeIntent.revision });
      await refresh();
    } catch (selectionError) { setError(selectionError instanceof Error ? selectionError.message : "选择失败"); }
    finally { setBusy(false); }
  };
  const createPreview = async () => {
    if (!projectId || !selectedShot || !currentApproval || !storyboardRevision || !previewShotIds.length) return;
    if (missingPreviewShotIds.length) { setError(`先为 ${missingPreviewShotIds.join("、")} 完成审核关键帧选择。`); return; }
    setBusy(true); setError("");
    try {
      const created = await plotloomApi.createStillPreview(projectId, { sceneId: selectedShot.sceneId, shotIds: previewShotIds, expectedSelectionRevision: workbench.selectionRevision, storyboardRevision, approvalId: currentApproval.id });
      await refresh(); selectPreview(created.id);
    } catch (previewError) { setError(previewError instanceof Error ? previewError.message : "预览创建失败"); }
    finally { setBusy(false); }
  };

  return <Panel className="managed-media-workbench" data-testid="managed-media-workbench">
    <div className="section-title"><span>Imported stills · P0</span><strong>非生成式审核关键帧</strong></div>
    <p className="muted">原始字节、来源声明、可审核意图和精确批准绑定都会保留；此处不会创建生成任务或视频。</p>
    <div className="button-row">
      <Field label="当前媒体镜头"><select value={selectedShot?.id ?? ""} onChange={(event) => onSelectShot?.(event.target.value)} disabled={!storyboard.shots.length}>
        {!storyboard.shots.length && <option value="">尚无镜头</option>}
        {storyboard.shots.map((shot) => <option key={shot.id} value={shot.id}>{shot.title} · {shot.id}</option>)}
      </select></Field>
      <Button variant="quiet" onClick={onReview}>{currentApproval ? "查看分镜批准" : "前往分镜审核"}</Button>
    </div>
    {selectedShot && <small>当前镜头：{selectedShot.action} · {selectedShot.durationUnits}ms</small>}
    {error && <div className="notice warning" role="alert">{error}</div>}
    <div className="field-grid two compact">
      <Field label="来源声明"><input value={origin} disabled={readOnly || busy} onChange={(event) => setOrigin(event.target.value)} /></Field>
      <Field label="已知新增内容（每行一项）"><input value={declaredAdditions} disabled={readOnly || busy} onChange={(event) => setDeclaredAdditions(event.target.value)} /></Field>
      <Field label="导入 JPEG / PNG"><input data-testid="managed-image-upload" type="file" accept="image/jpeg,image/png" disabled={readOnly || busy} onChange={(event) => void importFile(event.target.files?.[0])} /></Field>
    </div>
    <div className="media-candidate-grid" aria-label="候选图像比较">
      {workbench.assets.map((asset) => <CandidateCard key={asset.id} asset={asset} projectId={projectId} selected={candidates.includes(asset.id)} kept={keptAssetId === asset.id} onPick={() => chooseCandidate(asset.id)} onKeep={() => keepCandidate(asset.id)} />)}
      {!workbench.assets.length && <small>导入真实 JPEG/PNG 后，在这里比较两个候选。</small>}
    </div>
    <div className="button-row"><small>{candidates.length === 2 ? "正在比较两个候选：显式保留一个、都不选，或细化其意图。" : "最多选择两个候选进行对比。"}</small><Button variant="quiet" disabled={!candidates.length && !keptAssetId} onClick={() => { setCandidates([]); setKeptAssetId(""); }}>两者都不选</Button></div>
    {selectedBinding && <small data-testid="current-reviewed-keyframe">当前 Shot 已保存资产 {selectedBinding.assetId.slice(0, 8)} · intent r{selectedBinding.visualIntentRevision ?? "—"}</small>}
    {keptAssetId && <section className="intent-editor" aria-label="可审核视觉意图">
      <strong>为保留候选记录可审核意图 · shot_keyframe</strong>
      {intentEditor.dirty && <div className="notice warning" role="status">
        <span>{intentEditor.stale ? "已保存意图已有新版本；草稿未被覆盖。" : "有未保存的意图草稿；切换镜头或候选不会丢失。先保存再审核选择。"}</span>
        <Button variant="quiet" onClick={intentEditor.clear}>放弃草稿，载入已保存意图</Button>
      </div>}
      {intentEditor.storageFailed && <small role="alert">浏览器暂时无法保存会话草稿，请保持本页打开并保存意图。</small>}
      <div className="field-grid two compact">
        <Field label="身份意图"><textarea rows={2} disabled={readOnly || busy} value={intentDraft.identityIntent} onChange={(event) => setIntentDraft((draft) => ({ ...draft, identityIntent: event.target.value }))} /></Field>
        <Field label="构图意图"><textarea rows={2} disabled={readOnly || busy} value={intentDraft.compositionIntent} onChange={(event) => setIntentDraft((draft) => ({ ...draft, compositionIntent: event.target.value }))} /></Field>
        <Field label="风格意图"><textarea rows={2} disabled={readOnly || busy} value={intentDraft.styleIntent} onChange={(event) => setIntentDraft((draft) => ({ ...draft, styleIntent: event.target.value }))} /></Field>
        <Field label="来源引用（每行一项）"><textarea data-testid="visual-intent-source-refs" rows={2} disabled={readOnly || busy} value={intentDraft.sourceRefs} onChange={(event) => setIntentDraft((draft) => ({ ...draft, sourceRefs: event.target.value }))} /></Field>
      </div>
      <div className="button-row"><Button data-testid="save-visual-intent" variant="quiet" disabled={readOnly || busy || intentEditor.stale} onClick={() => void saveIntent()}>{activeIntent ? `细化意图 r${activeIntent.revision}` : "保存意图"}</Button>{activeIntent && <small>已保存 r{activeIntent.revision}；审核选择会固定这一版本。</small>}</div>
    </section>}
    <Field label="审核兼容性说明"><textarea rows={2} placeholder="说明此参考与当前已批准镜头为何兼容" disabled={readOnly || busy} value={compatibility} onChange={(event) => setCompatibility(event.target.value)} /></Field>
    <div className="button-row">
      <Button variant="primary" data-testid="select-reviewed-keyframe" disabled={readOnly || busy || intentEditor.dirty || !keptAssetId || !selectedShot || !currentApproval || !activeIntent || !compatibility.trim()} onClick={() => void selectKeyframe()}>为当前 Shot 审核选择</Button>
      <Field label="连续预览镜头数"><select data-testid="preview-subset-length" value={Math.min(previewLength, maxPreviewLength || 1)} disabled={readOnly || busy || !maxPreviewLength} onChange={(event) => setPreviewLength(Number(event.target.value))}>{Array.from({ length: maxPreviewLength }, (_, index) => index + 1).map((length) => <option value={length} key={length}>{length}</option>)}</select></Field>
      <Button variant="primary" data-testid="create-still-preview" disabled={readOnly || busy || !previewShotIds.length || !!missingPreviewShotIds.length || !currentApproval} onClick={() => void createPreview()}>创建连续 still animatic</Button>
    </div>
    {!currentApproval && <small className="notice warning">需要当前 storyboard Approval；导入、比较和意图细化仍可继续。</small>}
    {!!previewShotIds.length && <small>{previewShotIds.join(" → ")} · {missingPreviewShotIds.length ? `尚缺 ${missingPreviewShotIds.length} 个审核关键帧：${missingPreviewShotIds.join("、")}` : "所有镜头已有当前审核关键帧，可冻结预览。"}</small>}
    <div className="preview-history"><strong>冻结预览历史</strong>{workbench.previews.map((item) => <button key={item.id} className={item.id === previewId ? "selected" : ""} onClick={() => selectPreview(item.id)}>{item.manifest.shotIds.join(" → ")} <Badge tone={stateTone(item.state)}>{item.state.toUpperCase()}</Badge></button>)}</div>
    {preview && <AnimaticPlayer preview={preview} projectId={projectId} frameIndex={frameIndex} playing={playing} onSeek={setFrameIndex} onPlay={() => setPlaying((current) => !current)} />}
  </Panel>;
}

function CandidateCard({ asset, projectId, selected, kept, onPick, onKeep }: { asset: ManagedAsset; projectId?: string; selected: boolean; kept: boolean; onPick: () => void; onKeep: () => void }) {
  return <article className={`media-candidate ${selected ? "selected" : ""}`}><button onClick={onPick} aria-pressed={selected}>{projectId && <img src={plotloomApi.managedAssetUrl(projectId, asset.id)} alt={`Imported candidate ${asset.id}`} />}<strong>{asset.width}×{asset.height} · {Math.ceil(asset.byteSize / 1024)} KB</strong><small>{asset.provenance?.origin || "来源未知"}</small>{asset.provenance?.declaredAdditions.length ? <small>已知新增：{asset.provenance.declaredAdditions.join("、")}</small> : null}</button><Button data-testid={`keep-candidate-${asset.id}`} variant={kept ? "primary" : "quiet"} onClick={onKeep}>{kept ? "已保留" : "保留此候选"}</Button></article>;
}

function AnimaticPlayer({ preview, projectId, frameIndex, playing, onSeek, onPlay }: { preview: StillPreview; projectId?: string; frameIndex: number; playing: boolean; onSeek: (index: number) => void; onPlay: () => void }) {
  const frame = preview.manifest.frames[frameIndex];
  return <div className="still-animatic" data-testid="still-animatic"><div><Badge tone={stateTone(preview.state)}>{preview.state.toUpperCase()}</Badge><strong> Reviewed still animatic · {preview.manifest.shotIds.join(" → ")}</strong></div>{stateGuidance(preview.state) && <small className="notice warning">{stateGuidance(preview.state)}</small>}{frame && projectId && <img src={plotloomApi.managedAssetUrl(projectId, frame.assetId)} alt={`Shot ${frame.shotId} reviewed still`} />}<div className="button-row"><Button data-testid="animatic-play-pause" variant="primary" onClick={onPlay}>{playing ? "暂停" : "播放"}</Button><Button variant="quiet" onClick={() => onSeek(Math.max(0, frameIndex - 1))}>上一镜头</Button><Button variant="quiet" onClick={() => onSeek(Math.min(preview.manifest.frames.length - 1, frameIndex + 1))}>下一镜头</Button><input data-testid="animatic-seek" type="range" min={0} max={Math.max(0, preview.manifest.frames.length - 1)} value={frameIndex} onChange={(event) => onSeek(Number(event.target.value))} /></div><small>{frame ? `${frame.shotId} · ${frame.durationMs}ms · frozen ${preview.manifestHash.slice(0, 12)}` : "空预览"}</small></div>;
}
