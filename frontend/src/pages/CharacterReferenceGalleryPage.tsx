import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { plotloomApi } from "../api";
import { Button, ErrorNotice, Field, Spinner } from "../components";
import type { AcceptedCastRevision, CastReviewState, CharacterImportedAppearance, CharacterReferenceDecision, CharacterReferenceProposal, ManagedAsset, VisualWorkbench } from "../types";

type GalleryData = {
  title: string;
  decisions: CharacterReferenceDecision[];
  referenceStates: VisualWorkbench["characterReferences"]["states"];
  proposals: CharacterReferenceProposal[];
  imported: CharacterImportedAppearance[];
  assets: ManagedAsset[];
};

type Subject = { id: string; name: string; inAcceptedCast: boolean };
type Candidate = {
  id: string;
  assetId: string;
  asset: ManagedAsset | null;
  proposal: CharacterReferenceProposal;
  delivery: CharacterReferenceProposal["deliveries"][number];
  outputHash: string;
  role: "original" | "refinement";
  imported?: boolean;
};

/**
 * The F2B review belongs beside the cast that admits its subjects.  It only
 * reads until a creator deliberately invokes one of the supplied operations.
 */
export function CharacterReferenceReviewPanel({ projectId, readOnly, castState, castSession, castSessionOwner, castTransitionPending }: { projectId: string; readOnly: boolean; castState: CastReviewState | undefined; castSession: string; castSessionOwner: Readonly<{ current: string }>; castTransitionPending: boolean }) {
  const [data, setData] = useState<GalleryData>();
  const [error, setError] = useState("");
  const [selectedSubjectId, setSelectedSubjectId] = useState("");
  const requestOwner = useRef(0);
  const observedProjectId = useRef("");

  const refresh = useCallback(async (expectedSession: string, signal?: AbortSignal) => {
    if (castSessionOwner.current !== expectedSession) return false;
    const owner = ++requestOwner.current;
    const isCurrent = () => castSessionOwner.current === expectedSession && requestOwner.current === owner;
    try {
      const [project, references, proposals, workbench, imported] = await Promise.all([
        plotloomApi.getProject(projectId, signal),
        plotloomApi.getCharacterReferences(projectId, signal),
        plotloomApi.getCharacterReferenceProposals(projectId, signal),
        plotloomApi.getVisualWorkbench(projectId, signal), plotloomApi.getImportedCharacterAppearances(projectId),
      ]);
      if (!isCurrent()) return false;
      setData({
        title: project.brief.title,
        decisions: references.decisions,
        referenceStates: references.states,
        proposals: proposals.proposals,
        assets: workbench.assets,
        imported: imported.appearances,
      });
      setError("");
      return true;
    } catch (reason) {
      if (isCurrent()) setError(reason instanceof Error ? reason.message : "无法刷新角色参考。");
      return false;
    }
  }, [castSessionOwner, projectId]);

  useEffect(() => {
    if (!projectId) return;
    const projectChanged = observedProjectId.current !== projectId;
    observedProjectId.current = projectId;
    if (projectChanged) { setData(undefined); setError(""); setSelectedSubjectId(""); }
    const controller = new AbortController();
    void refresh(castSession, controller.signal);
    return () => {
      controller.abort();
      requestOwner.current += 1;
    };
  }, [castSession, projectId, refresh]);

  // A prepared accepted-cast proposal becomes visible in this gallery only
  // through its existing hash/currentness admission endpoint.  Queue success
  // is not delivery success, and a package conflict stops repeat observation.
  useEffect(() => {
    if (!data) return;
    const timer = window.setInterval(() => {
      const outstanding = data.proposals.filter((proposal) =>
        proposal.current && proposal.state === "exported" && !proposal.deliveries.some(
          (delivery) => delivery.diagnosticCode === "package_conflict",
        ),
      );
      void Promise.all(outstanding.map((proposal) => plotloomApi.refreshCharacterReferenceProposal(projectId, proposal.id)))
        .then((results) => results.some((result) => result.state !== "awaiting_delivery") ? refresh(castSession) : undefined)
        .catch(() => refresh(castSession).catch(() => false));
    }, 3_000);
    return () => window.clearInterval(timer);
  }, [castSession, data, projectId, refresh]);

  const subjects = useMemo(() => data ? gallerySubjects(castState?.acceptedCast ?? null, data.proposals) : [], [data, castState?.acceptedCast]);
  useEffect(() => {
    if (subjects.length && !subjects.some((subject) => subject.id === selectedSubjectId)) setSelectedSubjectId(subjects[0].id);
  }, [subjects, selectedSubjectId]);
  const selected = subjects.find((subject) => subject.id === selectedSubjectId) || subjects[0];

  if (error) return <section className="character-reference-review"><ErrorNotice message={error} /></section>;
  if (!data || !castState) return <section className="character-reference-review reference-gallery-loading"><Spinner label="正在读取角色参考" /></section>;
  if (!castState.acceptedCast) return <section className="character-reference-review"><EmptyState title="尚无已接受角色" message="先在上方审核并接受角色文字提案；图像选择不会创建角色或示例图像。" /></section>;
  if (!selected) return <section className="character-reference-review"><EmptyState title="角色中没有可查看的主体" message="当前已接受角色未提供可映射的主体；这里不会猜测或创建主体。" /></section>;

  return <section className="character-reference-review" data-testid="character-reference-gallery">
    <section className="reference-gallery-intro">
      <div><span className="eyebrow">角色外观</span><h2>外观参考</h2><p>{data.title} · 先比较已有图片，再明确选用身份参考；也可基于当前查看图片探索调整。创建提案只冻结请求；必须明确发送给 specialist，且不会自动选择。</p></div>
      <div className={`reference-gallery-cast-state ${castState.status === "accepted" && !castTransitionPending ? "current" : "stale"}`}><strong>{castTransitionPending ? "角色文字正在更新" : castState.status === "accepted" ? `已接受角色 r${castState.acceptedCast.revision}` : "已接受角色已过期"}</strong><span>{castTransitionPending ? "角色更新完成前，保留图像仅供核对。" : castState.status === "accepted" ? "可以审阅、选择、准备并发送新提案。" : "保留图像仅供核对；重新接受角色前不能选择、细化、准备或发送新提案。"}</span></div>
    </section>
    <div className="reference-gallery-layout">
      <nav className="reference-subjects" aria-label="角色主体"><span>角色主体</span>{subjects.map((subject) => <button key={subject.id} type="button" className={subject.id === selected.id ? "selected" : ""} aria-pressed={subject.id === selected.id} onClick={() => setSelectedSubjectId(subject.id)}><strong>{subject.name}</strong><small>{subject.inAcceptedCast ? "已接受角色" : "仅保留的历史主体"}</small></button>)}</nav>
      <SubjectGallery key={`${castSession}:${selected.id}`} projectId={projectId} subject={selected} data={data} readOnly={readOnly || castTransitionPending || castState.status !== "accepted"} castRevision={castState.acceptedCast.revision} rootSession={castSession} session={`${castSession}:${selected.id}`} castSessionOwner={castSessionOwner} onRefresh={refresh} />
    </div>
  </section>;
}

