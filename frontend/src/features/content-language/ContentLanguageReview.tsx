import { GenerationRetryStatus } from "../generation-retry/GenerationRetryStatus";
import { ManualExecutionRetry } from "../generation-retry/ManualExecutionRetry";
import { AutomaticRetryCount } from "../generation-retry/AutomaticRetryCount";
import { Button, ErrorNotice } from "../../components";
import { languageCheckPassed, languageCheckPending, type ContentLanguageStatus } from "./contracts";
import type { useContentLanguageCheck } from "./useContentLanguageCheck";
const labels: Record<string, string> = { required: "等待检查当前完整候选", spawn_intent: "语言检查已准备", queued: "语言检查已排队", running: "助手正在检查内容语言", validating: "正在验证语言检查结果", outcome_unknown: "原检查结果不确定，请核实同一任务", cancel_requested: "正在等待原检查结束", completed: "语言检查已完成", failed: "原语言检查执行失败", settled: "原语言检查已停止" };
export function ContentLanguageEvidence({ status }: { status?: ContentLanguageStatus | null }) {
  return <section aria-label="完整候选内容语言检查">
    <strong>{languageCheckPassed(status) ? "当前完整候选已通过助手语言检查" : status?.verdict === "reject" ? "当前候选存在内容语言问题，尚未采用" : status?.verdict === "uncertain" ? "助手无法确认当前内容语言，尚未采用" : status ? labels[status.state] : "当前完整候选尚未通过语言检查"}</strong>
    <p>结构交付完成与内容语言检查是不同结果。AI 语言检查可能遗漏问题；它不代表创作者确认、创作质量通过或媒体已接受。</p>
    {status?.checkJobId && !status.retry && <p>此检查未冻结自动重试额度；不会新增重试授权。</p>}
    <GenerationRetryStatus status={status?.retry} />
    {status?.blocker && !languageCheckPassed(status) && <p role="status">{status.blocker}</p>}
    {status?.findings?.map((finding, index) => <div role="alert" key={index}><p>{finding.explanation}</p><blockquote style={{ whiteSpace: "pre-wrap" }}>{finding.span.text}</blockquote><small>字段位置：{finding.span.path}；范围 {finding.span.start}–{finding.span.end}</small></div>)}
    {status?.issues?.map((issue, index) => <p key={index}>请按项目语言修正完整候选中的字段：{issue.fieldPaths.join("、")}。</p>)}
    {status && <details><summary>语言检查溯源与字段覆盖（技术详情）</summary><pre>{JSON.stringify(status, null, 2)}</pre></details>}
  </section>;
}
export function ContentLanguageReview({ check }: { check: ReturnType<typeof useContentLanguageCheck> }) {
  return <section className="content-language-review"><ContentLanguageEvidence status={check.status} />
    {check.edited && <p>完整候选已编辑，旧检查不再授权当前内容。请检查当前完整候选内容；检查不会自动翻译或确认采用。</p>}
    {!check.retryFrozen && <AutomaticRetryCount value={check.retryValue} onChange={check.setRetryValue} disabled={check.disabled || check.busy} />}
    {check.status?.checkJobId && !check.exact && !check.observeExisting && <p>已读取原候选的检查。请核对当前将提交的完整候选内容；不会因打开页面而提交任务。</p>}
    <Button disabled={check.disabled || check.busy || !check.retryValid} onClick={() => void check.check()}>{check.observeExisting ? "核对原语言检查" : "检查当前完整候选语言"}</Button>
    {check.canContinue && <Button disabled={check.disabled || check.busy} onClick={() => void check.continuePrepared()}>继续当前检查</Button>}
    {languageCheckPending(check.status) && <Button disabled={check.disabled || check.busy} onClick={() => void check.cancel()}>取消此语言检查</Button>}
    <ManualExecutionRetry identity={check.identity} status={check.status?.retry} disabled={check.disabled || check.busy} onRetry={check.retryManual} onObserve={check.observeCurrent} />
    {check.error && <ErrorNotice message={check.error} />}
  </section>;
}
