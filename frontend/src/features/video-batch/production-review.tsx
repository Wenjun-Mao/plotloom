import type { Batch, ProductionBrief, Target } from "./contracts";

export const batchStateLabels: Record<string, string> = {
  setup: "制作清单已准备", drafting: "助手正在起草供应商指令", checking: "独立助手正在检查指令保真性",
  translation_rejected: "指令保真检查未通过，尚未发送视频", ready: "请审阅完整制作简报并授权生成",
  running: "正在制作视频", paused: "已暂停新派发", cancelled: "已取消新派发", blocked: "需要处理原任务",
  stale: "来源已变化，未发送工作已暂停", awaiting_review: "视频已返回，等待选择播放片段", approved: "视频已保存片段选择",
};
const sectionIds = ["shot", "context", "presentation", "references", "timing", "settings"];
export function reviewableBrief(brief: ProductionBrief | null | undefined): boolean {
  return !!brief && brief.version === "plotloom.production-brief.v2" && brief.displayVersion === "plotloom.production-brief-display.v2" && ["zh-CN", "en-US"].includes(brief.contentLocale)
    && /^[a-f0-9]{64}$/.test(brief.briefHash) && /^[a-f0-9]{64}$/.test(brief.sourceHash)
    && sectionIds.every(id => brief.sections.some(section => section.id === id && !!section.items?.length))
    && brief.conflicts.length === 0;
}
export function canAuthorizeBatch(batch: Batch): boolean {
  return batch.state === "ready" && !batch.manifest.blockers.length && batch.manifest.targets.every(target =>
    target.mode !== "generate" || reviewableBrief(target.productionBrief) && target.productionBrief?.sourceHash === target.sourceHash
      && target.fidelity?.verdict === "pass" && !!target.directions?.fidelityCheck && !!target.compiledPrompt);
}

export function ProductionBriefReview({ target }: { target: Target }) {
  const brief = target.productionBrief;
  return <section className="production-brief-review" aria-label={`${target.title}的完整制作简报`}>
    <h4>{target.title} · {target.shotId}</h4>
    {brief ? <>
      {brief.sections.map(section => <section key={section.id}><h5>{section.label}</h5>
        {section.items?.length ? <dl>{section.items.map((item, index) => <div key={index}><dt>{item.label}</dt><dd style={{ whiteSpace: "pre-wrap" }}>{item.value}</dd></div>)}</dl>
          : <p role="status">此版本尚未提供可读的完整制作简报，不能据此授权新的生成。</p>}
      </section>)}
      <p>{brief.discretion}</p><ul>{brief.adapterConstraints.map((constraint, index) => <li key={index}>{constraint}</li>)}</ul>
      {brief.conflicts.map((conflict, index) => <p role="alert" key={index}>{conflict.message}<small>来源位置：{conflict.path}{conflict.owner ? `；修改位置：${conflict.owner}` : ""}</small></p>)}
    </> : <p>此保留任务没有新版制作简报；原媒体与原始证据仍保留。</p>}
    <FidelityReview target={target} />
    <details><summary>来源、完整供应商指令与检查记录（技术详情）</summary>
      <p>以下保留实际原文；助手检查不代表创作者亲自审阅英文，也不代表生成视频已被接受。</p>
      <pre>{target.compiledPrompt || "尚无完整供应商指令。"}</pre>
      <pre>{JSON.stringify({ sourceHash: target.sourceHash, brief, directions: target.directions, fidelity: target.fidelity }, null, 2)}</pre>
    </details>
  </section>;
}

export function FidelityReview({ target }: { target: Target }) {
  const check = target.fidelity, reference = target.directions?.fidelityCheck;
  return <section aria-label="助手指令保真检查">
    <p>{check?.verdict === "pass" && reference ? "独立助手保真检查已通过；尚需授权生成，视频返回后可选择技术有效的片段；音画质量观察为可选。"
      : check?.verdict === "reject" ? "助手发现以下语义问题，请回到创作来源或修正供应商候选；未通过前不能生成视频。"
      : "尚无当前候选的独立助手检查通过记录。"}</p>
    {check?.findings.map((finding, index) => <p role="alert" key={index}>{finding.message}<small>来源位置：{finding.sourcePath || finding.path}{finding.sourceOwner ? `；修改位置：${finding.sourceOwner}` : ""}</small></p>)}
    {reference && <details><summary>助手检查溯源</summary><p>检查执行：{reference.attemptId}；结果标识：{reference.resultHash}</p></details>}
    <small>AI 语义检查可能遗漏问题；不替代创作者对完整制作意图的判断；后续媒体质量观察为可选。</small>
  </section>;
}