function SubjectGallery({ projectId, subject, data, readOnly, castRevision, rootSession, session, castSessionOwner, onRefresh }: { projectId: string; subject: Subject; data: GalleryData; readOnly: boolean; castRevision: number; rootSession: string; session: string; castSessionOwner: Readonly<{ current: string }>; onRefresh: (expectedSession: string) => Promise<boolean> }) {
  const [direction, setDirection] = useState("");
  // A subject with no retained image can start an original study immediately;
  // using a viewed image remains an explicit creator choice.
  const [ideaMode, setIdeaMode] = useState<"refine" | "fresh">("fresh");
  const [viewedAssetId, setViewedAssetId] = useState("");
  // The gallery can retain any number of alternatives. Comparison is a
  // deliberate, local review set capped at four; it never selects identity.
  const [comparisonAssetIds, setComparisonAssetIds] = useState<string[]>([]);
  const [expanded, setExpanded] = useState(false);
  const [busy, setBusy] = useState(false);
  const [actionError, setActionError] = useState("");
  const [importFile, setImportFile] = useState<File | null>(null);
  const [importLabel, setImportLabel] = useState("");
  const [importOrigin, setImportOrigin] = useState("");
  const active = useRef(true); const sessionRef = useRef(session);
  const operationOwner = useRef(0);
  sessionRef.current = session;
  useEffect(() => {
    active.current = true;
    return () => { active.current = false; };
  }, []);
  const assets = new Map(data.assets.map((asset) => [asset.id, asset]));
  const decisions = data.decisions.filter((decision) => decision.characterId === subject.id);
  const selectedDecision = decisions.find((decision) => decision.current);
  const historicalDecisions = decisions.filter((decision) => !decision.current);
  const candidates = [
    ...candidateEntries(data.proposals, subject.id),
    ...data.imported.filter((item) => item.characterId === subject.id).map((item) => ({
      id: item.id, assetId: item.assetId, asset: item.asset, outputHash: item.asset.originalHash,
      role: "original" as const, imported: true,
      proposal: { id: item.id, projectId, characterId: subject.id, current: item.current, parentCandidateAssetId: null, requestHash: item.characterContextHash, request: { frozenSnapshot: { visualDirection: item.label } }, deliveries: [] } as unknown as CharacterReferenceProposal,
      delivery: { id: item.id, state: "accepted", candidates: [], diagnosticCode: null, publicationPhase: null } as unknown as CharacterReferenceProposal["deliveries"][number],
    })),
  ].map((candidate) => ({ ...candidate, asset: assets.get(candidate.assetId) ?? candidate.asset }));
  const observedDeliveries = data.proposals.filter((proposal) => proposal.characterId === subject.id)
    .flatMap((proposal) => proposal.deliveries.map((delivery) => ({ proposal, delivery })));
  // Old rows predate publication-phase provenance. Preserve them separately
  // rather than guessing that every legacy `delivery_partial` was transient;
  // any newly observed post-completion partial is explicitly `final` and stays
  // in the visible delivery-failure cards below.
  const legacyPartialDeliveries = observedDeliveries.filter(({ delivery }) =>
    delivery.state === "rejected" && delivery.diagnosticCode === "delivery_partial" && delivery.publicationPhase === null,
  );
  const incompleteDeliveries = observedDeliveries.filter(({ delivery }) =>
    delivery.candidates.length === 0 && !legacyPartialDeliveries.some(({ delivery: legacy }) => legacy.id === delivery.id),
  );
  const undeliveredProposals = data.proposals.filter((proposal) => proposal.characterId === subject.id && proposal.deliveries.length === 0);
  const selectedAssetIds = new Set(selectedDecision ? [selectedDecision.primaryAssetId, ...selectedDecision.complementaryAssetIds] : []);
  const selectedAsset = selectedDecision ? assets.get(selectedDecision.primaryAssetId) : undefined;
  const currentCandidate = candidates.find((candidate) => candidate.proposal.current && candidate.delivery.state === "accepted" && candidate.asset);
  const historicalCandidate = candidates.find((candidate) => candidate.asset);
  const viewableCandidates = candidates.filter((candidate) => candidate.asset);
  const fallbackViewedAssetId = selectedDecision?.primaryAssetId || currentCandidate?.assetId || historicalCandidate?.assetId || "";
  const effectiveViewedAssetId = viewableCandidates.some((candidate) => candidate.assetId === viewedAssetId) ? viewedAssetId : fallbackViewedAssetId;
  const viewedCandidate = viewableCandidates.find((candidate) => candidate.assetId === effectiveViewedAssetId);
  const viewedAsset = viewedCandidate?.asset ?? (selectedDecision?.primaryAssetId === effectiveViewedAssetId ? selectedAsset : undefined);
  const viewedImageLabel = viewedCandidate
    ? candidateImageLabel(viewedCandidate, selectedAssetIds.has(effectiveViewedAssetId))
    : selectedDecision?.primaryAssetId === effectiveViewedAssetId ? "当前身份参考"
      : "当前查看图片";
  const comparisonCandidates = comparisonAssetIds.flatMap((assetId) => {
    const candidate = viewableCandidates.find((entry) => entry.assetId === assetId);
    return candidate ? [candidate] : [];
  });
  const comparisonAtCapacity = comparisonCandidates.length >= 4;
  const toggleComparison = (assetId: string) => setComparisonAssetIds((current) => current.includes(assetId)
    ? current.filter((item) => item !== assetId)
    : current.length < 4 ? [...current, assetId] : current);
  const referenceState = data.referenceStates.find((state) => state.characterId === subject.id);
  const act = async <T,>(operation: () => Promise<T>, applyResult?: (result: T) => void) => {
    const capturedSession = sessionRef.current;
    const capturedOwner = ++operationOwner.current;
    const isCurrent = () => active.current && castSessionOwner.current === rootSession && sessionRef.current === capturedSession && operationOwner.current === capturedOwner;
    if (!isCurrent()) return;
    setBusy(true); setActionError("");
    try {
      const result = await operation();
      if (isCurrent()) { applyResult?.(result); await onRefresh(rootSession); }
    } catch (reason) { if (isCurrent()) setActionError(reason instanceof Error ? reason.message : "角色参考操作失败。"); }
    finally { if (isCurrent()) setBusy(false); }
  };
  const selectCandidate = (candidate: Candidate) => void act(async () => {
    await plotloomApi.selectCharacterReference(projectId, { characterId: subject.id, authority: "cast", primaryAssetId: candidate.assetId, complementaryAssetIds: [], expectedReferenceRevision: referenceState?.revision ?? 0 });
  });
  const prepare = () => void act(async () => {
    await plotloomApi.prepareCharacterReferenceProposal(projectId, { characterId: subject.id, castRevision, visualDirection: direction.trim(), parentCandidateAssetId: ideaMode === "refine" ? effectiveViewedAssetId || undefined : undefined });
  }, () => { setDirection(""); setIdeaMode("fresh"); });
  const send = (proposal: CharacterReferenceProposal) => void act(async () => {
    await plotloomApi.sendCharacterReferenceProposal(projectId, proposal.id);
  });
  const refreshProposal = (proposal: CharacterReferenceProposal) => void act(async () => { await plotloomApi.refreshCharacterReferenceProposal(projectId, proposal.id); });
  const cancel = (proposal: CharacterReferenceProposal) => void act(async () => { await plotloomApi.cancelCharacterReferenceProposal(projectId, proposal.id, "Creator cancelled the exploratory reference handoff from Characters."); });
  const importAppearance = () => void act(async () => {
    if (!importFile) throw new Error("请选择 PNG 或 JPEG 图片。");
    const asset = await plotloomApi.importManagedAsset(projectId, importFile, { origin: importOrigin.trim(), rights: "known", rightsNote: "Character appearance technical import." });
    await plotloomApi.attachImportedCharacterAppearance(projectId, { characterId: subject.id, assetId: asset.id, label: importLabel.trim(), expectedCastRevision: castRevision });
  }, () => { setImportFile(null); setImportLabel(""); setImportOrigin(""); });

  return <section className="reference-subject-gallery" aria-labelledby="reference-subject-title">
    <header className="reference-subject-heading"><div><span className="eyebrow">当前主体</span><h2 id="reference-subject-title">{subject.name}</h2><p>{selectedDecision?.current ? `已选择身份参考 r${selectedDecision.referenceRevision}；查看图片不会改变选择。` : "尚未选择身份参考。查看或比较图片不会自动成为选择。"}</p></div><span className={selectedDecision?.current ? "reference-state selected" : "reference-state missing"}>{selectedDecision?.current ? "已选择" : "未选择"}</span></header>
    <section className="appearance-workspace" aria-label={`${subject.name} 的外观工作区`}>
      <div className="appearance-viewer" data-testid="appearance-viewer">
        <div className="appearance-viewer-heading"><div><span className="eyebrow">当前查看</span><strong>{viewedCandidate ? viewedCandidate.imported ? "导入图片" : viewedCandidate.role === "refinement" ? "细化候选" : "候选图片" : "当前身份参考"}</strong></div>{selectedDecision && <span className={selectedDecision.primaryAssetId === effectiveViewedAssetId ? "reference-state selected" : "reference-state historical"}>{selectedDecision.primaryAssetId === effectiveViewedAssetId ? "这张图已被选用" : "当前身份参考在另一张图"}</span>}</div>
        {effectiveViewedAssetId ? <AssetPresentation projectId={projectId} subjectId={subject.id} asset={viewedAsset} assetId={effectiveViewedAssetId} alt={`${subject.name} 当前查看图片`} unavailableLabel="当前查看图片不可用" /> : <div className="reference-no-image" data-testid="reference-no-image"><strong>尚无可显示的图像</strong><p>此主体还没有既有候选或已选择参考。</p></div>}
        <div className="button-row"><Button variant="primary" disabled={readOnly || busy || !viewedCandidate || selectedDecision?.primaryAssetId === effectiveViewedAssetId} onClick={() => viewedCandidate && selectCandidate(viewedCandidate)}>{selectedDecision?.primaryAssetId === effectiveViewedAssetId ? "当前已选用" : "选用当前图片"}</Button><Button variant="quiet" disabled={!effectiveViewedAssetId} onClick={() => setExpanded(true)}>放大查看</Button></div>
        {viewedCandidate?.imported ? <ImportedAppearanceDetails candidate={viewedCandidate} /> : viewedCandidate && <ProposalDetails proposal={viewedCandidate.proposal} delivery={viewedCandidate.delivery} outputHash={viewedCandidate.outputHash} provenance={viewedCandidate.asset?.provenance?.origin} direction={frozenDirection(viewedCandidate.proposal)} />}
      </div>
      <div className="appearance-thumbnails" aria-label="已有图片">
        {viewableCandidates.map((candidate) => <button key={candidate.id} type="button" className={`appearance-thumbnail${candidate.assetId === effectiveViewedAssetId ? " viewing" : ""}${selectedAssetIds.has(candidate.assetId) ? " selected" : ""}`} aria-pressed={candidate.assetId === effectiveViewedAssetId} onClick={() => setViewedAssetId(candidate.assetId)}><AssetPresentation projectId={projectId} subjectId={subject.id} asset={candidate.asset ?? undefined} assetId={candidate.assetId} alt={`${candidateImageLabel(candidate, selectedAssetIds.has(candidate.assetId))}缩略图`} unavailableLabel="候选图片不可用" /><span>{candidateImageLabel(candidate, selectedAssetIds.has(candidate.assetId))}</span></button>)}
        {!viewableCandidates.length && <p className="reference-empty-list">没有可浏览的候选图片。</p>}
      </div>
      {viewableCandidates.length > 1 && <div className="appearance-compare-controls" aria-label="图片比较"><span>比较（已选 {comparisonCandidates.length}/4；至少选择 2 张）</span>{viewableCandidates.map((candidate) => { const compared = comparisonAssetIds.includes(candidate.assetId); return <Button key={candidate.id} variant={compared ? "primary" : "quiet"} disabled={busy || (!compared && comparisonAtCapacity)} onClick={() => toggleComparison(candidate.assetId)}>{compared ? `移出 ${candidateImageLabel(candidate, selectedAssetIds.has(candidate.assetId))}` : `加入 ${candidateImageLabel(candidate, selectedAssetIds.has(candidate.assetId))}`}</Button>; })}{comparisonCandidates.length > 0 && <Button variant="quiet" disabled={busy} onClick={() => setComparisonAssetIds([])}>清空比较</Button>}{comparisonAtCapacity && <small>已达四张上限；先移出一张再替换。</small>}</div>}
      {comparisonCandidates.length >= 2 && <div className={`appearance-compare comparison-count-${comparisonCandidates.length}`} data-testid="appearance-comparison"><header><strong>并排比较 · {comparisonCandidates.length} 张</strong><small>当前查看：{viewedImageLabel}；对比不会选用身份参考。</small></header>{comparisonCandidates.map((candidate) => <figure key={candidate.assetId}><figcaption>{candidate.assetId === effectiveViewedAssetId ? "当前查看" : "对比图片"} · {candidateImageLabel(candidate, selectedAssetIds.has(candidate.assetId))}</figcaption><AssetPresentation projectId={projectId} subjectId={subject.id} asset={candidate.asset ?? undefined} assetId={candidate.assetId} alt={`${candidateImageLabel(candidate, selectedAssetIds.has(candidate.assetId))} 比较图片`} unavailableLabel="对比图片不可用" /></figure>)}</div>}
      <section className="appearance-import"><span className="eyebrow">导入已有图片</span><p>导入会保留来源与权利声明，并只作为未选用的 {subject.name} 外观选项。</p><Field label="图片标签"><input value={importLabel} disabled={readOnly || busy} onChange={(event) => setImportLabel(event.target.value)} /></Field><Field label="来源声明"><input value={importOrigin} disabled={readOnly || busy} onChange={(event) => setImportOrigin(event.target.value)} /></Field><label>PNG 或 JPEG<input type="file" accept="image/png,image/jpeg" disabled={readOnly || busy} onChange={(event) => setImportFile(event.target.files?.[0] ?? null)} /></label><Button variant="quiet" disabled={readOnly || busy || !importFile || !importLabel.trim() || !importOrigin.trim()} onClick={importAppearance}>导入为外观选项</Button></section>
      <section className="appearance-ideas"><span className="eyebrow">新想法</span><h3>用文字探索下一张图片</h3><div className="appearance-mode" role="group" aria-label="提案模式"><Button variant={ideaMode === "refine" ? "primary" : "quiet"} disabled={readOnly || busy || !effectiveViewedAssetId} onClick={() => setIdeaMode("refine")}>基于当前图片修改</Button><Button variant={ideaMode === "fresh" ? "primary" : "quiet"} disabled={readOnly || busy} onClick={() => setIdeaMode("fresh")}>尝试全新方案</Button></div><p>{ideaMode === "refine" ? "会冻结当前查看的图片与这段文字；不会改变当前身份参考。" : "只使用这段文字，不引用当前查看图片；不会改变当前身份参考。"}</p><Field label="想法"><textarea rows={3} value={direction} disabled={readOnly || busy} placeholder="描述希望保留、调整或探索的外观特征。" onChange={(event) => setDirection(event.target.value)} /></Field><div className="button-row"><Button variant="primary" disabled={readOnly || busy || !direction.trim() || (ideaMode === "refine" && !effectiveViewedAssetId)} onClick={prepare}>{busy ? "正在创建…" : "创建提案"}</Button><small>创建后可在下方提案状态中发送；返回图片会加入这里，但不会自动选用。</small></div></section>
      {actionError && <ErrorNotice message={actionError} />}
    </section>
    {expanded && effectiveViewedAssetId && <div className="appearance-dialog" role="dialog" aria-modal="true" aria-label="放大查看图片"><div><Button variant="quiet" onClick={() => setExpanded(false)}>关闭</Button><AssetPresentation projectId={projectId} subjectId={subject.id} asset={viewedAsset} assetId={effectiveViewedAssetId} alt={`${subject.name} 放大图片`} unavailableLabel="当前查看图片不可用" /></div></div>}
    <section className="reference-alternatives" aria-label={`${subject.name} 的提案状态与历史`}><header><div><span className="eyebrow">提案状态与历史</span><h3>交付与保留记录</h3></div></header><div className="reference-card-grid">
      {incompleteDeliveries.map(({ proposal, delivery }) => <DeliveryEvidenceCard key={`delivery:${delivery.id}`} projectId={projectId} subjectId={subject.id} proposal={proposal} delivery={delivery} parent={proposal.parentCandidateAssetId ? candidates.find((entry) => entry.assetId === proposal.parentCandidateAssetId) : undefined} actions={{ readOnly: readOnly || busy, onSend: () => send(proposal), onRefresh: () => refreshProposal(proposal), onCancel: () => cancel(proposal) }} />)}
      {legacyPartialDeliveries.length > 0 && <LegacyPartialHistory deliveries={legacyPartialDeliveries} />}
      {undeliveredProposals.map((proposal) => <UndeliveredProposalCard key={`proposal:${proposal.id}`} projectId={projectId} subjectId={subject.id} proposal={proposal} parent={proposal.parentCandidateAssetId ? candidates.find((entry) => entry.assetId === proposal.parentCandidateAssetId) : undefined} actions={{ readOnly: readOnly || busy, onSend: () => send(proposal), onRefresh: () => refreshProposal(proposal), onCancel: () => cancel(proposal) }} />)}
      {historicalDecisions.flatMap((decision) => [decision.primaryAssetId, ...decision.complementaryAssetIds].map((assetId) => <HistoricalSelectionCard key={`history:${decision.id}:${assetId}`} projectId={projectId} subjectId={subject.id} decision={decision} asset={assets.get(assetId)} assetId={assetId} />))}
    </div></section>
    {historicalDecisions.length > 0 && <details className="reference-history"><summary>历史选择说明（不作为当前参考）</summary>{historicalDecisions.map((decision) => <p key={decision.id}>r{decision.referenceRevision} · {decision.revokedAt ? "已撤销" : "已被后续选择取代"}{decision.notes ? ` · ${decision.notes}` : ""}</p>)}</details>}
  </section>;
}

