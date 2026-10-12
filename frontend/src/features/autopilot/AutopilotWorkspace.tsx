import { createContext, useContext, useEffect, useRef, useState, type ReactNode } from "react";
import { Button, Field, Panel } from "../../components";
import type { ArtRenderStyle } from "../../types";
import { specialistsApi, type SpecialistSettings } from "../specialists/api";
import { autopilotApi } from "./api";
import type { AutopilotRun, Launch } from "./contracts";
import { MaterialReview } from "./MaterialReview";
import "./autopilot.css";

type Owner = { projectId: string; admissionKey: string; run: AutopilotRun | null; ready: boolean; busy: boolean; error: string;
  start: (body: Omit<Launch, "expectedBriefRevision">) => Promise<void> };
const Context = createContext<Owner | null>(null);
export const useAutopilot = () => useContext(Context);
export const adoptionSentence = (label: string, subject: string) => label === "已确认" ? `${subject}已确认` : `${subject} · ${label}`;
export function useAdoptionLabel() {
  const owner = useAutopilot();
  return (operation: string, revision?: number, hash?: string) => {
    if (owner && !owner.ready) return "已采用 · 来源待核实";
    if (owner?.run?.checkpoints.some(item => item.operationKey === operation && item.state === "adopted"
      && item.evidence.result.revision === revision && item.evidence.result.contentHash === hash)) return "AI 已采用";
    if (owner?.run && !["taken_over", "cancelled", "stale", "handed_off"].includes(owner.run.state)) return "已采用 · 来源待核实";
    return "已确认";
  };
}
const stateLabels: Record<AutopilotRun["state"], string> = { running: "正在准备", waiting: "等待助手交付", paused: "已暂停", blocked: "需要处理", cancelled: "已取消", stale: "素材已变化", taken_over: "已手动接管", awaiting_review: "等待你审阅", handed_off: "素材已记录人工审阅" };
const phaseLabels: Record<string, string> = { source: "故事来源", outline: "故事大纲", branches: "故事路线", characters: "角色设定", art: "美术方向", script: "完整剧本", storyboard: "分镜", "bridge-intent": "戏剧意图", "bridge-presentation": "画面呈现", references: "参考图片", "first-frames": "镜头首帧", "material-review": "完整素材审阅", "manual-video": "手动视频制作" };

