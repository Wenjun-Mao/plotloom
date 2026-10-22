import { useEffect, useRef, useState } from "react";
import type { ManagedAsset, VideoBackendProfile } from "./types";
import { plotloomApi } from "./api";
import type { VideoEndFrameDecision } from "./api";
import { Button } from "./components";
import { ApiError } from "./api-transport";
import type { MediaReadPhase } from "./features/media/useMediaWorkbenchData";
import "./video-end-frame.css";

type AspectPolicy = "reject_mismatch" | "contain_pad" | "cover_center_crop";
type Failure = { operation: "read" | "save"; detail: string };

function errorDetail(reason: unknown): string {
  if (reason instanceof ApiError) return `${reason.name}: ${reason.message}\nHTTP ${reason.status}\n${JSON.stringify(reason.details, null, 2) ?? ""}`;
  return reason instanceof Error ? `${reason.name}: ${reason.message}` : String(reason);
}

function decisionLabel(decision: VideoEndFrameDecision): string {
  if (decision.revision === 0) return "当前设置：不使用末帧画面。";
  return `当前已保存：${decision.assetId ? `末帧 ${decision.assetId.slice(0, 8)}` : "不使用末帧画面"} · 第 ${decision.revision} 版。`;
}

export function VideoEndFrameChoice({ projectId, shotId, approvalId, storyboardRevision, profile,
  requestAspectPolicy, readOnly, onDecision, onDraftChange, onReadinessChange }: {
  projectId: string; shotId: string; approvalId?: string; storyboardRevision?: number;
  profile?: VideoBackendProfile; requestAspectPolicy: AspectPolicy; readOnly: boolean;
  onDecision: (value: VideoEndFrameDecision) => void;
  onDraftChange?: (dirty: boolean) => void;
  onReadinessChange: (ready: boolean) => void;
}) {
  const [decision, setDecision] = useState<VideoEndFrameDecision | null>(null);
  const [assets, setAssets] = useState<ManagedAsset[]>([]);
  const [assetId, setAssetId] = useState("");
  const [policy, setPolicy] = useState<AspectPolicy>(requestAspectPolicy);
  const [failure, setFailure] = useState<Failure | null>(null);
  const [readPhase, setReadPhase] = useState<MediaReadPhase>("loading");
  const [saving, setSaving] = useState(false);
  const busy = readPhase === "loading" || saving;
  const ready = readPhase === "ready" && !saving;
  const session = useRef(0);
  const loadRequest = useRef(0);

  const load = async (owner: number) => {
    const request = ++loadRequest.current;
    setReadPhase("loading"); setFailure(null); onReadinessChange(false);
    try {
      const [next, catalog] = await Promise.all([
        plotloomApi.getVideoEndFrame(projectId, shotId), plotloomApi.getManagedAssets(projectId),
      ]);
      if (owner !== session.current || request !== loadRequest.current) return;
      setDecision(next); setAssets(catalog.assets); setAssetId(next.assetId ?? "");
      setPolicy(next.aspectPolicy ?? requestAspectPolicy); setReadPhase("ready"); onDecision(next);
      onDraftChange?.(false);
      onReadinessChange(true);
    } catch (reason) {
      if (owner === session.current && request === loadRequest.current) {
        setReadPhase("error"); setFailure({ operation: "read", detail: errorDetail(reason) });
      }
    }
  };

  useEffect(() => {
    const owner = ++session.current;
    setDecision(null); setAssets([]); setAssetId(""); setPolicy(requestAspectPolicy); setFailure(null); setSaving(false);
    void load(owner);
    return () => { session.current += 1; loadRequest.current += 1; };
  }, [projectId, shotId, approvalId, storyboardRevision]);

  const choose = async () => {
    if (readOnly || !decision || !approvalId || !storyboardRevision || !ready) return;
    const owner = session.current;
    setSaving(true); setFailure(null); onReadinessChange(false);
    try {
      const next = await plotloomApi.chooseVideoEndFrame(projectId, shotId, {
        assetId: assetId || null, approvalId, storyboardRevision,
        expectedRevision: decision.revision, aspectPolicy: assetId ? policy : null,
      });
      if (owner !== session.current) return;
      loadRequest.current += 1;
      setDecision(next); onDecision(next);
      onDraftChange?.(false);
      onReadinessChange(true);
    } catch (reason) {
      if (owner === session.current) {
        // A failed response cannot establish whether the write committed.
        setReadPhase("error"); setFailure({ operation: "save", detail: errorDetail(reason) });
      }
    } finally { if (owner === session.current) setSaving(false); }
  };
  const selected = assets.find((item) => item.id === assetId);
  const mismatch = Boolean(selected && profile && selected.width * profile.height !== selected.height * profile.width);
  const policyReady = policy === requestAspectPolicy && (!mismatch || policy !== "reject_mismatch");
  return <section className="video-end-frame-choice" data-testid="h3-end-frame-choice">
    <header><strong>可选末帧画面</strong>
      <small>末帧是当前镜头的视觉引导，不保证生成画面精确重合。保存决定后仍须预览完整提示词；改变末帧会使旧候选失效。</small></header>
    <label>项目内已管理图片
      <select value={assetId} disabled={readOnly || !ready || !decision} onChange={(event) => {
        setAssetId(event.target.value); onDraftChange?.(true);
      }}>
        <option value="">不使用末帧画面</option>
        {assets.filter((item) => ["image/png", "image/jpeg"].includes(item.mimeType)).map((item) =>
          <option key={item.id} value={item.id}>{item.id.slice(0, 8)} · {item.width}×{item.height}</option>)}
      </select>
    </label>
    {selected && <><div className="video-end-frame-preview">
      <img src={plotloomApi.managedAssetUrl(projectId, selected.id)} alt="待选末帧画面" />
      <div><small>{selected.width}×{selected.height} · 起始关键帧与末帧独立选择。</small>
        <details className="video-end-frame-technical"><summary>原图指纹</summary>
          <code>SHA-256 {selected.originalHash}</code></details></div>
    </div>
      <label>统一输入比例处理
        <select value={policy} disabled={readOnly || !ready} onChange={(event) => {
          setPolicy(event.target.value as AspectPolicy); onDraftChange?.(true);
        }}>
          <option value="reject_mismatch">比例匹配，直接使用原图</option>
          <option value="contain_pad">网关保留画布并补黑边</option>
          <option value="cover_center_crop">网关居中裁切</option>
        </select>
      </label>
      <small>H3 一次请求对首帧与末帧使用同一比例处理。当前请求选择 {requestAspectPolicy}。{mismatch ? "末帧与输出比例不同。" : "末帧与输出比例匹配。"}</small>
      {!policyReady && <small className="notice warning">请使末帧比例处理与当前请求一致，并确保不匹配时明确选择裁切或黑边。</small>}
    </>}
    <div className="button-row"><Button disabled={busy} onClick={() => void load(session.current)}>刷新末帧与图片列表</Button>
      <Button disabled={readOnly || !ready || !decision || !approvalId || !storyboardRevision || Boolean(selected && !policyReady)} onClick={() => void choose()}>保存当前镜头末帧决定</Button></div>
    <small role="status">{saving ? "正在保存末帧设置…" : readPhase === "loading" ? "正在读取末帧设置与图片列表…" : readPhase === "error" ? "当前末帧设置尚未核实。" : decision && decisionLabel(decision)}</small>
    {!ready && decision && <small>上次核实：{decisionLabel(decision)}当前状态仍需重新核实。</small>}
    {failure && <div className="notice warning video-end-frame-error" role="alert">
      <small>{failure.operation === "read" ? "无法读取末帧设置与图片列表。请重新读取；核实前不能保存或准备新视频。" : "未能确认末帧设置的保存结果。设置可能已经保存；请重新读取核实，不要重复保存。"}</small>
      <details className="video-end-frame-technical"><summary>{failure.operation === "read" ? "读取错误详情" : "保存错误详情"}</summary><pre>{failure.detail}</pre></details>
    </div>}
  </section>;
}