type ProposalActions = { readOnly: boolean; onSend: () => void; onRefresh: () => void; onCancel: () => void };

function ProposalLifecycle({ proposal, actions }: { proposal: CharacterReferenceProposal; actions: ProposalActions }) {
  const canSend = proposal.current && proposal.state === "prepared";
  const canRefresh = proposal.state === "exported";
  const canCancel = proposal.state === "prepared" || proposal.state === "exported";
  if (!canSend && !canRefresh && !canCancel) return <small className="proposal-lifecycle-status">{proposal.state === "cancelled" ? "提案已取消。" : proposal.current ? "提案已完成；返回图片会出现在上方。" : "这是保留的历史提案。"}</small>;
  return <div className="reference-card-actions">{canSend && <Button variant="quiet" disabled={actions.readOnly} onClick={actions.onSend}>发送给 specialist</Button>}{canRefresh && <Button variant="quiet" disabled={actions.readOnly} onClick={actions.onRefresh}>立即检查交付</Button>}{canCancel && <Button variant="danger" disabled={actions.readOnly} onClick={actions.onCancel}>取消提案</Button>}</div>;
}

function DeliveryEvidenceCard({ projectId, subjectId, proposal, delivery, parent, actions }: { projectId: string; subjectId: string; proposal: CharacterReferenceProposal; delivery: CharacterReferenceProposal["deliveries"][number]; parent: Candidate | undefined; actions: ProposalActions }) {
  const direction = frozenDirection(proposal);
  return <article className="reference-card delivery-evidence" data-proposal-id={proposal.id}><div className="reference-missing-asset"><strong>{deliveryLabel(delivery.state)}</strong><small>{delivery.diagnosticCode || "此交付没有可显示的图像输出。"}</small></div><div className="reference-card-body"><span className="reference-state failed">{deliveryLabel(delivery.state)}</span><strong>{proposal.parentCandidateAssetId ? "细化交付" : "原始交付"}</strong><small className="proposal-lifecycle-status">本次交付未通过，未加入图片列表。</small>{proposal.parentCandidateAssetId && <ParentReference projectId={projectId} subjectId={subjectId} assetId={proposal.parentCandidateAssetId} parent={parent} />}{proposal.state !== "delivered" && <ProposalLifecycle proposal={proposal} actions={actions} />}<ProposalDetails proposal={proposal} delivery={delivery} direction={direction} /></div></article>;
}

