import { useEffect, useMemo, useRef, useState } from "react";

import { plotloomApi } from "../api";
import { Button, ErrorNotice } from "../components";
import { AssetZoomDialog, ManagedAssetImage, useBoundedAssetComparison } from "../features/media/references/AppearanceReviewPrimitives";
import type { ArtReferenceDecision, ArtReferenceDecisionState, ArtReferenceProposal } from "../types";

type Subject = { subjectType: "scene" | "prop"; subjectId: string; name: string };
type Candidate = ArtReferenceProposal["deliveries"][number]["candidates"][number] & {
  delivery: ArtReferenceProposal["deliveries"][number]; study: ArtReferenceProposal;
};

/**
 * F3B stays in the existing ArtPanel. This is only its image-first review
 * presentation; accepted art, F3B proposals, and managed assets retain ownership.
 */
export function ArtReferenceGallery({ projectId, art, acceptedRevision, acceptedContentHash, studies, decisions, decisionStates, readOnly, busy, setAssignment, refresh }: {
  projectId: string; art: Record<string, unknown>; acceptedRevision: number; acceptedContentHash: string;
  studies: ArtReferenceProposal[]; decisions: ArtReferenceDecision[]; decisionStates: ArtReferenceDecisionState[];
  readOnly: boolean; busy: boolean; setAssignment: (value: string) => void;
  refresh: () => Promise<void>;
}) {
  const [direction, setDirection] = useState("Cinematic realism: grounded materials, natural lens behavior, no people or hands unless the accepted subject explicitly requires them.");
  const [selectedSubjectKey, setSelectedSubjectKey] = useState("");
  const [error, setError] = useState("");
  const sessionKey = `${projectId}:${acceptedRevision}:${acceptedContentHash}`;
  const activeSession = useRef({ key: sessionKey, epoch: 0 });
  if (activeSession.current.key !== sessionKey) activeSession.current = { key: sessionKey, epoch: activeSession.current.epoch + 1 };
  const ownsSession = (session: { key: string; epoch: number }) => activeSession.current === session;
  const [busySession, setBusySession] = useState<{ key: string; epoch: number }>();
  const studyBusy = busy || busySession === activeSession.current;
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
  const act = async <Result,>(operation: () => Promise<Result>, onSuccess?: (result: Result) => void) => {
    const session = activeSession.current;
    setBusySession(session); setError("");
    try {
      const result = await operation();
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
  const actionable = !readOnly && !studyBusy;
  const chooseLabel = selected.subjectType === "scene" ? "用作此环境的参考图" : "用作此道具的参考图";
  const candidateIsCurrent = Boolean(viewed?.study.current && viewed.delivery.state === "accepted");
  const candidateAlreadyChosen = currentDecision?.assetId === viewed?.assetId;
  return <section className="art-reference-studies art-reference-gallery" data-testid="art-reference-studies">
    <header><div><span>F3B · 环境 / 道具参考研究</span><strong>已接受美术 → 探索候选</strong></div><small>不会选择生产资产，也不会生成或修改 art.json。</small></header>
    <p>只比较同一稳定主体的现有候选。候选可供审阅，不能成为镜头、生产选择或新的调整父项。</p>
    {demonstration && <p className="reference-demonstration" role="note"><strong>演示声明：</strong>{demonstration}。不代表真实交付、生成或创意批准。</p>}
    <nav className="reference-subjects" aria-label="环境和道具主体"><span>当前美术主体</span>{subjects.map((subject) => <button key={subjectKey(subject)} type="button" className={subjectKey(subject) === subjectKey(selected) ? "selected" : ""} aria-pressed={subjectKey(subject) === subjectKey(selected)} onClick={() => { setSelectedSubjectKey(subjectKey(subject)); setViewedAssetId(""); clearComparison(); }}><strong>{subject.subjectType === "scene" ? "环境" : "道具"} · {subject.name}</strong><small>{subject.subjectId}</small></button>)}</nav>
    <section className="appearance-workspace" aria-label={`${selected.name} 的环境或道具参考工作区`} data-testid={`art-reference-${selected.subjectType}-${selected.subjectId}`}>
      <div className="appearance-viewer">
        <div className="appearance-viewer-heading"><div><span className="eyebrow">当前查看</span><strong>{selected.subjectType === "scene" ? "环境" : "道具"} · {selected.name}</strong></div><span className={study?.current ? "reference-state selected" : "reference-state historical"}>{status}</span></div>
        {viewed ? <ManagedAssetImage projectId={projectId} subjectId={subjectKey(selected)} asset={viewed.asset} assetId={viewed.assetId} alt={`${selected.name} 当前查看图片`} unavailableLabel="当前查看图片不可用" /> : <div className="reference-no-image"><strong>尚无可显示的候选图片</strong><p>{study ? "交付尚未提供可浏览的候选；保留其真实状态。" : "尚未准备此主体的参考研究。"}</p></div>}
        <div className="button-row"><Button variant="quiet" disabled={!viewed} onClick={() => setExpanded(true)}>放大查看</Button>{viewed && <Button variant="primary" disabled={!actionable || !candidateIsCurrent || candidateAlreadyChosen} onClick={() => void act(() => plotloomApi.createArtReferenceDecision(projectId, { subjectType: selected.subjectType, subjectId: selected.subjectId, assetId: viewed.assetId, expectedReferenceRevision: decisionState?.revision || 0 }))}>{currentDecision ? `替换为${chooseLabel}` : chooseLabel}</Button>}</div>
        {currentDecision && <p className="reference-decision" role="status">当前已选参考：{currentDecision.assetId === viewed?.assetId ? "正在查看的候选" : currentDecision.assetId}（r{currentDecision.referenceRevision}）。</p>}
        {!currentDecision && latestDecision && <p className="reference-decision stale" role="status">此前的参考决定已过期；保留在历史中，尚未为当前美术主体自动选择候选。</p>}
        <p className="reference-decision-boundary">此决定目前仅供环境/道具参考审阅；尚未被镜头或生产流程消费。</p>
        {viewed && <CandidateDetails candidate={viewed} study={viewed.study} />}
      </div>
      <div className="appearance-thumbnails" aria-label="同一主体的已有图片">
        {viewableCandidates.map((candidate) => <button key={candidate.id} type="button" className={`appearance-thumbnail${candidate.assetId === viewed?.assetId ? " viewing" : ""}`} aria-pressed={candidate.assetId === viewed?.assetId} onClick={() => setViewedAssetId(candidate.assetId)}><ManagedAssetImage projectId={projectId} subjectId={subjectKey(selected)} asset={candidate.asset} assetId={candidate.assetId} alt={`${candidate.outputFilename} 缩略图`} unavailableLabel="候选图片不可用" /><span>{candidate.outputFilename}</span></button>)}
        {candidates.filter((candidate) => !candidate.asset).map((candidate) => <div className="appearance-thumbnail" key={candidate.id}><ManagedAssetImage projectId={projectId} subjectId={subjectKey(selected)} asset={candidate.asset} assetId={candidate.assetId} alt="候选图片不可用" unavailableLabel="候选图片不可用" /><span>{candidate.outputFilename}</span></div>)}
      </div>
      {viewableCandidates.length > 1 && <div className="appearance-compare-controls" aria-label="同一主体图片比较"><span>比较（已选 {comparisonCandidates.length}/4；至少选择 2 张）</span>{viewableCandidates.map((candidate) => { const compared = comparisonAssetIds.includes(candidate.assetId); return <Button key={candidate.id} variant={compared ? "primary" : "quiet"} disabled={!compared && comparisonAtCapacity} onClick={() => toggleComparison(candidate.assetId)}>{compared ? `移出 ${candidate.outputFilename}` : `加入 ${candidate.outputFilename}`}</Button>; })}{comparisonCandidates.length > 0 && <Button variant="quiet" onClick={clearComparison}>清空比较</Button>}{comparisonAtCapacity && <small>已达四张上限；先移出一张再替换。</small>}</div>}
      {comparisonCandidates.length >= 2 && <div className={`appearance-compare comparison-count-${comparisonCandidates.length}`} data-testid="art-reference-comparison"><header><strong>并排比较 · {comparisonCandidates.length} 张</strong><small>仅比较 {selected.subjectType === "scene" ? "环境" : "道具"} {selected.name}；不会选择生产资产。</small></header>{comparisonCandidates.map((candidate) => <figure key={candidate.assetId}><figcaption>{candidate.assetId === viewed?.assetId ? "当前查看" : "对比图片"} · {candidate.outputFilename}</figcaption><ManagedAssetImage projectId={projectId} subjectId={subjectKey(selected)} asset={candidate.asset} assetId={candidate.assetId} alt={`${candidate.outputFilename} 比较图片`} unavailableLabel="对比图片不可用" /></figure>)}</div>}
      <section className="appearance-ideas"><span className="eyebrow">研究操作</span><h3>冻结一个新的环境或道具研究</h3><p>此处仅复用既有 F3B 手动 handoff；不会发送、生成、选择或导入图片。</p><label>渲染方向 overlay<textarea data-testid="art-reference-direction" disabled={!actionable} rows={3} value={direction} onChange={(event) => setDirection(event.target.value)} /></label>{(!study || !study.current) && <Button disabled={!actionable || !direction.trim()} onClick={() => void act(() => plotloomApi.prepareArtReferenceProposal(projectId, { subjectType: selected.subjectType, subjectId: selected.subjectId, renderDirection: direction.trim() }))}>准备研究</Button>}{study && <div className="button-row">{study.current && <Button disabled={!actionable} onClick={() => void act(() => plotloomApi.copyArtReferenceProposal(projectId, study.id), (copied) => setAssignment(copied.assignment))}>复制 ImageGen 任务</Button>}{study.state !== "cancelled" && <Button disabled={!actionable} onClick={() => void act(() => plotloomApi.refreshArtReferenceProposal(projectId, study.id))}>刷新 delivery</Button>}{(study.state === "prepared" || study.state === "exported") && <Button variant="danger" disabled={!actionable} onClick={() => void act(() => plotloomApi.cancelArtReferenceProposal(projectId, study.id, "Operator cancelled the F3B reference-study handoff."))}>取消 handoff</Button>}</div>}</section>
      {error && <ErrorNotice message={error} />}
    </section>
    {viewed && <AssetZoomDialog open={expanded} onClose={() => setExpanded(false)} label="放大查看环境或道具图片"><ManagedAssetImage projectId={projectId} subjectId={subjectKey(selected)} asset={viewed.asset} assetId={viewed.assetId} alt={`${selected.name} 放大图片`} unavailableLabel="当前查看图片不可用" /></AssetZoomDialog>}
  </section>;
}

function artSubjects(art: Record<string, unknown>): Subject[] {
  return (["scene", "prop"] as const).flatMap((subjectType) => {
    const items = art[subjectType === "scene" ? "scenes" : "props"];
    return Array.isArray(items) ? items.filter((item): item is Record<string, unknown> => typeof item === "object" && item !== null && typeof item.id === "string").map((item) => ({ subjectType, subjectId: item.id as string, name: String(item.name || item.id) })) : [];
  });
}

function subjectKey(subject: Subject) { return `${subject.subjectType}:${subject.subjectId}`; }

function studyStatus(study: ArtReferenceProposal | undefined) {
  if (!study) return "missing";
  if (study.state === "cancelled") return "cancelled";
  if (!study.current) return "changed / stale";
  if (study.deliveries.some((delivery) => delivery.state === "rejected")) return "delivery rejected";
  return study.state === "delivered" ? "current" : "awaiting delivery";
}

function CandidateDetails({ candidate, study }: { candidate: Candidate; study: ArtReferenceProposal }) {
  return <details className="reference-technical"><summary>查看候选来源与技术详情</summary><dl><div><dt>主体</dt><dd>{study.subjectType}:{study.subjectId}</dd></div><div><dt>提案</dt><dd>{study.id}</dd></div><div><dt>交付</dt><dd>{candidate.delivery.deliveryId || candidate.delivery.state}</dd></div><div><dt>资产</dt><dd>{candidate.assetId}</dd></div><div><dt>输出标识</dt><dd>{candidate.outputHash}</dd></div><div><dt>来源</dt><dd>{candidate.asset?.provenance?.origin || "来源信息不可用"}</dd></div><div><dt>权利</dt><dd>{candidate.asset?.provenance?.rights || "权利信息不可用"}</dd></div><div><dt>尺寸</dt><dd>{candidate.asset ? `${candidate.asset.width} × ${candidate.asset.height}` : "资产不可用"}</dd></div></dl></details>;
}
