import { ApiError } from "../api-transport";
import { sourceWorkflowHref, workspaceHref } from "../app/workspace/sourceWorkflowNavigation";
import { ErrorNotice } from "../components";
import type { ReviewContextCode, ReviewContextDiagnostic, ReviewContextField } from "../review-context-types";

const messages: Record<ReviewContextCode, string> = {
  source_context_not_ready: "故事来源、大纲、章节分支或已应用路线尚未就绪。请先检查并确认这些内容，再回来准备任务。",
  installed_graph_not_current: "已应用的故事路线不是当前版本。请先检查并重新应用当前故事分支。",
  installed_graph_context_mismatch: "已应用的故事路线与当前来源或章节分支不一致。请先检查并重新应用当前故事分支。",
  accepted_cast_not_current: "角色设定尚未确认，或正在修改。请先保存并确认当前角色设定，再回来准备美术任务。",
  binding_revision_changed: "创作依据的版本已变化，需要重新检查这份设定。",
  binding_content_changed: "创作依据的内容已变化，需要重新检查这份设定。",
  section_context_changed: "故事章节或分支关系已变化，需要重新检查这份设定。",
  art_render_contract_changed: "美术风格或项目视觉方向已变化。请重新准备并确认美术设定；已有内容与图片仍保留。",
  cast_render_contract_changed: "角色风格或项目视觉方向需更新。请重新准备并确认角色设定；原设定与图片仍保留。",
};
const fieldLabels: Record<ReviewContextField, string> = {
  source_revision: "故事来源", source_content_hash: "故事来源",
  outline_revision: "已确认大纲", outline_content_hash: "已确认大纲",
  section_map_revision: "章节分支", section_map_content_hash: "章节分支",
  graph_revision: "已应用故事路线", graph_content_hash: "已应用故事路线",
  cast_revision: "角色设定", cast_content_hash: "角色设定",
};
const ownerLabels = { source: "来源与大纲", characters: "角色", art: "美术参考" } as const;

export function reviewContextMessage(diagnostic: ReviewContextDiagnostic): string {
  if (diagnostic.field && (diagnostic.code === "binding_revision_changed" || diagnostic.code === "binding_content_changed")) {
    return `${fieldLabels[diagnostic.field]}${diagnostic.code === "binding_revision_changed" ? "版本" : "内容"}已变化，需要重新检查这份设定。`;
  }
  return messages[diagnostic.code];
}

export function reviewContextNextStep(diagnostic: ReviewContextDiagnostic | undefined, fallback: string): string {
  // A changed binding means the upstream content exists but this review is old.
  // Sending the author back upstream cannot make that old binding current.
  if (diagnostic && ["binding_revision_changed", "binding_content_changed", "section_context_changed", "art_render_contract_changed", "cast_render_contract_changed"].includes(diagnostic.code)) return fallback;
  return diagnostic ? `请先到“${ownerLabels[diagnostic.owner]}”检查并确认当前内容，再回来继续。` : fallback;
}

/** The link opens separately: diagnostic reading cannot bypass the dirty-draft gate. */
export function ReviewContextNotice({ projectId, diagnostics, alert = false }: { projectId: string; diagnostics: ReviewContextDiagnostic[]; alert?: boolean }) {
  if (!diagnostics.length) return null;
  return <section className="notice warning review-context-notice" role={alert ? "alert" : "status"} aria-label="创作依据需要更新">
    <ul>{diagnostics.map((diagnostic, index) => <li key={`${diagnostic.code}:${diagnostic.field}:${index}`}>{reviewContextMessage(diagnostic)}</li>)}</ul>
    <div className="button-row">{[...new Set(diagnostics.map(item => item.owner))].map(owner => <a key={owner} className="button quiet" target="_blank" rel="noreferrer" href={owner === "characters" ? workspaceHref(projectId, owner) : sourceWorkflowHref(projectId, owner)}>在新页打开{ownerLabels[owner]}</a>)}</div>
    <details><summary>查看创作依据的技术详情</summary><ul>{diagnostics.map((diagnostic, index) => <li key={index}><code>{diagnostic.code}{diagnostic.field ? ` · ${diagnostic.field}` : ""}</code><p>{diagnostic.technicalMessage}</p></li>)}</ul></details>
  </section>;
}

export type ReviewContextFailure = string | ReviewContextDiagnostic;

export function reviewContextFailure(reason: unknown, fallback: string): ReviewContextFailure {
  if (reason instanceof ApiError && reason.status === 409 && reason.details && typeof reason.details === "object" && "code" in reason.details && reason.details.code === "review_context_not_current" && "diagnostic" in reason.details) {
    const diagnostic = reason.details.diagnostic;
    if (diagnostic && typeof diagnostic === "object" && "code" in diagnostic && typeof diagnostic.code === "string" && Object.hasOwn(messages, diagnostic.code) && "owner" in diagnostic && typeof diagnostic.owner === "string" && Object.hasOwn(ownerLabels, diagnostic.owner) && "technicalMessage" in diagnostic && typeof diagnostic.technicalMessage === "string" && "field" in diagnostic && (diagnostic.field === null || typeof diagnostic.field === "string" && Object.hasOwn(fieldLabels, diagnostic.field))) {
      return diagnostic as ReviewContextDiagnostic;
    }
  }
  return reason instanceof Error ? reason.message : fallback;
}

export function ReviewContextErrorNotice({ error, projectId }: { error: ReviewContextFailure; projectId: string }) {
  return typeof error === "string" ? <ErrorNotice message={error} /> : <ReviewContextNotice projectId={projectId} diagnostics={[error]} alert />;
}