function LegacyPartialHistory({ deliveries }: { deliveries: Array<{ proposal: CharacterReferenceProposal; delivery: CharacterReferenceProposal["deliveries"][number] }> }) {
  return <details className="reference-history transient-delivery-history" data-testid="historical-partial-deliveries"><summary>历史未分类交付观察（{deliveries.length}）</summary><p>这些旧记录缺少 completion.json 发布阶段标记，仍保留以供审计。新的最终交付完整性失败会作为可见的拒绝卡片显示。</p><ul>{deliveries.map(({ proposal, delivery }) => <li key={delivery.id}>{proposal.id} · {delivery.createdAt} · {delivery.diagnosticCode}</li>)}</ul></details>;
}

function UndeliveredProposalCard({ projectId, subjectId, proposal, parent, actions }: { projectId: string; subjectId: string; proposal: CharacterReferenceProposal; parent: Candidate | undefined; actions: ProposalActions }) {
  const direction = frozenDirection(proposal);
  const state = proposal.state === "cancelled" ? "已取消，未交付" : proposal.state === "exported" ? "已导出，等待交付" : "已准备，尚未交付";
  return <article className="reference-card delivery-evidence" data-proposal-id={proposal.id}><div className="reference-missing-asset"><strong>{state}</strong><small>没有交付记录，因此没有可显示图像。</small></div><div className="reference-card-body"><span className="reference-state historical">{state}</span><strong>{proposal.parentCandidateAssetId ? "细化提案" : "原始提案"}</strong>{proposal.parentCandidateAssetId && <ParentReference projectId={projectId} subjectId={subjectId} assetId={proposal.parentCandidateAssetId} parent={parent} />}<ProposalLifecycle proposal={proposal} actions={actions} /><ProposalDetails proposal={proposal} direction={direction} /></div></article>;
}

