import { useEffect, useRef, useState } from "react";
import { Button } from "../components";
import type { AcceptedOutlineRevision, AcceptedSectionMapRevision, SectionMap, SourceMapGraphAdmission, SourceTopology } from "../types";
import type { StoryRoute } from "../model";
import { useReviewEditorDraft } from "../features/authoring/ReviewDraftContext";
import { BranchSuggestionPanel } from "./BranchSuggestionPanel";
import { SourceStructureEditor } from "./SourceStructureEditor";
import { blankStructure, cloneMap, completeMap, mapsEqual } from "./sourceStructureModel";

export function SectionMapPanel({ projectId = "", structureKey = "", outline, outlineCurrent = true, accepted, status, staleReasons, graphAdmission, graphReady, sourceDirty, routes, readOnly, busy, onSave, onInstall, onContinue }: {
  projectId?: string; structureKey?: string; outline: AcceptedOutlineRevision | null; outlineCurrent?: boolean; accepted: AcceptedSectionMapRevision | null;
  status: "missing" | "current" | "stale"; staleReasons: string[]; graphAdmission: SourceMapGraphAdmission | null; graphReady: boolean;
  sourceDirty: boolean; routes: StoryRoute[]; readOnly: boolean; busy: boolean;
  onSave: (mapping: SectionMap) => void | Promise<boolean>; onInstall: () => void; onContinue: () => void;
}) {
  const [mapping, applyMapping] = useState<SectionMap>(() => cloneMap(accepted?.mapping));
  const [planned, setPlanned] = useState<SourceTopology>();
  const [hasDraft, setHasDraft] = useState(Boolean(accepted));
  const mappingDirty = useRef(false);
  const basis = outline ? `map:${outline.revision}:${outline.contentHash}:${accepted?.revision ?? 0}${structureKey}` : "";
  useEffect(() => { setPlanned(undefined); }, [basis]);
  const reviewDraft = useReviewEditorDraft(projectId, "section_map", basis, text => {
    const recovered = JSON.parse(text) as SectionMap;
    if (!Array.isArray(recovered.sections) || !recovered.choice && !recovered.topology) throw new Error("分支草稿格式无效，请复制后重新填写。");
    mappingDirty.current = true; setHasDraft(true); applyMapping(recovered);
  }, readOnly || busy, () => { mappingDirty.current = false; setHasDraft(Boolean(accepted)); applyMapping(cloneMap(accepted?.mapping)); });
  const setMapping = (next: SectionMap) => { mappingDirty.current = true; applyMapping(next); reviewDraft.changed(JSON.stringify(next)); };
  useEffect(() => { if (!mappingDirty.current) { applyMapping(cloneMap(accepted?.mapping)); setHasDraft(Boolean(accepted)); } }, [accepted?.revision]);
  const saveMapping = async () => {
    if (readOnly || busy || reviewDraft.stale || !outlineCurrent || sourceDirty) return;
    if (await onSave(mapping) === true) { mappingDirty.current = false; await reviewDraft.clear(); applyMapping(cloneMap(mapping)); }
  };
  const dirty = !mapsEqual(mapping, accepted?.mapping);
  const admissionMatches = Boolean(accepted && graphAdmission?.status === "current" && graphAdmission.sectionMapRevision === accepted.revision && graphAdmission.sectionMapContentHash === accepted.contentHash);
  const installed = status === "current" && admissionMatches && graphReady;
  const applied = installed && !dirty;
  const disabled = readOnly || busy || reviewDraft.stale || !outlineCurrent;
  const saveDisabled = disabled || sourceDirty || !completeMap(mapping) || Boolean(accepted && !dirty && status !== "stale");
  return <article className="panel section-map" data-testid="section-map">
    {reviewDraft.notice}
    <header><span>剧情分支与结局</span><strong>{status === "current" ? `当前 r${accepted?.revision}` : status === "stale" ? `需要重新检查 r${accepted?.revision}` : "尚未确认"}</strong></header>
    <p>观众在选择点为主角选择下一步；一条播放路线从开场走到一个结局。多条路线可以共享剧情或结局。结构按项目简报规划，内容须经你审阅确认。</p>
    {status === "stale" && <div className="notice warning">{staleReasons.join("；")}</div>}
    {!outline ? <p className="muted">先确认大纲，再准备完整分支建议。</p> : <>
      {projectId && <BranchSuggestionPanel projectId={projectId} basis={basis} disabled={disabled || sourceDirty} dirty={mappingDirty.current || reviewDraft.stale} onPlan={setPlanned} onAdopt={draft => { if (mappingDirty.current) return; setHasDraft(true); setMapping(draft); }} />}
      {planned && <Button variant="quiet" disabled={disabled || mappingDirty.current} onClick={() => { setHasDraft(true); setMapping(blankStructure(planned)); }}>自行填写当前结构草稿</Button>}
      {mappingDirty.current && <Button variant="quiet" disabled={readOnly || busy} onClick={async () => { if (await reviewDraft.clear()) { mappingDirty.current = false; applyMapping(cloneMap(accepted?.mapping)); setHasDraft(Boolean(accepted)); } }}>放弃本地草稿，保留已保存分支</Button>}
      {hasDraft && <>
        {!mapping.topology && <p className="action-prerequisite">这是保留的单选择、双结局版本。其内容与身份仍保留；新的建议按当前简报结构规划。</p>}
        <small className="required-legend">* 为必填项；身份与链接由系统管理。</small>
        <SourceStructureEditor mapping={mapping} disabled={disabled} onChange={setMapping} />
        <section className="section-map-actions" aria-label="剧情分支操作">
          <div className="section-map-action"><div><strong>{accepted ? "保存修改" : "确认并保存故事分支"}</strong><p>{!completeMap(mapping) ? "请填写每个节点、问题、选项与汇合衔接。" : !outlineCurrent ? "请先确认当前大纲或返回保留的有效版本。" : sourceDirty ? "请先保存来源修改。" : "确认保存当前审阅内容；随后单独应用到故事路线。"}</p></div><Button variant="primary" busy={busy} disabled={saveDisabled} onClick={() => void saveMapping()}>{busy ? "正在保存…" : accepted ? "保存修改" : "确认并保存故事分支"}</Button></div>
          {accepted && <div className="section-map-action"><div><strong>应用到故事路线</strong><p>{dirty ? "请先保存修改，才能应用故事路线。" : status !== "current" ? "请按当前简报与大纲重新审阅并保存。" : applied ? "当前故事路线已使用此版本。" : "应用已确认结构；不会自动生成后续内容或替换已安装投产。"}</p></div><Button variant="quiet" disabled={disabled || dirty || status !== "current" || applied} onClick={onInstall}>应用到故事路线</Button></div>}
          {installed && <div className="section-map-action section-map-action-ready" data-testid="section-map-ready"><div><strong>{dirty ? "故事分支有未保存修改" : "故事路线已就绪"}</strong><p>{dirty ? "请先保存故事分支修改。" : sourceDirty ? "请先保存故事内容。" : "下一步完善角色设定；切换页面不会生成内容。"}</p></div><Button variant="primary" disabled={disabled || dirty || sourceDirty || !applied} onClick={onContinue}>继续：角色设定</Button></div>}
        </section>
      </>}
      {graphAdmission && <small>故事路线 r{graphAdmission.graphRevision} · {graphAdmission.status === "current" ? "当前" : "需要重新检查"}</small>}
      {routes.length > 0 && <section className="section-map-routes" data-testid="section-map-route-cards"><strong>完整播放路线 · {routes.length} 条</strong>{routes.map((route, index) => <article key={route.id}><span>播放路线 {index + 1}</span><strong>{route.label}</strong><details><summary>技术详情：路线节点</summary><small>{route.nodeIds.join(" → ")}</small></details></article>)}</section>}
    </>}
  </article>;
}
