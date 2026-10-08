import { useEffect, useMemo, useRef, useState } from "react";

import { plotloomApi } from "../api";
import { Button, ErrorNotice } from "../components";
import { AssetZoomDialog, ManagedAssetImage, useBoundedAssetComparison } from "../features/media/references/AppearanceReviewPrimitives";
import type { ArtReferenceDecision, ArtReferenceDecisionState, ArtReferenceProposal } from "../types";
import { specialistsApi } from "../features/specialists/api";
import { reconcileFailedSend } from "../features/specialists/reconcileFailedSend";
import { ArtReferencePreparation } from "./ArtReferencePreparation";
import { artSubjects, defaultImageRequirements, record, studyStatus, subjectKey } from "./artReferencePresentation";
import { useExplicitReviewCloseGuard } from "../features/authoring/ReviewDraftContext";

type Candidate = ArtReferenceProposal["deliveries"][number]["candidates"][number] & {
  delivery: ArtReferenceProposal["deliveries"][number]; study: ArtReferenceProposal;
};
type RequirementDraft = { value: string; sourceStudyId?: string };

/**
 * F3B stays in the existing ArtPanel. This is only its image-first review
 * presentation; accepted art, F3B proposals, and managed assets retain ownership.
 */
export function ArtReferenceGallery({ projectId, art, acceptedRevision, acceptedContentHash, acceptedArtCurrent, studies, decisions, decisionStates, readOnly, busy, setAssignment, refresh, createReferenceDecision, onReferenceDecisionCreated, showStudyActions = true, assetUrl }: {
  projectId: string; art: Record<string, unknown>; acceptedRevision: number; acceptedContentHash: string;
  acceptedArtCurrent: boolean;
  studies: ArtReferenceProposal[]; decisions: ArtReferenceDecision[]; decisionStates: ArtReferenceDecisionState[];
  readOnly: boolean; busy: boolean; setAssignment: (value: string) => void;
  refresh: () => Promise<void>;
  createReferenceDecision?: (body: { subjectType: "scene" | "prop"; subjectId: string; assetId: string; expectedReferenceRevision: number }) => Promise<ArtReferenceDecision>;
  onReferenceDecisionCreated?: (decision: ArtReferenceDecision) => void;
  showStudyActions?: boolean;
  assetUrl?: (assetId: string) => string;
}) {
  const [selectedSubjectKey, setSelectedSubjectKey] = useState("");
  const [error, setError] = useState("");
  const sessionKey = `${projectId}:${acceptedRevision}:${acceptedContentHash}`;
  const [drafts, setDrafts] = useState<{ session: string; values: Record<string, RequirementDraft> }>({ session: sessionKey, values: {} });
  if (drafts.session !== sessionKey) setDrafts({ session: sessionKey, values: {} });
  const activeSession = useRef({ key: sessionKey, epoch: 0 });
  if (activeSession.current.key !== sessionKey) activeSession.current = { key: sessionKey, epoch: activeSession.current.epoch + 1 };
  const ownsSession = (session: { key: string; epoch: number }) => activeSession.current === session;
  const [busySession, setBusySession] = useState<{ key: string; epoch: number }>();
  const studyBusy = busy || busySession === activeSession.current;
  const requirementsDirty = drafts.session === sessionKey && Object.entries(drafts.values).some(([key, draft]) => {
    const latest = studies.find(study => `${study.subjectType}:${study.subjectId}` === key && study.current);
    return record(latest?.request.frozenSnapshot).renderDirection !== draft.value;
  });
  useExplicitReviewCloseGuard(projectId, "art_reference_requirements", requirementsDirty, busySession === activeSession.current,
    () => setDrafts({ session: sessionKey, values: {} }), "环境与道具的图片任务要求");
  const subjects = useMemo(() => artSubjects(art), [art]);
  useEffect(() => {
    if (subjects.length && !subjects.some((subject) => subjectKey(subject) === selectedSubjectKey)) setSelectedSubjectKey(subjectKey(subjects[0]!));
  }, [selectedSubjectKey, subjects]);
  useEffect(() => {
    const session = activeSession.current;
    return () => { if (ownsSession(session)) activeSession.current = { key: session.key, epoch: session.epoch + 1 }; };
  }, [sessionKey]);
  const selected = subjects.find((subject) => subjectKey(subject) === selectedSubjectKey) || subjects[0];
  const subjectStudies = selected ? studies.filter((item) => item.subjectType === selected.subjectType && item.subjectId === selected.subjectId) : [];
  const study = subjectStudies[0];
  const demonstration = study && typeof study.request.demonstration === "string" ? study.request.demonstration : "";
  const candidates = subjectStudies.flatMap((item) => item.deliveries.flatMap((delivery) => delivery.candidates.map((candidate) => ({ ...candidate, delivery, study: item }))));
  const viewableCandidates = candidates.filter((candidate) => candidate.asset);
  const [viewedAssetId, setViewedAssetId] = useState("");
  const [expanded, setExpanded] = useState(false);
  const viewed = viewableCandidates.find((candidate) => candidate.assetId === viewedAssetId) || viewableCandidates[0];
  const decisionState = selected ? decisionStates.find((item) => item.subjectType === selected.subjectType && item.subjectId === selected.subjectId) : undefined;
  const currentDecision = selected ? decisions.find((item) => item.current && item.subjectType === selected.subjectType && item.subjectId === selected.subjectId) : undefined;
  const latestDecision = selected ? decisions.find((item) => item.subjectType === selected.subjectType && item.subjectId === selected.subjectId) : undefined;
  const { comparisonCandidates, comparisonAssetIds, comparisonAtCapacity, toggleComparison, clearComparison } = useBoundedAssetComparison(viewableCandidates);
  const act = async <Result,>(operation: (isCurrent: () => boolean) => Promise<Result>, onSuccess?: (result: Result) => void) => {
    const session = activeSession.current;
    setBusySession(session); setError("");
    try {
      const result = await operation(() => ownsSession(session));
      if (!ownsSession(session)) return;
      onSuccess?.(result);
      await refresh();
    } catch (reason) {
      if (ownsSession(session)) setError(reason instanceof Error ? reason.message : "环境/道具参考操作失败。");
    } finally {
      if (ownsSession(session)) setBusySession(undefined);
    }
  };

  if (!selected) return <section className="art-reference-studies art-reference-gallery" data-testid="art-reference-studies"><strong>尚无可审阅的环境或道具</strong><p>先接受包含稳定 scene/prop ID 的 art.json；这里不会猜测或创建主体。</p></section>;
  const status = studyStatus(study);
  const draft = drafts.session === sessionKey ? drafts.values[subjectKey(selected)] : undefined;
  const direction = draft?.value ?? defaultImageRequirements(art.style, selected.subjectType);
  const revising = Boolean(study?.current && study.state === "delivered" && draft?.sourceStudyId === study.id);
  const setDraft = (value: RequirementDraft) => setDrafts((previous) => ({ session: sessionKey, values: { ...(previous.session === sessionKey ? previous.values : {}), [subjectKey(selected)]: value } }));
  const setDirection = (value: string) => setDraft({ value, sourceStudyId: revising ? study?.id : undefined });
  const startRevision = () => {
    if (!study?.current || study.state !== "delivered") return;
    const frozenDirection = record(study.request.frozenSnapshot).renderDirection;
    setDraft({ value: typeof frozenDirection === "string" ? frozenDirection : defaultImageRequirements(art.style, selected.subjectType), sourceStudyId: study.id });
    setError("");
  };
  const actionable = !readOnly && !studyBusy;
  // Retained Art is readable, but only its current confirmed head can authorize
  // generation or selection. Task cancellation and late delivery checks differ.
  const generationActionable = actionable && acceptedArtCurrent;
  const chooseLabel = selected.subjectType === "scene" ? "这张环境参考图" : "这张道具参考图";
  const candidateIsCurrent = Boolean(viewed?.study.current && viewed.delivery.state === "accepted");
  const candidateAlreadyChosen = currentDecision?.assetId === viewed?.assetId;
  return <section className="art-reference-studies art-reference-gallery" data-testid="art-reference-studies">
    <header><div><span>环境 / 道具参考图片</span><strong>{acceptedArtCurrent ? "按已确认的美术设定生成图片" : "查看保留的参考图片"}</strong></div><small>不会修改已确认的美术设定。</small></header>
    <p>{acceptedArtCurrent ? "先选择环境或道具，再准备图片任务。这里选用的图片仅供参考，不会自动用于镜头或生产。" : "当前美术设定尚未重新确认，暂不能准备、发送或选用参考图。已有图片和任务记录仍可查看。"}</p>
    {demonstration && <p className="reference-demonstration" role="note"><strong>演示声明：</strong>{demonstration}。不代表真实交付、生成或创意批准。</p>}
    <nav className="reference-subjects" aria-label="环境和道具主体"><span>{acceptedArtCurrent ? "当前美术主体" : "保留的美术主体"}</span>{subjects.map((subject) => <button key={subjectKey(subject)} type="button" className={subjectKey(subject) === subjectKey(selected) ? "selected" : ""} aria-pressed={subjectKey(subject) === subjectKey(selected)} onClick={() => { setSelectedSubjectKey(subjectKey(subject)); setViewedAssetId(""); clearComparison(); }}><strong>{subject.subjectType === "scene" ? "环境" : "道具"} · {subject.name}</strong><small>{subject.subjectId}</small></button>)}</nav>
    <section className="appearance-workspace" aria-label={`${selected.name} 的环境或道具参考工作区`} data-testid={`art-reference-${selected.subjectType}-${selected.subjectId}`}>
      <div className="appearance-viewer">
        <div className="appearance-viewer-heading"><div><span className="eyebrow">当前查看</span><strong>{selected.subjectType === "scene" ? "环境" : "道具"} · {selected.name}</strong></div><span className={study?.current ? "reference-state selected" : "reference-state historical"}>{status}</span></div>
        {viewed ? <ManagedAssetImage projectId={projectId} subjectId={subjectKey(selected)} asset={viewed.asset} assetId={viewed.assetId} alt={`${selected.name} 当前查看图片`} unavailableLabel="当前查看图片不可用" imageUrl={assetUrl?.(viewed.assetId)} onZoom={() => setExpanded(true)} /> : <div className="reference-no-image"><strong>尚无可显示的候选图片</strong><p>{study ? "本次任务尚无可查看的图片。" : "尚未为此环境或道具准备图片任务。"}</p></div>}
        <div className="button-row">{viewed && <Button variant="primary" disabled={!generationActionable || !candidateIsCurrent || candidateAlreadyChosen} onClick={() => void act(() => (createReferenceDecision || ((body) => plotloomApi.createArtReferenceDecision(projectId, body)))({ subjectType: selected.subjectType, subjectId: selected.subjectId, assetId: viewed.assetId, expectedReferenceRevision: decisionState?.revision || 0 }), onReferenceDecisionCreated)}>{candidateAlreadyChosen ? `已选用${chooseLabel}` : `${currentDecision ? "改用" : "选用"}${chooseLabel}`}</Button>}</div>
        {currentDecision && <><p className="reference-decision" role="status"><strong>当前参考图：</strong>{currentDecision.assetId === viewed?.assetId ? "正在查看的候选。" : "在另一张候选中。"}</p><ReferenceDecisionDetails decision={currentDecision} /></>}
        {!currentDecision && latestDecision && <p className="reference-decision stale" role="status">此前的参考决定已过期；保留在历史中，尚未为当前美术主体自动选择候选。</p>}
        <p className="reference-decision-boundary">这里的参考图选择仅用于环境/道具审阅，暂不会传入镜头制作流程。</p>
        {viewed && <CandidateDetails candidate={viewed} study={viewed.study} />}
      </div>
      <div className="appearance-thumbnails" aria-label="同一主体的已有图片">
        {viewableCandidates.map((candidate) => <button key={candidate.id} type="button" className={`appearance-thumbnail${candidate.assetId === viewed?.assetId ? " viewing" : ""}${currentDecision?.assetId === candidate.assetId ? " selected" : ""}`} aria-pressed={candidate.assetId === viewed?.assetId} onClick={() => setViewedAssetId(candidate.assetId)}><ManagedAssetImage projectId={projectId} subjectId={subjectKey(selected)} asset={candidate.asset} assetId={candidate.assetId} alt={`${candidate.outputFilename} 缩略图`} unavailableLabel="候选图片不可用" imageUrl={assetUrl?.(candidate.assetId)} /><span>{candidate.outputFilename}</span>{currentDecision?.assetId === candidate.assetId && <strong className="reference-current-image">当前参考图</strong>}</button>)}
        {candidates.filter((candidate) => !candidate.asset).map((candidate) => <div className="appearance-thumbnail" key={candidate.id}><ManagedAssetImage projectId={projectId} subjectId={subjectKey(selected)} asset={candidate.asset} assetId={candidate.assetId} alt="候选图片不可用" unavailableLabel="候选图片不可用" /><span>{candidate.outputFilename}</span></div>)}
      </div>
      {viewableCandidates.length > 1 && <div className="appearance-compare-controls" aria-label="同一主体图片比较"><span>比较（已选 {comparisonCandidates.length}/4；至少选择 2 张）</span>{viewableCandidates.map((candidate) => { const compared = comparisonAssetIds.includes(candidate.assetId); return <Button key={candidate.id} variant="quiet" aria-pressed={compared} className="selection-toggle" disabled={!compared && comparisonAtCapacity} onClick={() => toggleComparison(candidate.assetId)}>{compared ? `移出 ${candidate.outputFilename}` : `加入 ${candidate.outputFilename}`}</Button>; })}{comparisonCandidates.length > 0 && <Button variant="quiet" onClick={clearComparison}>清空比较</Button>}{comparisonAtCapacity && <small>已达四张上限；先移出一张再替换。</small>}</div>}
      {comparisonCandidates.length >= 2 && <div className={`appearance-compare comparison-count-${comparisonCandidates.length}`} data-testid="art-reference-comparison"><header><strong>并排比较 · {comparisonCandidates.length} 张</strong><small>仅比较 {selected.subjectType === "scene" ? "环境" : "道具"} {selected.name}；不会选择生产资产。</small></header>{comparisonCandidates.map((candidate) => <figure key={candidate.assetId}><figcaption>{candidate.assetId === viewed?.assetId ? "当前查看" : "对比图片"} · {candidate.outputFilename}</figcaption><ManagedAssetImage projectId={projectId} subjectId={subjectKey(selected)} asset={candidate.asset} assetId={candidate.assetId} alt={`${candidate.outputFilename} 比较图片`} unavailableLabel="对比图片不可用" imageUrl={assetUrl?.(candidate.assetId)} /></figure>)}</div>}
      {showStudyActions && <ArtReferencePreparation style={art.style} subject={selected} study={study} actionable={actionable} generationActionable={generationActionable} direction={direction} onDirectionChange={setDirection}
        revising={revising} onRevise={startRevision} onCancelRevision={() => setDraft({ value: direction })}
        onPrepare={() => void act(() => plotloomApi.prepareArtReferenceProposal(projectId, { subjectType: selected.subjectType, subjectId: selected.subjectId, renderDirection: direction.trim() }))}
        onSend={() => study && void act((isCurrent) => reconcileFailedSend(() => specialistsApi.sendArtImage(projectId, study.id), async () => { if (isCurrent()) await refresh(); }))}
        onRefresh={() => study && void act(() => plotloomApi.refreshArtReferenceProposal(projectId, study.id))}
        onCancel={() => study && void act(() => plotloomApi.cancelArtReferenceProposal(projectId, study.id, "Operator cancelled the F3B reference-study handoff."))}
      />}
      {error && <ErrorNotice message={error} />}
    </section>
    {viewed && <AssetZoomDialog open={expanded} onClose={() => setExpanded(false)} label="放大查看环境或道具图片"><ManagedAssetImage projectId={projectId} subjectId={subjectKey(selected)} asset={viewed.asset} assetId={viewed.assetId} alt={`${selected.name} 放大图片`} unavailableLabel="当前查看图片不可用" imageUrl={assetUrl?.(viewed.assetId)} /></AssetZoomDialog>}
  </section>;
}

