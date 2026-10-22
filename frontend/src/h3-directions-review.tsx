import { useEffect, useRef, useState } from "react";
import { plotloomApi } from "./api";
import type { H3PromptPreview, H3ReviewedDirections, VideoJobPrepareBody } from "./api";
import { Button } from "./components";

function newSeed(): number {
  const values = crypto.getRandomValues(new Uint32Array(2));
  return (values[0] & 0x1fffff) * 2 ** 32 + values[1];
}

function parseSeed(value: string): number | null {
  const seed = Number(value);
  return /^\d+$/.test(value) && Number.isSafeInteger(seed) && seed >= 0 ? seed : null;
}

export function H3DirectionsReview({ projectId, sourceIdentity, sourceReady, disabled, buildRequest, onFreeze, keyframeHash, endFrameHash, quality, requestedSeconds, frameCount }: {
  projectId: string;
  sourceIdentity: string;
  sourceReady: boolean;
  disabled: boolean;
  buildRequest: (seed: number, idempotencyKey: string) => VideoJobPrepareBody;
  onFreeze: (packageValue: H3ReviewedDirections, seed: number, idempotencyKey: string) => Promise<void>;
  keyframeHash: string;
  endFrameHash?: string | null;
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
  const [sourceReadRequired, setSourceReadRequired] = useState(true);
  const requestEpoch = useRef(0);
  const currentIdentity = useRef(`${projectId}:${sourceIdentity}`);
  const [seedText, setSeedText] = useState(() => String(newSeed()));
  const seed = parseSeed(seedText);
  const requestKey = useRef(crypto.randomUUID());
  currentIdentity.current = `${projectId}:${sourceIdentity}`;
  const available = useRef(sourceReady);
  available.current = sourceReady;

  useEffect(() => {
    setSources(null); setDrafts({}); setReviewed(false); setCompiled(""); setCompiledHash(""); setError(""); setBusy(false);
    setSeedText(String(newSeed()));
    requestKey.current = crypto.randomUUID();
    setSourceReadRequired(true);
    return () => { requestEpoch.current += 1; };
  }, [projectId, sourceIdentity]);

  useEffect(() => {
    if (sourceReady) return;
    // Unknown media withdraws authorization, not the creator's seed or buffer.
    // A fresh exact source hash must establish whether that buffer still fits.
    requestEpoch.current += 1;
    setReviewed(false); setCompiled(""); setCompiledHash(""); setBusy(false);
    setSourceReadRequired(true); setError("");
  }, [sourceReady]);

  const changeSeed = (value: string) => {
    // Seed participates in the source hash; old consent and idempotency cannot
    // authorize a different request, even when the English text is unchanged.
    requestEpoch.current += 1;
    requestKey.current = crypto.randomUUID();
    setSeedText(value); setSources(null); setDrafts({}); setReviewed(false);
    setCompiled(""); setCompiledHash(""); setError("");
    setSourceReadRequired(true);
  };

  const load = async () => {
    if (seed === null || !sourceReady || disabled || busy) return;
    const requestId = ++requestEpoch.current;
    const identity = currentIdentity.current;
    const owns = () => available.current && requestId === requestEpoch.current && identity === currentIdentity.current;
    setBusy(true); setError(""); setCompiled(""); setCompiledHash(""); setReviewed(false); setSourceReadRequired(true);
    try {
      const next = await plotloomApi.previewH3Prompt(projectId, buildRequest(seed, requestKey.current));
      if (!owns()) return;
      setDrafts((previous) => next.sourceHash === sources?.sourceHash
        ? previous
        : Object.fromEntries(next.sources.map((source) => [source.path, ""])));
      setSources(next);
      setSourceReadRequired(false);
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
    if (seed === null || !sourceReady || sourceReadRequired || disabled || busy) return;
    const requestId = ++requestEpoch.current;
    const identity = currentIdentity.current;
    const owns = () => available.current && requestId === requestEpoch.current && identity === currentIdentity.current;
    setBusy(true); setError(""); setCompiled(""); setCompiledHash("");
    try {
      const result = await plotloomApi.previewH3Prompt(projectId, {
        ...buildRequest(seed, requestKey.current), reviewedDirections: packageValue(),
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
    if (seed === null || !sourceReady || sourceReadRequired || disabled || busy || !sources || !reviewed || !compiledHash) return;
    const requestId = ++requestEpoch.current;
    const identity = currentIdentity.current;
    setBusy(true); setError("");
    try { await onFreeze({ ...packageValue(), promptSha256: compiledHash }, seed, requestKey.current); }
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
    <label className="h3-seed-field"><strong>H3 随机种子</strong>
      <input aria-label="H3 随机种子" type="text" inputMode="numeric" value={seedText}
        disabled={disabled || !sourceReady || busy} aria-invalid={seed === null}
        onChange={(event) => changeSeed(event.target.value)} />
      <small>默认随机。对照实验可填入旧原片的种子；修改后须重新读取来源、审阅并预览，不会自动提交或重试。</small>
      {seed === null && <small role="alert">请输入 0–9007199254740991 的十进制整数；不接受小数、指数或精度丢失。</small>}
    </label>
    <div className="h3-direction-actions"><Button disabled={disabled || !sourceReady || busy || seed === null} onClick={() => void load()}>读取当前来源</Button></div>
    {sources && sourceReadRequired && <small role="status">媒体来源需要重新核验；说明与种子已保留。请重新读取来源，再核对并预览。</small>}
    {sources && <>
      <small>来源绑定：{sources.sourceHash.slice(0, 12)}。改动分镜或审核选择后需重新读取。</small>
      {sources.sources.map((source) => <label className="h3-direction-field" key={source.path}>
        <strong>{source.label}</strong><small className="h3-direction-source">来源：{source.text}</small>
        <textarea value={drafts[source.path] ?? ""} disabled={disabled || !sourceReady || sourceReadRequired || busy}
          onChange={(event) => { setDrafts((value) => ({ ...value, [source.path]: event.target.value })); setCompiled(""); setCompiledHash(""); setReviewed(false); }}
          aria-label={`${source.label}的英文生成说明`} />
      </label>)}
      <label className="h3-direction-check"><input type="checkbox" checked={reviewed} disabled={disabled || !sourceReady || sourceReadRequired || busy}
        onChange={(event) => { setReviewed(event.target.checked); setCompiled(""); setCompiledHash(""); }} /><span>我已核对英文说明忠于来源；画面文字保持准确且不发声；声音补充已明确审阅</span></label>
      <div className="h3-direction-actions"><Button disabled={disabled || !sourceReady || sourceReadRequired || busy || !reviewed || sources.sources.some((source) => !drafts[source.path]?.trim())}
        onClick={() => void preview()}>预览完整 H3 提示词</Button></div>
      {compiled && <><pre className="video-prompt-preview">{compiled}</pre>
        <small data-testid="h3-frozen-review-inputs">本次冻结输入：质量 {quality}；请求 {requestedSeconds} 秒 / {frameCount} 帧；种子 {seed}；起始关键帧 SHA-256 {keyframeHash}；末帧 {endFrameHash ? `SHA-256 ${endFrameHash}` : "未使用"}。提示词 SHA-256 {compiledHash}。请求秒数不是最终播放时长。</small>
        <div className="h3-direction-actions"><Button disabled={disabled || !sourceReady || sourceReadRequired || busy} onClick={() => void freeze()}>冻结此说明并准备原片</Button></div></>}
    </>}
    {error && <small className="notice warning" role="alert">{error}</small>}
  </details>;
}
