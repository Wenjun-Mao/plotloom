import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { plotloomApi } from "../api";
import { Button, ErrorNotice, Field, Spinner } from "../components";
import type { AcceptedCastRevision, CastReviewState, CharacterReferenceDecision, CharacterReferenceProposal, ManagedAsset, VisualWorkbench } from "../types";

type GalleryData = {
  title: string;
  decisions: CharacterReferenceDecision[];
  referenceStates: VisualWorkbench["characterReferences"]["states"];
  proposals: CharacterReferenceProposal[];
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
      const [project, references, proposals, workbench] = await Promise.all([
        plotloomApi.getProject(projectId, signal),
        plotloomApi.getCharacterReferences(projectId, signal),
        plotloomApi.getCharacterReferenceProposals(projectId, signal),
        plotloomApi.getVisualWorkbench(projectId, signal),
      ]);
      if (!isCurrent()) return false;
      setData({
        title: project.brief.title,
        decisions: references.decisions,
        referenceStates: references.states,
        proposals: proposals.proposals,
        assets: workbench.assets,
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
      <div><span className="eyebrow">角色外观</span><h2>外观参考</h2><p>{data.title} · 先比较已有图像，再明确选用身份参考；也可基于可识别的父图调整。创建提案只冻结请求；必须明确发送给 specialist，且不会自动选择。</p></div>
      <div className={`reference-gallery-cast-state ${castState.status === "accepted" && !castTransitionPending ? "current" : "stale"}`}><strong>{castTransitionPending ? "角色文字正在更新" : castState.status === "accepted" ? `已接受角色 r${castState.acceptedCast.revision}` : "已接受角色已过期"}</strong><span>{castTransitionPending ? "角色更新完成前，保留图像仅供核对。" : castState.status === "accepted" ? "可以审阅、选择、准备并发送新提案。" : "保留图像仅供核对；重新接受角色前不能选择、细化、准备或发送新提案。"}</span></div>
    </section>
    <div className="reference-gallery-layout">
      <nav className="reference-subjects" aria-label="角色主体"><span>角色主体</span>{subjects.map((subject) => <button key={subject.id} type="button" className={subject.id === selected.id ? "selected" : ""} aria-pressed={subject.id === selected.id} onClick={() => setSelectedSubjectId(subject.id)}><strong>{subject.name}</strong><small>{subject.inAcceptedCast ? "已接受角色" : "仅保留的历史主体"}</small></button>)}</nav>
      <SubjectGallery key={`${castSession}:${selected.id}`} projectId={projectId} subject={selected} data={data} readOnly={readOnly || castTransitionPending || castState.status !== "accepted"} castRevision={castState.acceptedCast.revision} rootSession={castSession} session={`${castSession}:${selected.id}`} castSessionOwner={castSessionOwner} onRefresh={refresh} />
    </div>
  </section>;
}

function SubjectGallery({ projectId, subject, data, readOnly, castRevision, rootSession, session, castSessionOwner, onRefresh }: { projectId: string; subject: Subject; data: GalleryData; readOnly: boolean; castRevision: number; rootSession: string; session: string; castSessionOwner: Readonly<{ current: string }>; onRefresh: (expectedSession: string) => Promise<boolean> }) {
  const [reviewer, setReviewer] = useState("creator");
  const [notes, setNotes] = useState("");
  const [direction, setDirection] = useState("");
  const [parentCandidateAssetId, setParentCandidateAssetId] = useState("");
  const [busy, setBusy] = useState(false);
  const [actionError, setActionError] = useState("");
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
  const candidates = candidateEntries(data.proposals, subject.id).map((candidate) => ({ ...candidate, asset: assets.get(candidate.assetId) ?? candidate.asset }));
  const selectedParent = candidates.find((candidate) => candidate.assetId === parentCandidateAssetId);
  const incompleteDeliveries = data.proposals.filter((proposal) => proposal.characterId === subject.id)
    .flatMap((proposal) => proposal.deliveries.filter((delivery) => delivery.candidates.length === 0).map((delivery) => ({ proposal, delivery })));
  const undeliveredProposals = data.proposals.filter((proposal) => proposal.characterId === subject.id && proposal.deliveries.length === 0);
  const selectedAssetIds = new Set(selectedDecision ? [selectedDecision.primaryAssetId, ...selectedDecision.complementaryAssetIds] : []);
  const selectedAsset = selectedDecision ? assets.get(selectedDecision.primaryAssetId) : undefined;
  const currentCandidate = candidates.find((candidate) => candidate.proposal.current && candidate.delivery.state === "accepted" && candidate.asset);
  const historicalCandidate = candidates.find((candidate) => candidate.asset);
  // A current decision owns the hero even when its managed asset is unavailable.
  // Showing a candidate there would misrepresent an alternative as the selection.
  const hero = selectedDecision
    ? { asset: selectedAsset, assetId: selectedDecision.primaryAssetId, label: "当前已选择的身份参考", selected: true }
    : currentCandidate?.asset
      ? { asset: currentCandidate.asset, assetId: currentCandidate.asset.id, label: "当前候选，尚未选择", selected: false }
      : historicalCandidate?.asset
        ? { asset: historicalCandidate.asset, assetId: historicalCandidate.asset.id, label: "历史候选，未被选择", selected: false }
        : undefined;
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
    await plotloomApi.selectCharacterReference(projectId, { characterId: subject.id, authority: "cast", primaryAssetId: candidate.assetId, complementaryAssetIds: [], expectedReferenceRevision: referenceState?.revision ?? 0, reviewer: reviewer.trim(), notes: notes.trim() });
  }, () => setNotes(""));
  const prepare = () => void act(async () => {
    await plotloomApi.prepareCharacterReferenceProposal(projectId, { characterId: subject.id, castRevision, visualDirection: direction.trim(), parentCandidateAssetId: parentCandidateAssetId || undefined });
  }, () => { setDirection(""); setParentCandidateAssetId(""); });
  const send = (proposal: CharacterReferenceProposal) => void act(async () => {
    await plotloomApi.sendCharacterReferenceProposal(projectId, proposal.id);
  });
  const refreshProposal = (proposal: CharacterReferenceProposal) => void act(async () => { await plotloomApi.refreshCharacterReferenceProposal(projectId, proposal.id); });
  const cancel = (proposal: CharacterReferenceProposal) => void act(async () => { await plotloomApi.cancelCharacterReferenceProposal(projectId, proposal.id, "Creator cancelled the exploratory reference handoff from Characters."); });

  return <section className="reference-subject-gallery" aria-labelledby="reference-subject-title">
    <header className="reference-subject-heading"><div><span className="eyebrow">当前主体</span><h2 id="reference-subject-title">{subject.name}</h2><p>{selectedDecision?.current ? `已选择身份参考 r${selectedDecision.referenceRevision}。候选与选择不同：仅明确选择才会成为当前身份参考。` : "尚未选择身份参考。现有候选不会因查看而自动成为选择。"}</p></div><span className={selectedDecision?.current ? "reference-state selected" : "reference-state missing"}>{selectedDecision?.current ? "已选择" : "未选择"}</span></header>
    {hero ? <figure className={`reference-hero${hero.selected ? " selected-hero" : ""}`} data-testid={hero.selected ? "reference-selected-hero" : "reference-candidate-hero"}><AssetPresentation projectId={projectId} subjectId={subject.id} asset={hero.asset} assetId={hero.assetId} alt={`${subject.name} ${hero.label}`} unavailableLabel={hero.selected ? "当前已选择的身份参考图像不可用" : `${hero.label}图像不可用`} /><figcaption><strong>{hero.label}</strong><span>{hero.asset ? `${hero.asset.width} × ${hero.asset.height}` : "已选择资产缺失"}</span></figcaption></figure> : <div className="reference-no-image" data-testid="reference-no-image"><strong>尚无可显示的图像</strong><p>{candidates.length ? "保留记录未提供可用图像；请查看下方缺失或失败状态。" : "此主体还没有既有候选或已选择参考。"}</p></div>}
    <section className="reference-actions" aria-label={`${subject.name} 的选择与调整`}>
      <section className="reference-task selection-task"><div><span className="eyebrow">选择</span><h3>选用这张图</h3><p>在下方候选卡点击“选用这张图”。审阅者和选择理由会与明确决定一同保存，并受当前版本保护。</p></div><div className="field-grid two compact"><Field label="审阅者"><input value={reviewer} disabled={readOnly || busy} onChange={(event) => setReviewer(event.target.value)} /></Field><Field label="选择理由"><textarea rows={2} value={notes} disabled={readOnly || busy} placeholder="说明为何这张图可作为跨镜头身份参考。" onChange={(event) => setNotes(event.target.value)} /></Field></div></section>
      <section className="reference-task refinement-task"><div><span className="eyebrow">调整</span><h3>基于这张图调整</h3><p>先选一张可识别的父图，再说明你想改什么。创建只冻结提案，不会自动改变当前选择。</p></div><div className="field-grid two compact"><Field label="作为依据的父图"><select value={parentCandidateAssetId} disabled={readOnly || busy} onChange={(event) => setParentCandidateAssetId(event.target.value)}><option value="">不使用已有父图</option>{candidates.filter((candidate) => candidate.proposal.current && candidate.delivery.state === "accepted" && candidate.asset).map((candidate, index) => <option key={candidate.assetId} value={candidate.assetId}>候选图 {index + 1} · {candidate.role === "refinement" ? "细化结果" : "原始研究"}</option>)}</select></Field><Field label="你想改什么"><textarea rows={2} value={direction} disabled={readOnly || busy} placeholder="描述要保留或调整的外观特征。" onChange={(event) => setDirection(event.target.value)} /></Field></div>{selectedParent && <ParentPreview projectId={projectId} subjectId={subject.id} parent={selectedParent} />}<div className="button-row"><Button variant="primary" disabled={readOnly || busy || !direction.trim()} onClick={prepare}>{busy ? "正在创建…" : "创建调整提案"}</Button><small>创建后在提案卡中发送给 specialist；delivery 会自动检查，且不会自动选择。</small></div></section>
      {actionError && <ErrorNotice message={actionError} />}
    </section>
    <section className="reference-alternatives" aria-label={`${subject.name} 的候选和参考`}>
      <header><div><span className="eyebrow">候选与参考</span><h3>比较已有图像</h3></div><small>{candidates.length ? `${candidates.length} 条保留候选记录` : "没有候选记录"}</small></header>
      <div className="reference-card-grid">
        {selectedDecision && selectedDecision.complementaryAssetIds.map((assetId) => <SelectedAssetCard key={`complementary:${assetId}`} projectId={projectId} subjectId={subject.id} asset={assets.get(assetId)} assetId={assetId} />)}
        {candidates.map((candidate) => <CandidateCard key={candidate.id} projectId={projectId} subjectId={subject.id} candidate={candidate} selected={selectedAssetIds.has(candidate.assetId)} parent={candidate.proposal.parentCandidateAssetId ? candidates.find((entry) => entry.assetId === candidate.proposal.parentCandidateAssetId) : undefined} actions={{ readOnly: readOnly || busy, canSelect: Boolean(reviewer.trim() && notes.trim()), onSelect: () => selectCandidate(candidate), onRefine: () => setParentCandidateAssetId(candidate.assetId), onSend: () => send(candidate.proposal), onRefresh: () => refreshProposal(candidate.proposal), onCancel: () => cancel(candidate.proposal) }} />)}
        {incompleteDeliveries.map(({ proposal, delivery }) => <DeliveryEvidenceCard key={`delivery:${delivery.id}`} projectId={projectId} subjectId={subject.id} proposal={proposal} delivery={delivery} parent={proposal.parentCandidateAssetId ? candidates.find((entry) => entry.assetId === proposal.parentCandidateAssetId) : undefined} actions={{ readOnly: readOnly || busy, onSend: () => send(proposal), onRefresh: () => refreshProposal(proposal), onCancel: () => cancel(proposal) }} />)}
        {undeliveredProposals.map((proposal) => <UndeliveredProposalCard key={`proposal:${proposal.id}`} projectId={projectId} subjectId={subject.id} proposal={proposal} parent={proposal.parentCandidateAssetId ? candidates.find((entry) => entry.assetId === proposal.parentCandidateAssetId) : undefined} actions={{ readOnly: readOnly || busy, onSend: () => send(proposal), onRefresh: () => refreshProposal(proposal), onCancel: () => cancel(proposal) }} />)}
        {historicalDecisions.flatMap((decision) => [decision.primaryAssetId, ...decision.complementaryAssetIds].map((assetId) => <HistoricalSelectionCard key={`history:${decision.id}:${assetId}`} projectId={projectId} subjectId={subject.id} decision={decision} asset={assets.get(assetId)} assetId={assetId} />))}
        {!selectedDecision && candidates.length === 0 && incompleteDeliveries.length === 0 && undeliveredProposals.length === 0 && historicalDecisions.length === 0 && <p className="reference-empty-list">尚未选择身份参考，也没有参考候选。</p>}
      </div>
    </section>
    {historicalDecisions.length > 0 && <details className="reference-history"><summary>历史选择说明（不作为当前参考）</summary>{historicalDecisions.map((decision) => <p key={decision.id}>r{decision.referenceRevision} · {decision.revokedAt ? "已撤销" : "已被后续选择取代"} · {decision.notes}</p>)}</details>}
  </section>;
}

