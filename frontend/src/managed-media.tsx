import { useEffect, useMemo, useState } from "react";
import type { ApprovalDecision, ManagedAsset, Shot, StillPreview, Storyboard, StoryboardReview, VisualWorkbench } from "./types";
import { plotloomApi } from "./api";
import { Badge, Button, Field, Panel } from "./components";

function previewKey(projectId: string): string { return `plotloom:still-preview:${projectId}`; }

function stateTone(state: StillPreview["state"]): "ok" | "warning" | "danger" {
  return state === "current" ? "ok" : state === "stale" ? "warning" : "danger";
}

export function ManagedMediaWorkbench({
  projectId, storyboard, selectedShot, storyboardRevision, review, readOnly,
}: {
  projectId?: string;
  storyboard: Storyboard;
  selectedShot: Shot | undefined;
  storyboardRevision?: number;
  review: StoryboardReview | null | undefined;
  readOnly: boolean;
}) {
  const [workbench, setWorkbench] = useState<VisualWorkbench>({ assets: [], selectionRevision: 0, previews: [] });
  const [candidates, setCandidates] = useState<string[]>([]);
  const [origin, setOrigin] = useState("Local creator import");
  const [compatibility, setCompatibility] = useState("Creator reviewed this reference against the current canonical shot.");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [previewId, setPreviewId] = useState("");
  const [playing, setPlaying] = useState(false);
  const [frameIndex, setFrameIndex] = useState(0);

  const refresh = async () => {
    if (!projectId) return;
    const next = await plotloomApi.getVisualWorkbench(projectId);
    setWorkbench(next);
    const saved = window.localStorage.getItem(previewKey(projectId));
    const preferred = next.previews.find((item) => item.id === saved) ?? next.previews[0];
    if (preferred) setPreviewId(preferred.id);
  };
  useEffect(() => { void refresh().catch((loadError) => setError(loadError instanceof Error ? loadError.message : "无法读取导入媒体")); }, [projectId]);

  const preview = workbench.previews.find((item) => item.id === previewId);
  const assets = useMemo(() => new Map(workbench.assets.map((asset) => [asset.id, asset])), [workbench.assets]);
  const sceneShots = useMemo(() => selectedShot
    ? storyboard.shots.filter((shot) => shot.sceneId === selectedShot.sceneId).sort((left, right) => left.order - right.order)
    : [], [storyboard, selectedShot]);
  const currentApproval: ApprovalDecision | undefined = review?.activeApproval ?? undefined;
  const previewShotIds = useMemo(() => {
    const start = selectedShot ? sceneShots.findIndex((shot) => shot.id === selectedShot.id) : -1;
    return start < 0 ? [] : sceneShots.slice(start, start + 3).map((shot) => shot.id);
  }, [sceneShots, selectedShot]);

  useEffect(() => {
    if (!playing || !preview) return;
    const frame = preview.manifest.frames[frameIndex];
    if (!frame) return;
    const timer = window.setTimeout(() => setFrameIndex((current) => (current + 1) % preview.manifest.frames.length), Math.max(250, frame.durationMs));
    return () => window.clearTimeout(timer);
  }, [playing, preview, frameIndex]);

  const chooseCandidate = (id: string) => setCandidates((current) => current.includes(id)
    ? current.filter((candidate) => candidate !== id)
    : [...current.slice(-1), id]);
  const selectPreview = (id: string) => {
    setPreviewId(id); setFrameIndex(0); setPlaying(false);
    if (projectId) window.localStorage.setItem(previewKey(projectId), id);
  };
  const importFile = async (file: File | undefined) => {
    if (!projectId || !file) return;
    setBusy(true); setError("");
    try {
      await plotloomApi.importManagedAsset(projectId, file, { origin, rights: "unknown", declaredAdditions: ["reference only"] });
      await refresh();
    } catch (importError) { setError(importError instanceof Error ? importError.message : "导入失败"); }
    finally { setBusy(false); }
  };
  const selectKeyframe = async () => {
    const assetId = candidates.at(-1);
    if (!projectId || !assetId || !selectedShot || !currentApproval || !storyboardRevision) return;
    setBusy(true); setError("");
    try {
      await plotloomApi.createVisualIntent(projectId, assetId, { role: "shot_keyframe", compositionIntent: selectedShot.composition, styleIntent: selectedShot.visualIntent });
      await plotloomApi.selectReviewedKeyframe(projectId, {
        assetId, shotId: selectedShot.id, sceneId: selectedShot.sceneId,
        expectedSelectionRevision: workbench.selectionRevision, storyboardRevision,
        approvalId: currentApproval.id, compatibilityNote: compatibility,
      });
      await refresh();
    } catch (selectionError) { setError(selectionError instanceof Error ? selectionError.message : "选择失败"); }
    finally { setBusy(false); }
  };
  const createPreview = async () => {
    if (!projectId || !selectedShot || !currentApproval || !storyboardRevision) return;
    if (previewShotIds.length !== 3) { setError("需要从同一场景的起始镜头选择连续三个镜头才能创建 P0 animatic。"); return; }
    setBusy(true); setError("");
    try {
      const created = await plotloomApi.createStillPreview(projectId, {
        sceneId: selectedShot.sceneId, shotIds: previewShotIds, expectedSelectionRevision: workbench.selectionRevision,
        storyboardRevision, approvalId: currentApproval.id,
      });
      await refresh(); selectPreview(created.id);
    } catch (previewError) { setError(previewError instanceof Error ? previewError.message : "预览创建失败"); }
    finally { setBusy(false); }
  };

  return <Panel className="managed-media-workbench" data-testid="managed-media-workbench">
    <div className="section-title"><span>Imported stills · P0</span><strong>非生成式审核关键帧</strong></div>
    <p className="muted">原始字节、独立来源声明和已审核绑定都会保留。此处不会创建生成任务或视频。</p>
    {error && <div className="notice warning" role="alert">{error}</div>}
    <div className="field-grid two compact">
      <Field label="来源声明"><input value={origin} disabled={readOnly || busy} onChange={(event) => setOrigin(event.target.value)} /></Field>
      <Field label="导入 JPEG / PNG"><input data-testid="managed-image-upload" type="file" accept="image/jpeg,image/png" disabled={readOnly || busy} onChange={(event) => void importFile(event.target.files?.[0])} /></Field>
    </div>
    <div className="media-candidate-grid" aria-label="候选图像比较">
      {workbench.assets.map((asset) => <CandidateCard key={asset.id} asset={asset} projectId={projectId} selected={candidates.includes(asset.id)} onPick={() => chooseCandidate(asset.id)} />)}
      {!workbench.assets.length && <small>导入四张真实 JPEG/PNG 后，在这里比较两个候选。</small>}
    </div>
    <div className="button-row"><small>{candidates.length === 2 ? "正在比较两个候选：显式保留其中一个、都不选，或继续细化意图。" : "最多选择两个候选进行对比。"}</small><Button variant="quiet" disabled={!candidates.length} onClick={() => setCandidates([])}>两者都不选</Button></div>
    <Field label="审核兼容性说明"><textarea rows={2} disabled={readOnly || busy} value={compatibility} onChange={(event) => setCompatibility(event.target.value)} /></Field>
    <div className="button-row">
      <Button variant="primary" data-testid="select-reviewed-keyframe" disabled={readOnly || busy || !candidates.length || !selectedShot || !currentApproval} onClick={() => void selectKeyframe()}>为当前 Shot 审核选择</Button>
      <Button variant="primary" data-testid="create-still-preview" disabled={readOnly || busy || previewShotIds.length !== 3 || !currentApproval} onClick={() => void createPreview()}>创建连续三镜头 still animatic</Button>
    </div>
    {!currentApproval && <small className="notice warning">需要当前 storyboard Approval；导入和候选比较仍可继续。</small>}
    <div className="preview-history">
      <strong>冻结预览历史</strong>
      {workbench.previews.map((item) => <button key={item.id} className={item.id === previewId ? "selected" : ""} onClick={() => selectPreview(item.id)}>
        {item.manifest.shotIds.join(" → ")} <Badge tone={stateTone(item.state)}>{item.state.toUpperCase()}</Badge>
      </button>)}
    </div>
    {preview && <AnimaticPlayer preview={preview} projectId={projectId} frameIndex={frameIndex} playing={playing} onSeek={setFrameIndex} onPlay={() => setPlaying((current) => !current)} />}
  </Panel>;
}

