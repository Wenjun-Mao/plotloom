import { useEffect, useRef, useState } from "react";
import { plotloomApi } from "./api";
import type { H3PromptPreview, H3ReviewedDirections, VideoJobPrepareBody } from "./api";
import { Button } from "./components";

function newSeed(): number {
  const values = crypto.getRandomValues(new Uint32Array(2));
  return (values[0] & 0x1fffff) * 2 ** 32 + values[1];
}

export function H3DirectionsReview({ projectId, sourceIdentity, disabled, buildRequest, onFreeze, keyframeHash, quality, requestedSeconds, frameCount }: {
  projectId: string;
  sourceIdentity: string;
  disabled: boolean;
  buildRequest: (seed: number, idempotencyKey: string) => VideoJobPrepareBody;
  onFreeze: (packageValue: H3ReviewedDirections, seed: number, idempotencyKey: string) => Promise<void>;
  keyframeHash: string;
  quality: number;
  requestedSeconds: number;
  frameCount: number;
}) {
  const [sources, setSources] = useState<H3PromptPreview | null>(null);
  const [drafts, setDrafts] = useState<Record<string, string>>({});
  const [reviewed, setReviewed] = useState(false);
  const [compiled, setCompiled] = useState("");
  const [compiledHash, setCompiledHash] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const requestEpoch = useRef(0);
  const currentIdentity = useRef(`${projectId}:${sourceIdentity}`);
  const frozenSeed = useRef(newSeed());
  const requestKey = useRef(crypto.randomUUID());
  currentIdentity.current = `${projectId}:${sourceIdentity}`;

  useEffect(() => {
    setSources(null); setDrafts({}); setReviewed(false); setCompiled(""); setCompiledHash(""); setError(""); setBusy(false);
    frozenSeed.current = newSeed();
    requestKey.current = crypto.randomUUID();
    return () => { requestEpoch.current += 1; };
  }, [projectId, sourceIdentity]);

  const load = async () => {
    const requestId = ++requestEpoch.current;
    const identity = currentIdentity.current;
    const owns = () => requestId === requestEpoch.current && identity === currentIdentity.current;
    setBusy(true); setError(""); setCompiled(""); setCompiledHash("");
    try {
      const next = await plotloomApi.previewH3Prompt(projectId, buildRequest(frozenSeed.current, requestKey.current));
      if (!owns()) return;
      setDrafts((previous) => next.sourceHash === sources?.sourceHash
        ? previous
        : Object.fromEntries(next.sources.map((source) => [source.path, ""])));
      setSources(next);
      setReviewed(false);
    } catch (reason) { if (owns()) setError(reason instanceof Error ? reason.message : "无法读取提示词来源"); }
    finally { if (owns()) setBusy(false); }
  };

  const packageValue = (): H3ReviewedDirections => ({
    sourceHash: sources?.sourceHash ?? "",
    fields: (sources?.sources ?? []).map((source) => ({ path: source.path, english: drafts[source.path] ?? "" })),
    reviewedEnglish: true,
  });

  const preview = async () => {
    const requestId = ++requestEpoch.current;
    const identity = currentIdentity.current;
    const owns = () => requestId === requestEpoch.current && identity === currentIdentity.current;
    setBusy(true); setError(""); setCompiled(""); setCompiledHash("");
    try {
      const result = await plotloomApi.previewH3Prompt(projectId, {
        ...buildRequest(frozenSeed.current, requestKey.current), reviewedDirections: packageValue(),
      });
      if (!owns()) return;
      if (result.sourceHash !== sources?.sourceHash || !result.compiledPrompt || !result.compiledPromptSha256) {
        throw new Error("来源已变化，请重新读取并审阅。");
      }
      setCompiled(result.compiledPrompt);
      setCompiledHash(result.compiledPromptSha256);
    } catch (reason) { if (owns()) setError(reason instanceof Error ? reason.message : "无法预览最终提示词"); }
    finally { if (owns()) setBusy(false); }
  };

  const freeze = async () => {
    const requestId = ++requestEpoch.current;
    const identity = currentIdentity.current;
    setBusy(true); setError("");
    try { await onFreeze({ ...packageValue(), promptSha256: compiledHash }, frozenSeed.current, requestKey.current); }
    catch (reason) {
      if (requestId === requestEpoch.current && identity === currentIdentity.current) {
        setError(reason instanceof Error ? reason.message : "无法冻结英文说明");
      }
    } finally {
      if (requestId === requestEpoch.current && identity === currentIdentity.current) setBusy(false);
    }
  };

  return <details className="video-technical-history h3-directions-review" data-testid="h3-directions-review">
    <summary>审阅英文生成说明</summary>
    <p>故事原文不变。请根据每项来源写英文生成说明；对白会由系统保留原文并放入对白区。可请助手起草，再检查动作、物体、位置和声音是否准确。</p>
    <div className="h3-direction-actions"><Button disabled={disabled || busy} onClick={() => void load()}>读取当前来源</Button></div>
    {sources && <>
      <small>来源绑定：{sources.sourceHash.slice(0, 12)}。改动分镜或审核选择后需重新读取。</small>
      {sources.sources.map((source) => <label className="h3-direction-field" key={source.path}>
        <strong>{source.label}</strong><small className="h3-direction-source">来源：{source.text}</small>
        <textarea value={drafts[source.path] ?? ""} disabled={disabled || busy}
          onChange={(event) => { setDrafts((value) => ({ ...value, [source.path]: event.target.value })); setCompiled(""); setCompiledHash(""); setReviewed(false); }}
          aria-label={`${source.label}的英文生成说明`} />
      </label>)}
      <label className="h3-direction-check"><input type="checkbox" checked={reviewed} disabled={disabled || busy}
        onChange={(event) => { setReviewed(event.target.checked); setCompiled(""); setCompiledHash(""); }} /><span>我已核对英文说明忠于来源；声音补充已明确审阅</span></label>
      <div className="h3-direction-actions"><Button disabled={disabled || busy || !reviewed || sources.sources.some((source) => !drafts[source.path]?.trim())}
        onClick={() => void preview()}>预览完整 H3 提示词</Button></div>
      {compiled && <><pre className="video-prompt-preview">{compiled}</pre>
        <small data-testid="h3-frozen-review-inputs">本次冻结输入：质量 {quality}；请求 {requestedSeconds} 秒 / {frameCount} 帧；种子 {frozenSeed.current}；起始关键帧 SHA-256 {keyframeHash}。提示词 SHA-256 {compiledHash}。请求秒数不是最终播放时长。</small>
        <div className="h3-direction-actions"><Button disabled={disabled || busy} onClick={() => void freeze()}>冻结此说明并准备原片</Button></div></>}
    </>}
    {error && <small className="notice warning" role="alert">{error}</small>}
  </details>;
}