function HistoricalSelectionCard({ projectId, subjectId, decision, asset, assetId }: { projectId: string; subjectId: string; decision: CharacterReferenceDecision; asset: ManagedAsset | undefined; assetId: string }) {
  return <article className="reference-card historical-selection"><AssetPresentation projectId={projectId} subjectId={subjectId} asset={asset} assetId={assetId} alt="历史身份参考，当前不可用" unavailableLabel="历史身份参考图像不可用" /><div className="reference-card-body"><span className="reference-state historical">历史选择，当前不可用</span><strong>身份参考 r{decision.referenceRevision}</strong><small>{asset ? `${asset.width} × ${asset.height}` : "已选择资产缺失"}</small><details className="reference-technical"><summary>技术详情</summary><dl><div><dt>选择</dt><dd>{decision.id}</dd></div><div><dt>状态</dt><dd>{decision.revokedAt ? "revoked" : "superseded_or_stale"}</dd></div><div><dt>备注</dt><dd>{decision.notes}</dd></div>{asset?.provenance && <div><dt>来源</dt><dd>{asset.provenance.origin}</dd></div>}</dl></details></div></article>;
}

function ProposalDetails({ proposal, delivery, outputHash, provenance, direction }: { proposal: CharacterReferenceProposal; delivery?: CharacterReferenceProposal["deliveries"][number]; outputHash?: string; provenance?: string; direction?: string }) {
  return <details className="reference-technical"><summary>查看生成指令与技术详情</summary>{direction && <><strong>冻结方向</strong><pre>{direction}</pre></>}<dl><div><dt>提案</dt><dd>{proposal.id}</dd></div><div><dt>请求标识</dt><dd>{proposal.requestHash}</dd></div><div><dt>提案状态</dt><dd>{proposal.state}</dd></div>{delivery && <div><dt>交付状态</dt><dd>{delivery.state}</dd></div>}{outputHash && <div><dt>输出标识</dt><dd>{outputHash}</dd></div>}{delivery?.diagnosticCode && <div><dt>诊断</dt><dd>{delivery.diagnosticCode}</dd></div>}{delivery?.manifestHash && <div><dt>交付清单</dt><dd>{delivery.manifestHash}</dd></div>}{provenance && <div><dt>来源</dt><dd>{provenance}</dd></div>}</dl></details>;
}