export function AutopilotWorkspace({ projectId, revision, admissionVersion = 0, readOnly, onChanged, onVideo, children }: {
  projectId: string; revision: number; admissionVersion?: number; readOnly: boolean; onChanged: () => Promise<void>; onVideo: () => void; children: ReactNode;
}) {
  const [run, setRun] = useState<AutopilotRun | null>(null);
  const [ready, setReady] = useState(false);
  const [busy, setBusy] = useState(false); const [error, setError] = useState(""); const [review, setReview] = useState(false);
  const [commandError, setCommandError] = useState("");
  const identity = useRef(projectId); identity.current = projectId;
  const command = useRef(false);
  const [readEpoch, setReadEpoch] = useState(0);
  const readContext = useRef("");
  useEffect(() => {
    const context = `${projectId}:${revision}`;
    if (readContext.current !== context) {
      readContext.current = context;
      setRun(null); setReady(false); setReview(false); setError(""); setCommandError("");
    }
    if (!projectId) return;
    const abort = new AbortController(); let timer: ReturnType<typeof setTimeout>;
    const refresh = async () => {
      try {
        const value = await autopilotApi.current(projectId, abort.signal);
        if (abort.signal.aborted) return;
        setRun(previous => value && previous?.id === value.id && previous.revision > value.revision ? previous : value); setReady(true); setError("");
        if (value?.state === "handed_off") setReview(false);
        // Material commands can withdraw a completed run without changing Brief.
        if (value) timer = setTimeout(refresh, 5000);
      } catch (failure) { if (!abort.signal.aborted) {
        setReady(false); setError(String(failure instanceof Error ? failure.message : failure));
        timer = setTimeout(refresh, 5000);
      } }
    };
    void refresh(); return () => { abort.abort(); clearTimeout(timer); };
  }, [projectId, revision, readEpoch]);
  const execute = async (operation: () => Promise<AutopilotRun>, refresh = false) => {
    if (command.current) return;
    command.current = true;
    setBusy(true); setCommandError("");
    try { const value = await operation(); if (identity.current !== projectId) return; setRun(value); setReadEpoch(epoch => epoch + 1); if (refresh) await onChanged(); }
    catch (failure) { if (identity.current === projectId) {
      setCommandError(failure instanceof Error ? failure.message : String(failure));
      // Reconcile an uncertain command response by reading the durable run;
      // never replay the command just to recover browser observation.
      setReadEpoch(epoch => epoch + 1);
    } }
    finally { command.current = false; setBusy(false); }
  };
  const owner: Owner = { projectId, admissionKey: `${projectId}:${revision}:${admissionVersion}`, run, ready, busy, error: error || commandError, start: body => execute(() => autopilotApi.start(projectId, { ...body, expectedBriefRevision: revision }), true) };
  const controllable = run && !["cancelled", "taken_over", "stale", "handed_off"].includes(run.state);
  const counts = run?.checkpoints.filter(item => ["image", "character-reference", "art-reference"].includes(item.evidence.owner));
  const inventory = run?.checkpoints.find(item => item.operationKey === "material.inventory")?.evidence.result.inventory as { subjects?: unknown[] } | undefined;
  const requiredImages = run?.bundle ? run.bundle.inventory.subjects.length : Array.isArray(inventory?.subjects) ? inventory.subjects.length : null;
  const textCount = run?.checkpoints.filter(item => ["outline", "branches", "characters", "art", "script", "storyboard", "bridge-intent", "bridge-presentation"].includes(item.operationKey) && item.state === "adopted").length || 0;
  return <Context.Provider value={owner}>
    {run && <section className="autopilot-status" aria-label="视频素材准备" role="region">
      <div><strong>{ready ? stateLabels[run.state] : "素材状态待核实"}</strong><span>{phaseLabels[run.phase] || "制作规划"}</span>
      <small>AI 初稿与暂选图片 · {!ready ? "人工审阅状态待核实" : run.handoff && run.state === "handed_off" ? "已记录完整人工审阅" : "尚未获得完整人工审阅"}</small></div>
      <p>文字初稿 {textCount}/8 已采用 · {counts?.filter(item => item.state === "adopted" && item.evidence.result.geometryCompatible !== false).length || 0} 项图片已暂选{requiredImages !== null ? ` / ${requiredImages} 项必需素材` : ""} · 任务上限 {run.policy.maxJobs} · 图片上限 {run.policy.maxImages}</p>
      {run.blocker && <p role="status">{run.blocker.message}</p>}
      <div className="button-row">
        {controllable && ["running", "waiting"].includes(run.state) && <Button disabled={busy || readOnly} onClick={() => void execute(() => autopilotApi.control(projectId, run.revision, "pause"))}>暂停</Button>}
        {controllable && ["paused", "blocked"].includes(run.state) && <Button disabled={busy || readOnly} onClick={() => void execute(() => autopilotApi.control(projectId, run.revision, "resume"), true)}>继续原任务</Button>}
        {controllable && <><Button disabled={busy || readOnly} onClick={() => void execute(() => autopilotApi.control(projectId, run.revision, "cancel"))}>取消自动准备</Button><Button disabled={busy || readOnly} onClick={() => void execute(() => autopilotApi.control(projectId, run.revision, "takeover"), true)}>接管手动编辑</Button></>}
        {["awaiting_review", "taken_over", "cancelled", "stale"].includes(run.state) && <Button variant="primary" disabled={busy || readOnly || !ready} onClick={() => setReview(true)}>审阅完整素材</Button>}
        {run.state === "handed_off" && ready && <Button variant="primary" onClick={onVideo}>进入手动视频制作</Button>}
      </div>
    </section>}
    {error && <p className="autopilot-error" role="alert">素材准备：{error}</p>}
    {commandError && <p className="autopilot-error" role="alert">上次操作反馈：{commandError}</p>}
    {children}
    {review && run && <MaterialReview key={`${projectId}:${run.revision}`} projectId={projectId} readOnly={readOnly || !ready} onClose={() => setReview(false)}
      onUncertain={message => { setCommandError(message); setReady(false); setReadEpoch(epoch => epoch + 1); }}
      onAccepted={async value => { setRun(value); setReview(false); await onChanged(); }} />}
  </Context.Provider>;
}