function SelectedAssetCard({ projectId, subjectId, asset, assetId }: { projectId: string; subjectId: string; asset: ManagedAsset | undefined; assetId: string }) {
  return <article className="reference-card selected-reference">{<AssetPresentation projectId={projectId} subjectId={subjectId} asset={asset} assetId={assetId} alt="已选择的辅助身份参考" unavailableLabel="已选择的辅助身份参考图像不可用" />}<div><span className="reference-state selected">已选择的辅助参考</span><small>{asset ? `${asset.width} × ${asset.height}` : "资产缺失"}</small></div></article>;
}

type ProposalActions = { readOnly: boolean; onSend: () => void; onRefresh: () => void; onCancel: () => void };
type CandidateActions = ProposalActions & { canSelect: boolean; onSelect: () => void; onRefine: () => void };

function ProposalLifecycle({ proposal, actions }: { proposal: CharacterReferenceProposal; actions: ProposalActions }) {
  return <div className="reference-card-actions"><Button variant="quiet" disabled={actions.readOnly || !proposal.current} onClick={actions.onSend}>发送给 specialist</Button><Button variant="quiet" disabled={actions.readOnly || proposal.state === "cancelled"} onClick={actions.onRefresh}>立即检查交付</Button>{(proposal.state === "prepared" || proposal.state === "exported") && <Button variant="danger" disabled={actions.readOnly} onClick={actions.onCancel}>取消提案</Button>}</div>;
}