function ImportedAppearanceDetails({ candidate }: { candidate: Candidate }) {
  return <details className="reference-technical"><summary>查看导入来源与技术详情</summary><dl><div><dt>图片标签</dt><dd>{frozenDirection(candidate.proposal)}</dd></div><div><dt>资产</dt><dd>{candidate.assetId}</dd></div><div><dt>来源</dt><dd>{candidate.asset?.provenance?.origin ?? "来源信息不可用"}</dd></div><div><dt>权利</dt><dd>{candidate.asset?.provenance?.rights ?? "权利信息不可用"}</dd></div>{candidate.asset?.provenance?.rightsNote && <div><dt>权利说明</dt><dd>{candidate.asset.provenance.rightsNote}</dd></div>}</dl></details>;
}

function AssetPresentation({ projectId, subjectId, asset, assetId, alt, unavailableLabel }: { projectId: string; subjectId: string; asset: ManagedAsset | undefined; assetId: string; alt: string; unavailableLabel: string }) {
  const identity = `${projectId}:${subjectId}:${assetId}`;
  const [failedIdentity, setFailedIdentity] = useState<string | null>(null);
  const unavailable = !asset || failedIdentity === identity;
  if (unavailable) return <MissingAsset assetId={assetId} label={unavailableLabel} />;
  return <img src={plotloomApi.managedAssetUrl(projectId, asset.id)} alt={alt} onError={() => setFailedIdentity(identity)} />;
}