function CandidateCard({ asset, projectId, selected, onPick }: { asset: ManagedAsset; projectId?: string; selected: boolean; onPick: () => void }) {
  return <button className={`media-candidate ${selected ? "selected" : ""}`} onClick={onPick} aria-pressed={selected}>
    {projectId && <img src={plotloomApi.managedAssetUrl(projectId, asset.id)} alt={`Imported candidate ${asset.id}`} />}
    <strong>{asset.width}×{asset.height} · {Math.ceil(asset.byteSize / 1024)} KB</strong>
    <small>{asset.provenance?.origin || "来源未知"}</small>
  </button>;
}

function AnimaticPlayer({ preview, projectId, frameIndex, playing, onSeek, onPlay }: { preview: StillPreview; projectId?: string; frameIndex: number; playing: boolean; onSeek: (index: number) => void; onPlay: () => void }) {
  const frame = preview.manifest.frames[frameIndex];
  return <div className="still-animatic" data-testid="still-animatic">
    <div><Badge tone={stateTone(preview.state)}>{preview.state.toUpperCase()}</Badge><strong> Reviewed still animatic · {preview.manifest.shotIds.join(" → ")}</strong></div>
    {frame && projectId && <img src={plotloomApi.managedAssetUrl(projectId, frame.assetId)} alt={`Shot ${frame.shotId} reviewed still`} />}
    <div className="button-row"><Button data-testid="animatic-play-pause" variant="primary" onClick={onPlay}>{playing ? "暂停" : "播放"}</Button><Button variant="quiet" onClick={() => onSeek(Math.max(0, frameIndex - 1))}>上一镜头</Button><Button variant="quiet" onClick={() => onSeek(Math.min(preview.manifest.frames.length - 1, frameIndex + 1))}>下一镜头</Button><input data-testid="animatic-seek" type="range" min={0} max={Math.max(0, preview.manifest.frames.length - 1)} value={frameIndex} onChange={(event) => onSeek(Number(event.target.value))} /></div>
    <small>{frame ? `${frame.shotId} · ${frame.durationMs}ms · frozen ${preview.manifestHash.slice(0, 12)}` : "空预览"}</small>
  </div>;
}