function CandidateCard({ projectId, subjectId, candidate, selected, parent, actions }: { projectId: string; subjectId: string; candidate: Candidate; selected: boolean; parent: Candidate | undefined; actions: CandidateActions }) {
  const state = selected ? ["selected", "当前已选择"] as const : candidate.proposal.current && candidate.delivery.state === "accepted" && candidate.asset ? ["candidate", "当前候选，未选择"] as const : candidate.delivery.state !== "accepted" ? ["failed", deliveryLabel(candidate.delivery.state)] as const : ["historical", candidate.proposal.current ? "候选资产缺失" : "历史 / 已过期候选"] as const;
  const direction = frozenDirection(candidate.proposal);
  return <article id={candidateAnchorId(candidate)} className="reference-card" data-testid={`reference-candidate-${candidate.assetId}`} data-proposal-id={candidate.proposal.id} tabIndex={-1}>
    <AssetPresentation projectId={projectId} subjectId={subjectId} asset={candidate.asset ?? undefined} assetId={candidate.assetId} alt={`${state[1]} ${candidate.role === "refinement" ? "细化" : "原始"}候选`} unavailableLabel={`${candidate.role === "refinement" ? "细化" : "原始"}候选图像不可用`} />
    <div className="reference-card-body"><span className={`reference-state ${state[0]}`}>{state[1]}</span><strong>{candidate.role === "refinement" ? "细化候选" : "原始候选"}</strong><small>{candidate.asset ? `${candidate.asset.width} × ${candidate.asset.height}` : "未提供可用资产"}</small>{candidate.proposal.parentCandidateAssetId && <ParentReference projectId={projectId} subjectId={subjectId} assetId={candidate.proposal.parentCandidateAssetId} parent={parent} />}{candidate.proposal.current && candidate.delivery.state === "accepted" && candidate.asset && <div className="reference-card-actions"><Button variant="primary" disabled={actions.readOnly || !actions.canSelect} onClick={actions.onSelect}>选用这张图</Button><Button variant="quiet" disabled={actions.readOnly} onClick={actions.onRefine}>作为调整父图</Button></div>}<ProposalLifecycle proposal={candidate.proposal} actions={actions} /><ProposalDetails proposal={candidate.proposal} delivery={candidate.delivery} outputHash={candidate.outputHash} provenance={candidate.asset?.provenance?.origin} direction={direction} /></div>
  </article>;
}