function ParentReference({ projectId, subjectId, assetId, parent }: { projectId: string; subjectId: string; assetId: string; parent: Candidate | undefined }) {
  const referenceName = parent ? `${parent.role === "refinement" ? "细化" : "候选"}图片` : "保留的图片依据";
  return <div className="reference-parent"><span>图片依据</span><strong>{referenceName}</strong><AssetPresentation projectId={projectId} subjectId={subjectId} asset={parent?.asset ?? undefined} assetId={assetId} alt={`${referenceName} 缩略图`} unavailableLabel="图片依据不可用" /></div>;
}

function MissingAsset({ assetId, label = "图像不可用" }: { assetId: string; label?: string }) { return <div className="reference-missing-asset" data-testid={`reference-image-unavailable-${assetId}`}><strong>{label}</strong><small>保留资产 {assetId.slice(0, 12)} 缺失、HTTP 读取失败或无法解码。</small></div>; }
function EmptyState({ title, message }: { title: string; message: string }) { return <section className="reference-gallery-empty"><strong>{title}</strong><p>{message}</p></section>; }

function gallerySubjects(accepted: AcceptedCastRevision | null, proposals: CharacterReferenceProposal[]): Subject[] {
  const characters = Array.isArray(accepted?.cast.characters) ? accepted.cast.characters : [];
  const mappings = new Map(accepted?.consumerMappings.map((mapping) => [mapping.castCharacterId, mapping.consumerCharacterId]) || []);
  const fromCast = characters.flatMap((value) => {
    if (!value || typeof value !== "object") return [];
    const character = value as Record<string, unknown>; const castId = typeof character.id === "string" ? character.id : "";
    const id = mappings.get(castId); if (!id) return [];
    return [{ id, name: typeof character.name === "string" && character.name ? character.name : id, inAcceptedCast: true }];
  });
  return fromCast;
}

