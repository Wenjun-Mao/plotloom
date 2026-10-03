import { useRef, useState } from "react";
import { Button, ErrorNotice } from "../../components";
import { specialistsApi, type ImageTerminalTarget, type ImageTerminalPreview } from "./api";

export function ImageTerminalSettlement({ jobId, onSettled }: { jobId: string; onSettled: () => Promise<void> }) {
  const [project, setProject] = useState(() => new URLSearchParams(window.location.search).get("project") || "");
  const [target, setTarget] = useState<ImageTerminalTarget>("image_job");
  const [preview, setPreview] = useState<ImageTerminalPreview>();
  const [turn, setTurn] = useState("");
  const [revision, setRevision] = useState("");
  const [reviewer, setReviewer] = useState("");
  const [attested, setAttested] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [done, setDone] = useState(false);
  const operation = useRef(false);
  const inspect = async () => {
    if (operation.current) return;
    operation.current = true;
    setBusy(true); setError(""); setPreview(undefined); setAttested(false);
    try { setPreview(await specialistsApi.imageTerminalPreview(project, target, jobId)); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "无法核对终止声明。"); }
    finally { operation.current = false; setBusy(false); }
  };
  const settle = async () => {
    if (operation.current || !preview || !attested || !turn || !reviewer.trim() || !Number.isInteger(Number(revision)) || Number(revision) < 1) return;
    operation.current = true;
    setBusy(true); setError("");
    try {
      await specialistsApi.settleImageTerminal(project, target, jobId, {
        markerHash: preview.markerHash, taskId: preview.marker.taskId,
        terminalTurnId: turn, terminalRevision: Number(revision),
        reviewer, observedIdle: true, reviewedBlockedVerdict: true,
      });
      setDone(true); await onSettled();
    } catch (reason) { setError(reason instanceof Error ? reason.message : "终止审核未完成；预约保留。"); }
    finally { operation.current = false; setBusy(false); }
  };
  return <details><summary>核对生成前阻塞的终止声明</summary>
    <p>仅限已取消、成功 pin、未开始 ImageGen 的图像任务。取消或聊天 idle 不足以释放预约；必须先取得请求绑定的 terminal.json，再人工检查对应最终回合。</p>
    <fieldset disabled={busy || done}>
      <label>终止任务所属项目 ID<input value={project} onChange={event => { setProject(event.target.value); setPreview(undefined); setAttested(false); }} /></label>
      <label>终止任务类型<select value={target} onChange={event => { setTarget(event.target.value as ImageTerminalTarget); setPreview(undefined); setAttested(false); }}>
        <option value="image_job">镜头图片</option><option value="character_reference_proposal">角色参考</option><option value="art_reference_proposal">美术参考</option>
      </select></label>
      <Button disabled={!project.trim()} onClick={() => void inspect()}>读取并验证终止声明</Button>
      {preview && <>
        <p>任务：{jobId}<br />助手：{preview.marker.taskId}<br />请求：{preview.marker.requestHash}<br />声明 SHA-256：{preview.markerHash}</p>
        <p>生成前阻塞；声明未开始生成、无活动工具、无输出。原因：{preview.marker.reason}</p>
        <label>已检查的最终回合 ID<input value={turn} onChange={event => { setTurn(event.target.value); setAttested(false); }} /></label>
        <label>已检查的助手状态 revision<input type="number" min="1" step="1" value={revision} onChange={event => { setRevision(event.target.value); setAttested(false); }} /></label>
        <label>终止审核人<input value={reviewer} onChange={event => setReviewer(event.target.value)} /></label>
        <label><input type="checkbox" checked={attested} onChange={event => setAttested(event.target.checked)} />我已检查此助手对应最终回合的阻塞结论，确认当前 idle、无活动工具；这是人工观察，不是系统验证队列消息身份。</label>
        <Button variant="danger" disabled={!attested || !turn.trim() || !reviewer.trim() || !Number.isInteger(Number(revision)) || Number(revision) < 1} onClick={() => void settle()}>记录生成前阻塞并释放此任务预约</Button>
      </>}
    </fieldset>
    {done && <p role="status">生成前阻塞已核对；仅此任务预约已释放，未发布任何图片候选。</p>}
    {error && <ErrorNotice message={error} />}
  </details>;
}