function DeliveryEvidenceCard({ projectId, subjectId, proposal, delivery, parent, actions }: { projectId: string; subjectId: string; proposal: CharacterReferenceProposal; delivery: CharacterReferenceProposal["deliveries"][number]; parent: Candidate | undefined; actions: ProposalActions }) {
  const direction = frozenDirection(proposal);
  return <article className="reference-card delivery-evidence" data-proposal-id={proposal.id}><div className="reference-missing-asset"><strong>{deliveryLabel(delivery.state)}</strong><small>{delivery.diagnosticCode || "此交付没有可显示的图像输出。"}</small></div><div className="reference-card-body"><span className="reference-state failed">{deliveryLabel(delivery.state)}</span><strong>{proposal.parentCandidateAssetId ? "细化交付" : "原始交付"}</strong>{proposal.parentCandidateAssetId && <ParentReference projectId={projectId} subjectId={subjectId} assetId={proposal.parentCandidateAssetId} parent={parent} />}<ProposalLifecycle proposal={proposal} actions={actions} /><ProposalDetails proposal={proposal} delivery={delivery} direction={direction} /></div></article>;
}

function UndeliveredProposalCard({ projectId, subjectId, proposal, parent, actions }: { projectId: string; subjectId: string; proposal: CharacterReferenceProposal; parent: Candidate | undefined; actions: ProposalActions }) {
  const direction = frozenDirection(proposal);
  const state = proposal.state === "cancelled" ? "已取消，未交付" : proposal.state === "exported" ? "已导出，等待交付" : "已准备，尚未交付";
  return <article className="reference-card delivery-evidence" data-proposal-id={proposal.id}><div className="reference-missing-asset"><strong>{state}</strong><small>没有交付记录，因此没有可显示图像。</small></div><div className="reference-card-body"><span className="reference-state historical">{state}</span><strong>{proposal.parentCandidateAssetId ? "细化提案" : "原始提案"}</strong>{proposal.parentCandidateAssetId && <ParentReference projectId={projectId} subjectId={subjectId} assetId={proposal.parentCandidateAssetId} parent={parent} />}<ProposalLifecycle proposal={proposal} actions={actions} /><ProposalDetails proposal={proposal} direction={direction} /></div></article>;
}

