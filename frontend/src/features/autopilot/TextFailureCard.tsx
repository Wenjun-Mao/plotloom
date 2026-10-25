import { useEffect, useRef, useState } from "react";
import { useReviewEditorDraft } from "../authoring/ReviewDraftContext";
import { Button } from "../../components";
import { ApiError } from "../../api-transport";
import { autopilotApi } from "./api";
import type { AutopilotRun, TextFailure } from "./contracts";

const outcomes: Record<string, string> = { failed: "未通过", adopted: "已采用", prepared: "等待执行", delivered: "已交付" };
const comparisons = { repeated: "与上次相同的问题", changed: "问题已变化", unknown: "无法确定问题是否相同" };

export function TextFailureCard({ projectId, run, disabled, execute, stage, readingDisabled = false }: { projectId: string; run: AutopilotRun; disabled: boolean; stage?: string; readingDisabled?: boolean;
  execute: (operation: () => Promise<AutopilotRun>, refresh?: boolean, foreground?: boolean) => Promise<void> }) {
  const [failure, setFailure] = useState<TextFailure | null>(null);
  const [error, setError] = useState(false);
  const [readEpoch, setReadEpoch] = useState(0);
  const [details, setDetails] = useState(false);
  const [editing, setEditing] = useState(false);
  const [directions, setDirections] = useState("");
  const submitted = useRef<import("./contracts").TextRetry | null>(null);
  const [pending, setPending] = useState(false);
  const [message, setMessage] = useState("");
  const [resend, setResend] = useState(false);
  const refused = useRef(false);
  const draftOwner = useRef("");
  const scope = useRef<object | null>(null);
  const identity = `${projectId}:${run.id}:${run.revision}:${stage || run.phase}`;
  const live = useRef(identity); live.current = identity;
  useEffect(() => {
    const abort = new AbortController();
    const token = {}; scope.current = token;
    setFailure(null); setError(false);
    void autopilotApi.textFailure(projectId, abort.signal, stage).then(value => {
      if (!abort.signal.aborted && live.current === identity && value?.runId === run.id && value.runRevision === run.revision) {
        const owner = `${projectId}:${value.runId}:${value.failedAttemptId || value.stage + ":resolved"}`;
        if (draftOwner.current !== owner) {
          draftOwner.current = owner; submitted.current = null; refused.current = false;
          setPending(false); setMessage(""); setResend(false); setEditing(false); setDirections(""); setDetails(false);
        }
        setFailure(value);
      }
    }).catch(() => { if (!abort.signal.aborted && live.current === identity) setError(true); });
    return () => { abort.abort(); if (scope.current === token) scope.current = null; };
  }, [identity, readEpoch]);
  const working = useReviewEditorDraft(projectId, "text_retry", failure ? `${failure.runId}:${failure.runRevision}:${failure.failedAttemptId}:${failure.rejectionHash}` : "unverified", text => {
    setDirections(text); setEditing(true);
  }, disabled || pending || !failure?.canRetry, undefined, stage || run.phase);
  if (error) return <div><p role="status">暂时无法读取文字问题详情；补充要求与已提交请求保持保留。</p>
    <Button disabled={readingDisabled} onClick={() => setReadEpoch(epoch => epoch + 1)}>重新读取问题</Button></div>;
  if (!failure) return null;
  const send = (body: import("./contracts").TextRetry) => {
    const token = scope.current;
    setPending(true); setResend(false); setMessage("已提交本次追加修正，正在核对结果；补充要求已保留，请勿重复发送。");
    void execute(async () => {
      try { return await autopilotApi.retryText(projectId, body); }
      catch (error) {
        if (scope.current === token && token !== null) {
          refused.current = error instanceof ApiError && [400, 401, 403, 404, 409, 422].includes(error.status);
          setMessage(refused.current ? "本次请求未获接受；补充要求已保留。请核对当前状态后修改重试。" : "本次请求的结果待核对；补充要求与请求身份已保留，不会自动重发。");
        }
        throw error;
      }
    }, true, true);
  };
  const reconcile = () => {
    const body = submitted.current, token = scope.current;
    if (!body || readingDisabled) return;
    void execute(async () => {
      const observed = await autopilotApi.current(projectId);
      if (!observed) throw new Error("当前运行无法读取；未重新发送。");
      const value = await autopilotApi.textFailure(projectId, undefined, stage);
      if (scope.current === token && token !== null && value?.runId === body.expectedRunId
        && value.runId === observed.id && value.runRevision === observed.revision
        && value.failedAttemptId === body.failedAttemptId && value.rejectionHash === body.rejectionHash && value.canRetry) {
        setFailure(value);
        if (refused.current) {
          submitted.current = null; setPending(false); setResend(false);
          setMessage("已核对本次请求未创建修正。可保留或修改补充要求后再次提交。");
        } else {
          setResend(true); setMessage("尚未发现本次修正。可明确重发同一本次请求；请求身份和要求保持不变。");
        }
      }
      return observed;
    });
  };
  const retry = () => {
    if (disabled || working.stale || submitted.current || !failure.canRetry || !failure.failedAttemptId || !failure.rejectionHash || live.current !== identity) return;
    const body = { commandId: crypto.randomUUID(), expectedRunId: failure.runId, expectedRevision: failure.runRevision,
      failedAttemptId: failure.failedAttemptId, rejectionHash: failure.rejectionHash, directions: editing ? directions : "" };
    submitted.current = body; refused.current = false; send(body);
  };
  return <section className="autopilot-text-failure" aria-label={failure.resolved ? `${failure.stageLabel}修正历史` : "文字任务问题"}>
    <strong>{failure.stageLabel} · {failure.resolved ? "已修正并采用" : failure.terminalContentFailure ? "内容验证未通过" : "原任务需要核对"}</strong>
    <p>{failure.automaticLimit === 0 ? "自动修正已关闭。" : `自动修正已用 ${failure.automaticUsed}/${failure.automaticLimit} 次。`}{failure.reason}</p>
    <div className="button-row"><Button onClick={() => setDetails(value => !value)}>{details ? "收起问题" : "查看问题"}</Button>
      {failure.canRetry && <><Button disabled={disabled || working.stale || pending} onClick={retry}>再修正一次</Button>
        <Button disabled={disabled || working.stale || pending} onClick={() => { setDetails(true); setEditing(true); }}>修改要求后重试</Button></>}
    </div>
    {working.notice}
    {message && <p role="status">{message}</p>}
    {pending && <div className="button-row"><Button disabled={readingDisabled} onClick={reconcile}>核对本次修正</Button>
      {resend && <Button disabled={disabled} onClick={() => { if (submitted.current) send(submitted.current); }}>重发同一本次请求</Button>}</div>}
    {editing && <label className="field">补充修正要求（可选）<textarea value={directions} maxLength={4000} disabled={disabled || working.stale || pending}
      onChange={event => { setDirections(event.target.value); working.changed(event.target.value); }} placeholder="在原简报与已采用内容范围内补充要求，然后点击「再修正一次」。" /></label>}
    {details && <div className="stack">
      {failure.issues.map((issue, index) => <div key={index}><p>{issue.field === "$" ? <strong>整份候选（来源未提供精确字段）</strong> : <><strong>{issue.item}</strong> · <code>{issue.field}</code></>}</p>
        <p>{issue.rule}</p>{issue.excerpt !== null && <pre>{issue.excerpt}</pre>}</div>)}
      {failure.diagnostics.length > 0 && <div><strong>来源验证说明</strong><ul>{failure.diagnostics.map((message, index) => <li key={index}>{message}</li>)}</ul></div>}
      <div><strong>尝试历史</strong><ol>{failure.history.map(item => <li key={item.ordinal}>
        {item.ordinal === 0 ? "首次生成" : `${item.mode === "manual" ? "本次追加" : "自动修正"} ${item.ordinal}`} · {outcomes[item.state] || item.state}
        {item.ordinal > 0 && item.state === "failed" && ` · ${comparisons[item.comparison]}`}
      </li>)}</ol></div>
    </div>}
  </section>;
}