export function AutopilotLaunch({ saved, dirty, disabled }: { saved: boolean; dirty: boolean; disabled: boolean }) {
  const owner = useAutopilot(); const [open, setOpen] = useState(false);
  const [admission, setAdmission] = useState<{ key: string; eligible: boolean } | null>(null);
  const [settings, setSettings] = useState<SpecialistSettings | null>(null); const [settingsError, setSettingsError] = useState("");
  const [style, setStyle] = useState<ArtRenderStyle>("live-action"); const [images, setImages] = useState(80); const [jobs, setJobs] = useState(96);
  const projectId = owner?.projectId || "";
  const admissionKey = owner?.admissionKey || "";
  useEffect(() => {
    setAdmission(null);
    if (!saved || !projectId) return;
    const abort = new AbortController();
    autopilotApi.launchContext(projectId, abort.signal).then(value => { if (!abort.signal.aborted) setAdmission({ key: admissionKey, eligible: value.eligible }); }).catch(() => undefined);
    return () => abort.abort();
  }, [saved, projectId, admissionKey]);
  useEffect(() => { if (!open) return; let active = true; specialistsApi.settings().then(value => { if (active) setSettings(value); }).catch(failure => { if (active) setSettingsError(String(failure)); }); return () => { active = false; }; }, [open]);
  if (!owner || !saved || owner.run || !owner.ready || admission?.key !== admissionKey || !admission.eligible) return null;
  const configured = Boolean(settings?.text.taskId && settings?.image.taskId && settings.text.taskId !== settings.image.taskId && !settings.busy);
  return <Panel className="autopilot-launch"><Button variant="primary" disabled={disabled || dirty || owner.busy} onClick={() => setOpen(value => !value)}>一键准备视频素材</Button>
    {dirty && <p>先保存当前简报，再开始准备。</p>}
    {open && <div className="stack"><p>使用已保存简报，AI 自动采用故事初稿并暂选角色、场景与每个镜头的首帧。全部路线准备完成后，由你一次审阅。</p>
      <p>文字助手：{settings?.text.name || "未配置"} · 图片助手：{settings?.image.name || "未配置"}</p>
      <Field label="角色与美术图像风格"><select value={style} onChange={event => setStyle(event.target.value as ArtRenderStyle)}><option value="live-action">真人实拍</option><option value="realistic">写实</option><option value="ghibli">吉卜力风格</option></select></Field>
      <div className="field-grid two"><Field label="最多图片数"><input type="number" min={1} max={256} value={images} onChange={event => setImages(Number(event.target.value))} /></Field><Field label="最多任务数"><input type="number" min={9} max={288} value={jobs} onChange={event => setJobs(Number(event.target.value))} /></Field></div>
      <p>本次不生成视频、声音或可选尾帧。图片质量、构图与人物身份仍需你审阅；暂停或取消会保留已发送任务的结果。</p>
      {settingsError && <p role="alert">{settingsError}</p>}
      {!configured && <p>请先在“生成助手设置”中配置两个空闲助手。</p>}
      <Button variant="primary" busy={owner.busy} disabled={disabled || dirty || !configured || !Number.isInteger(images) || images < 1 || images > 256 || !Number.isInteger(jobs) || jobs < 9 || jobs > 288} onClick={() => void owner.start({ renderStyle: style, artRenderStyle: style, maxImages: images, maxJobs: jobs })}>开始准备已保存简报的素材</Button>
    </div>}
  </Panel>;
}