function HistoricalSelectionCard({ projectId, subjectId, decision, asset, assetId }: { projectId: string; subjectId: string; decision: CharacterReferenceDecision; asset: ManagedAsset | undefined; assetId: string }) {
  return <article className="reference-card historical-selection"><AssetPresentation projectId={projectId} subjectId={subjectId} asset={asset} assetId={assetId} alt="历史身份参考，当前不可用" unavailableLabel="历史身份参考图像不可用" /><div className="reference-card-body"><span className="reference-state historical">历史选择，当前不可用</span><strong>身份参考 r{decision.referenceRevision}</strong><small>{asset ? `${asset.width} × ${asset.height}` : "已选择资产缺失"}</small><details className="reference-technical"><summary>技术详情</summary><dl><div><dt>选择</dt><dd>{decision.id}</dd></div><div><dt>状态</dt><dd>{decision.revokedAt ? "revoked" : "superseded_or_stale"}</dd></div><div><dt>备注</dt><dd>{decision.notes}</dd></div>{asset?.provenance && <div><dt>来源</dt><dd>{asset.provenance.origin}</dd></div>}</dl></details></div></article>;
}

function ParentPreview({ projectId, subjectId, parent }: { projectId: string; subjectId: string; parent: Candidate }) {
  return <div className="reference-parent-preview"><AssetPresentation projectId={projectId} subjectId={subjectId} asset={parent.asset ?? undefined} assetId={parent.assetId} alt="作为调整依据的父图" unavailableLabel="所选父图不可用" /><div><strong>当前依据：{parent.role === "refinement" ? "细化候选" : "原始候选"}</strong><small>新提案会保留这张图的父级关系。</small></div></div>;
}

