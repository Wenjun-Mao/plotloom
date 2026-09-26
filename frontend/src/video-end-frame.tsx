import { useEffect, useRef, useState } from "react";
import type { ManagedAsset, VideoBackendProfile } from "./types";
import { plotloomApi } from "./api";
import type { VideoEndFrameDecision } from "./api";
import { Button } from "./components";
import "./video-end-frame.css";

type AspectPolicy = "reject_mismatch" | "contain_pad" | "cover_center_crop";

export function VideoEndFrameChoice({ projectId, shotId, approvalId, storyboardRevision, profile,
  requestAspectPolicy, readOnly, onDecision, onDraftChange }: {
  projectId: string; shotId: string; approvalId?: string; storyboardRevision?: number;
  profile?: VideoBackendProfile; requestAspectPolicy: AspectPolicy; readOnly: boolean;
  onDecision: (value: VideoEndFrameDecision) => void;
  onDraftChange?: (dirty: boolean) => void;
}) {
  const [decision, setDecision] = useState<VideoEndFrameDecision | null>(null);
  const [assets, setAssets] = useState<ManagedAsset[]>([]);
  const [assetId, setAssetId] = useState("");
  const [policy, setPolicy] = useState<AspectPolicy>(requestAspectPolicy);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const session = useRef(0);
  const loadRequest = useRef(0);

  const load = async (owner: number) => {
    const request = ++loadRequest.current;
    setBusy(true);
    try {
      const [next, catalog] = await Promise.all([
        plotloomApi.getVideoEndFrame(projectId, shotId), plotloomApi.getManagedAssets(projectId),
      ]);
      if (owner !== session.current || request !== loadRequest.current) return;
      setDecision(next); setAssets(catalog.assets); setAssetId(next.assetId ?? "");
      setPolicy(next.aspectPolicy ?? requestAspectPolicy); setError(""); onDecision(next);
      onDraftChange?.(false);
    } catch (reason) {
      if (owner === session.current && request === loadRequest.current)
        setError(reason instanceof Error ? reason.message : "无法读取末帧决定");
    } finally {
      if (owner === session.current && request === loadRequest.current) setBusy(false);
    }
  };

  useEffect(() => {
    const owner = ++session.current;
    setDecision(null); setAssets([]); setAssetId(""); setPolicy(requestAspectPolicy); setError("");
    void load(owner);
    return () => { session.current += 1; loadRequest.current += 1; };
  }, [projectId, shotId]);

  const choose = async () => {
    if (!decision || !approvalId || !storyboardRevision || busy) return;
    const owner = session.current;
    setBusy(true); setError("");
    try {
      const next = await plotloomApi.chooseVideoEndFrame(projectId, shotId, {
        assetId: assetId || null, approvalId, storyboardRevision,
        expectedRevision: decision.revision, aspectPolicy: assetId ? policy : null,
      });
      if (owner !== session.current) return;
      loadRequest.current += 1;
      setDecision(next); onDecision(next);
      onDraftChange?.(false);
    } catch (reason) {
      if (owner === session.current) setError(reason instanceof Error ? reason.message : "末帧决定未保存");
    } finally { if (owner === session.current) setBusy(false); }
  };
  const selected = assets.find((item) => item.id === assetId);
  const mismatch = Boolean(selected && profile && selected.width * profile.height !== selected.height * profile.width);
  const policyReady = policy === requestAspectPolicy && (!mismatch || policy !== "reject_mismatch");
  return <section className="video-end-frame-choice" data-testid="h3-end-frame-choice">
    <header><strong>可选末帧画面</strong>
      <small>末帧是当前镜头的视觉引导，不保证生成画面精确重合。保存决定后仍须预览完整提示词；改变末帧会使旧候选失效。</small></header>
    <label>项目内已管理图片
      <select value={assetId} disabled={readOnly || busy || !decision} onChange={(event) => {
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
        <select value={policy} disabled={readOnly || busy} onChange={(event) => {
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
      <Button disabled={readOnly || busy || !decision || !approvalId || !storyboardRevision || Boolean(selected && !policyReady)} onClick={() => void choose()}>保存当前镜头末帧决定</Button></div>
    <small>当前已保存：{decision?.assetId ? `末帧 ${decision.assetId.slice(0, 8)} · 第 ${decision.revision} 版` : "无末帧"}。</small>
    {error && <small className="notice warning" role="alert">{error}</small>}
  </section>;
}