function candidateEntries(proposals: CharacterReferenceProposal[], characterId: string): Candidate[] {
  return proposals.filter((proposal) => proposal.characterId === characterId).flatMap((proposal) => proposal.deliveries.flatMap((delivery) => delivery.candidates.map((candidate) => ({ id: candidate.id, assetId: candidate.assetId, asset: candidate.asset, proposal, delivery, outputHash: candidate.outputHash, role: candidate.role }))));
}

function candidateImageLabel(candidate: Candidate, selected: boolean): string {
  const direction = frozenDirection(candidate.proposal);
  const name = direction ? compactDirection(direction) : candidate.role === "refinement" ? "细化方案" : "新方案";
  const prefix = candidate.imported ? "导入图片" : "方案";
  return selected ? `当前身份参考 · ${name}` : `${prefix} · ${name}`;
}

function compactDirection(value: string): string {
  const firstLine = value.replace(/\s+/g, " ").trim().split(/[。！？.!?]/)[0]?.trim() || "未命名方案";
  return firstLine.length > 32 ? `${firstLine.slice(0, 31)}…` : firstLine;
}

function frozenDirection(proposal: CharacterReferenceProposal): string | undefined {
  const snapshot = proposal.request.frozenSnapshot;
  return snapshot && typeof snapshot === "object" && typeof (snapshot as Record<string, unknown>).visualDirection === "string" ? (snapshot as Record<string, string>).visualDirection : undefined;
}
function deliveryLabel(state: CharacterReferenceProposal["deliveries"][number]["state"]): string { return state === "inapplicable" ? "已过期 / 不适用交付" : state === "rejected" ? "交付失败 / 已拒绝" : "交付未提供图像"; }