function ReferenceDecisionDetails({ decision }: { decision: ArtReferenceDecision }) {
  return <details className="reference-technical reference-decision-technical"><summary>参考决定技术详情</summary><dl><div><dt>参考版本</dt><dd>r{decision.referenceRevision}</dd></div><div><dt>决定</dt><dd>{decision.id}</dd></div><div><dt>资产</dt><dd>{decision.assetId}</dd></div></dl></details>;
}

function CandidateDetails({ candidate, study }: { candidate: Candidate; study: ArtReferenceProposal }) {
  return <details className="reference-technical"><summary>查看候选来源与技术详情</summary><dl><div><dt>主体</dt><dd>{study.subjectType}:{study.subjectId}</dd></div><div><dt>提案</dt><dd>{study.id}</dd></div><div><dt>交付</dt><dd>{candidate.delivery.deliveryId || candidate.delivery.state}</dd></div><div><dt>资产</dt><dd>{candidate.assetId}</dd></div><div><dt>输出标识</dt><dd>{candidate.outputHash}</dd></div><div><dt>来源</dt><dd>{candidate.asset?.provenance?.origin || "来源信息不可用"}</dd></div><div><dt>权利</dt><dd>{candidate.asset?.provenance?.rights || "权利信息不可用"}</dd></div><div><dt>尺寸</dt><dd>{candidate.asset ? `${candidate.asset.width} × ${candidate.asset.height}` : "资产不可用"}</dd></div></dl></details>;
}