function ProposalDetails({ proposal, delivery, outputHash, provenance, direction }: { proposal: CharacterReferenceProposal; delivery?: CharacterReferenceProposal["deliveries"][number]; outputHash?: string; provenance?: string; direction?: string }) {
  return <details className="reference-technical"><summary>查看生成指令与技术详情</summary>{direction && <><strong>冻结方向</strong><pre>{direction}</pre></>}<dl><div><dt>提案</dt><dd>{proposal.id}</dd></div><div><dt>请求标识</dt><dd>{proposal.requestHash}</dd></div><div><dt>提案状态</dt><dd>{proposal.state}</dd></div>{delivery && <div><dt>交付状态</dt><dd>{delivery.state}</dd></div>}{outputHash && <div><dt>输出标识</dt><dd>{outputHash}</dd></div>}{delivery?.diagnosticCode && <div><dt>诊断</dt><dd>{delivery.diagnosticCode}</dd></div>}{delivery?.manifestHash && <div><dt>交付清单</dt><dd>{delivery.manifestHash}</dd></div>}{provenance && <div><dt>来源</dt><dd>{provenance}</dd></div>}</dl></details>;
}

function AssetPresentation({ projectId, subjectId, asset, assetId, alt, unavailableLabel }: { projectId: string; subjectId: string; asset: ManagedAsset | undefined; assetId: string; alt: string; unavailableLabel: string }) {
  const identity = `${projectId}:${subjectId}:${assetId}`;
  const [failedIdentity, setFailedIdentity] = useState<string | null>(null);
  const unavailable = !asset || failedIdentity === identity;
  if (unavailable) return <MissingAsset assetId={assetId} label={unavailableLabel} />;
  return <img src={plotloomApi.managedAssetUrl(projectId, asset.id)} alt={alt} onError={() => setFailedIdentity(identity)} />;
}

function ParentReference({ projectId, subjectId, assetId, parent }: { projectId: string; subjectId: string; assetId: string; parent: Candidate | undefined }) {
  const parentName = parent ? `${parent.role === "refinement" ? "细化" : "原始"}候选` : "保留父候选";
  const target = parent ? candidateAnchorId(parent) : undefined;
  const focusParent = () => target && document.getElementById(target)?.focus();
  return <div className="reference-parent"><span>来源父图</span>{parent ? <a href={`#${target}`} onClick={focusParent}>{parentName}</a> : <strong>{parentName}（记录缺失）</strong>}<AssetPresentation projectId={projectId} subjectId={subjectId} asset={parent?.asset ?? undefined} assetId={assetId} alt={`${parentName} 缩略图`} unavailableLabel="父候选图像不可用" /></div>;
}

function candidateAnchorId(candidate: Candidate): string { return `reference-candidate-${candidate.id}`; }
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

function frozenDirection(proposal: CharacterReferenceProposal): string | undefined {
  const snapshot = proposal.request.frozenSnapshot;
  return snapshot && typeof snapshot === "object" && typeof (snapshot as Record<string, unknown>).visualDirection === "string" ? (snapshot as Record<string, string>).visualDirection : undefined;
}
function deliveryLabel(state: CharacterReferenceProposal["deliveries"][number]["state"]): string { return state === "inapplicable" ? "已过期 / 不适用交付" : state === "rejected" ? "交付失败 / 已拒绝" : "交付未提供图像"; }
