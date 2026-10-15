import { createContext, useContext, useEffect, useRef, useState, type ReactNode } from "react";
import { Button, Field, Panel } from "../../components";
import { autopilotApi } from "./api";
import type { AutopilotRun, Launch } from "./contracts";
import { MaterialReview } from "./MaterialReview";
import { projectAutopilotProgress } from "./progress";
import { ConcurrentActivity } from "./ConcurrentActivity";
import "./autopilot.css";

type Owner = { projectId: string; admissionKey: string; run: AutopilotRun | null; ready: boolean; busy: boolean; error: string; commandError: string;
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

function ActivityIndicator() {
  return <span className="autopilot-activity-indicator" aria-hidden="true" />;
}

export function AutopilotProgress() {
  const owner = useAutopilot();
  const run = owner?.run;
  if (!owner) return null;
  if (!run && owner.busy) return <div className="autopilot-progress" role="status" aria-live="polite"><ActivityIndicator /><strong>正在启动自动准备</strong><span>等待服务器确认；请勿重复提交。</span></div>;
  if (!run && !owner.error && !owner.commandError) return null;
  if (!run && !owner.ready) return <div className="autopilot-progress" role="status" aria-live="polite">无法确认自动运行状态，正在重新读取；请勿重复提交。</div>;
  if (!run) return <div className="autopilot-progress" role="status" aria-live="polite">{owner.error ? "素材运行状态读取失败，正在重试；不会重复发送任务。" : `上次操作未成功，已核实当前没有自动运行。${owner.commandError}`}</div>;
  const progress = projectAutopilotProgress(run);
  const label = owner.error || !owner.ready ? "状态待核实" : stateLabels[run.state];
  const activity = owner.ready && !owner.error ? `${stateLabels[run.state]} · ${phaseLabels[run.phase] || "制作规划"}` : label;
  const active = owner.busy || run.state === "running" || progress.generating > 0 || progress.validating > 0;
  return <div className="autopilot-progress" role="status" aria-live="polite" aria-atomic="true">
    {active && <ActivityIndicator />}<strong>{owner.ready && !owner.error ? activity : "素材状态待核实"}</strong>{owner.ready && !owner.error && <span>文字 {progress.textAdopted}/{progress.textRequired} · 图片 {progress.imagesSelected}{progress.imagesRequired !== null ? `/${progress.imagesRequired}` : " 项已暂选"}</span>}
    {(!owner.ready || owner.error) && <span>正在重新读取；暂不显示上次读取的进度统计。</span>}
    {owner.ready && !owner.error && <span>候选已保留 {progress.imagesRetained} 张{progress.imagesRequired === null ? " · 图片总量待完整发现" : ""}
      {run.activities && ` · 生成 ${progress.generating} · 校验 ${progress.validating} · 排队 ${progress.queued}`}</span>}
    {!owner.error && run.blocker && <span>{run.blocker.message}</span>}
  </div>;
}

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
      setReady(false);
      setReadEpoch(epoch => epoch + 1);
    } }
    finally { command.current = false; setBusy(false); }
  };
  const owner: Owner = { projectId, admissionKey: `${projectId}:${revision}:${admissionVersion}`, run, ready, busy, error, commandError, start: body => execute(() => autopilotApi.start(projectId, { ...body, expectedBriefRevision: revision }), true) };
  const controllable = run && !["cancelled", "taken_over", "stale", "handed_off"].includes(run.state);
  const progress = run ? projectAutopilotProgress(run) : null;
  return <Context.Provider value={owner}>
    {run && <section className="autopilot-status" aria-label="视频素材准备" role="region">
      <div><strong>{ready ? stateLabels[run.state] : "素材状态待核实"}</strong><span>{phaseLabels[run.phase] || "制作规划"}</span>
      <small>AI 初稿与暂选图片 · {!ready ? "人工审阅状态待核实" : run.handoff && run.state === "handed_off" ? "已记录完整人工审阅" : "尚未获得完整人工审阅"}</small></div>
      {ready && progress ? <p>文字初稿 {progress.textAdopted}/{progress.textRequired} 已采用 · {progress.imagesSelected} 项图片已暂选{progress.imagesRequired !== null ? ` / ${progress.imagesRequired} 项必需素材` : ""} · 任务上限 {run.policy.maxJobs} · 图片上限 {run.policy.maxImages}</p> : <p>正在重新读取；暂不显示上次读取的进度统计。</p>}
      {ready && progress && <p>已保留 {progress.imagesRetained} 张图片候选{progress.imagesRequired === null ? "；图片总量待完整发现。" : "。"}</p>}
      {ready && run.policy.executorBinding && <p>本次生成：Codex · {run.policy.executorBinding.model} · 最多同时运行 {run.policy.executorBinding.maxProcesses} 项任务</p>}
      {ready && <ConcurrentActivity run={run} />}
      {["plotloom.pre-video.v2", "plotloom.pre-video.v3"].includes(run.policy.version || "") && <p>首帧比例不符时，将保留原图并按冻结目标居中裁剪、缩放为独立素材；仍需你审阅。</p>}
      {ready && run.blocker && <p role="status">{run.blocker.message}</p>}
      <div className="button-row">
        {controllable && ["running", "waiting"].includes(run.state) && <Button disabled={busy || readOnly || !ready} onClick={() => void execute(() => autopilotApi.control(projectId, run.revision, "pause"))}>暂停</Button>}
        {controllable && ["paused", "blocked"].includes(run.state) && <Button disabled={busy || readOnly || !ready} onClick={() => void execute(() => autopilotApi.control(projectId, run.revision, "resume"), true)}>继续原任务</Button>}
        {controllable && <><Button disabled={busy || readOnly || !ready} onClick={() => void execute(() => autopilotApi.control(projectId, run.revision, "cancel"))}>取消自动准备</Button><Button disabled={busy || readOnly || !ready} onClick={() => void execute(() => autopilotApi.control(projectId, run.revision, "takeover"), true)}>接管手动编辑</Button></>}
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

export function AutopilotLaunch({ saved, dirty, disabled, visualDirection, onContinueManually }: {
  saved: boolean; dirty: boolean; disabled: boolean; visualDirection?: string | null; onContinueManually?: () => void;
}) {
  const owner = useAutopilot(); const [open, setOpen] = useState(false);
  const [admission, setAdmission] = useState<{ key: string; eligible: boolean; failed?: boolean } | null>(null);
  const [admissionRetry, setAdmissionRetry] = useState(0);
  const [images, setImages] = useState(80); const [jobs, setJobs] = useState(96);
  const projectId = owner?.projectId || "";
  const admissionKey = owner?.admissionKey || "";
  useEffect(() => {
    setAdmission(null);
    if (!saved || !projectId) return;
    const abort = new AbortController();
    autopilotApi.launchContext(projectId, abort.signal).then(value => { if (!abort.signal.aborted) setAdmission({ key: admissionKey, eligible: value.eligible }); }).catch(() => {
      if (!abort.signal.aborted) setAdmission({ key: admissionKey, eligible: false, failed: true });
    });
    return () => abort.abort();
  }, [saved, projectId, admissionKey, admissionRetry]);
  if (!owner || !saved || owner.run) return null;
  if (!owner.ready) return <Panel className="autopilot-launch"><strong>自动准备入口</strong>
    <p role="status">正在核对是否已有自动运行；核对完成前不会重复启动。</p>
    {onContinueManually && <Button variant="quiet" disabled={disabled || dirty || owner.busy} onClick={onContinueManually}>继续手动创作</Button>}
  </Panel>;
  const eligible = admission?.key === admissionKey && admission.eligible;
  const retryAdmission = () => { setAdmission(null); setAdmissionRetry(epoch => epoch + 1); };
  return <Panel className="autopilot-launch"><div className="autopilot-launch-choice"><div><strong>简报已保存</strong><p>现在可以自动准备视频素材，也可以继续手动创作。</p></div>
    <div className="button-row"><Button variant="primary" disabled={disabled || dirty || owner.busy || !eligible} onClick={() => setOpen(value => !value)}>自动准备素材</Button>
      {onContinueManually && <Button variant="quiet" disabled={disabled || dirty || owner.busy} onClick={onContinueManually}>继续手动创作</Button>}</div></div>
    {admission?.key !== admissionKey && <p role="status">正在核对项目是否可开始自动准备…</p>}
    {admission?.key === admissionKey && !admission.eligible && (admission.failed
      ? <div className="autopilot-admission-error"><p role="status">暂时无法核对自动准备条件；可重试核对或继续手动创作。</p><Button variant="quiet" disabled={disabled || dirty || owner.busy} onClick={retryAdmission}>重试核对</Button></div>
      : <p role="status">此项目当前不符合自动准备条件；可继续手动创作。</p>)}
    {dirty && <p>先保存当前简报，再开始准备。</p>}
    {open && eligible && <div className="stack"><p>使用已保存简报，AI 自动采用故事初稿并暂选角色、场景与每个镜头的首帧。全部路线准备完成后，由你一次审阅。</p>
      <p>角色与美术设定就绪后，可先准备最多四项参考图，计入本次任务与图片上限。完整素材发现后若超出上限，将停止新增任务，保留候选供你手动接管。</p>
      <section className="autopilot-brief-style" aria-label="本次冻结的简报视觉方向"><strong>角色、美术与图片将遵循已保存简报的视觉风格</strong>
        <p>{visualDirection?.trim() || "简报未指定视觉风格；交由专业助手结合故事内容判断，不默认真人实拍或其他预设。"}</p></section>
      <p>首帧比例不符时，将保留原图，居中裁剪并缩放到简报目标尺寸，作为独立素材供你审阅。比例已匹配的原图保持原样。</p>
      <p>由 Codex 执行文字与图片任务；启动时核对当前执行条件。</p>
      <div className="field-grid two"><Field label="最多图片数"><input type="number" min={1} max={256} value={images} onChange={event => setImages(Number(event.target.value))} /></Field><Field label="最多任务数"><input type="number" min={9} max={288} value={jobs} onChange={event => setJobs(Number(event.target.value))} /></Field></div>
      <p>本次不生成视频、声音或可选尾帧。图片质量、构图与人物身份仍需你审阅；暂停或取消会保留已发送任务的结果。</p>
      <Button variant="primary" busy={owner.busy} disabled={disabled || dirty || owner.busy || !Number.isInteger(images) || images < 1 || images > 256 || !Number.isInteger(jobs) || jobs < 9 || jobs > 288} onClick={() => void owner.start({ styleAuthority: "brief", maxImages: images, maxJobs: jobs })}>{owner.busy && <ActivityIndicator />}{owner.busy ? "正在开始自动准备…" : "开始准备已保存简报的素材"}</Button>
    </div>}
  </Panel>;
}
