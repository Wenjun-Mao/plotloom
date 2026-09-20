import { useEffect, useMemo, useRef, useState } from "react";
import type { ReactNode } from "react";

import { plotloomApi } from "../api";
import { ErrorNotice, Spinner } from "../components";
import type { AcceptedCastRevision, CharacterReferenceDecision, CharacterReferenceProposal, ManagedAsset } from "../types";

type GalleryData = {
  title: string;
  castStatus: string;
  accepted: AcceptedCastRevision | null;
  decisions: CharacterReferenceDecision[];
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

/** A viewing-only composition of the F2B owners; authoring stays in the workspace. */
export function CharacterReferenceGalleryPage() {
  const projectId = new URLSearchParams(window.location.search).get("project") || "";
  const [data, setData] = useState<GalleryData>();
  const [error, setError] = useState("");
  const [selectedSubjectId, setSelectedSubjectId] = useState("");
  const requestOwner = useRef(0);

  useEffect(() => {
    if (!projectId) return;
    const owner = ++requestOwner.current;
    setData(undefined); setError(""); setSelectedSubjectId("");
    void Promise.all([
      plotloomApi.getProject(projectId),
      plotloomApi.getCast(projectId),
      plotloomApi.getCharacterReferences(projectId),
      plotloomApi.getCharacterReferenceProposals(projectId),
      plotloomApi.getVisualWorkbench(projectId),
    ]).then(([project, cast, references, proposals, workbench]) => {
      if (requestOwner.current !== owner) return;
      setData({
        title: project.brief.title,
        castStatus: cast.status,
        accepted: cast.acceptedCast,
        decisions: references.decisions,
        proposals: proposals.proposals,
        assets: workbench.assets,
      });
    }).catch((reason: unknown) => {
      if (requestOwner.current === owner) setError(reason instanceof Error ? reason.message : "无法读取角色参考。");
    });
  }, [projectId]);

  const subjects = useMemo(() => data ? gallerySubjects(data.accepted, data.proposals) : [], [data]);
  useEffect(() => {
    if (subjects.length && !subjects.some((subject) => subject.id === selectedSubjectId)) setSelectedSubjectId(subjects[0].id);
  }, [subjects, selectedSubjectId]);
  const selected = subjects.find((subject) => subject.id === selectedSubjectId) || subjects[0];

  if (!projectId) return <GalleryShell><EmptyState title="需要一个项目" message="从已有已接受角色的项目打开此只读图集：在地址中加入 ?view=character-reference-review&project=…" /></GalleryShell>;
  if (error) return <GalleryShell><ErrorNotice message={error} /></GalleryShell>;
  if (!data) return <GalleryShell><div className="reference-gallery-loading"><Spinner label="正在读取角色参考" /></div></GalleryShell>;
  if (!data.accepted) return <GalleryShell><EmptyState title="尚无已接受角色" message="此图集只读取已接受角色及其既有参考；不会创建角色、参考或示例图像。" /></GalleryShell>;
  if (!selected) return <GalleryShell><EmptyState title="角色中没有可查看的主体" message="当前已接受角色未提供可映射的主体；这里不会猜测或创建主体。" /></GalleryShell>;

  return <GalleryShell>
    <header className="reference-gallery-header">
      <a className="brand" href={storyUrl(projectId)}><span className="brand-mark">PL</span><span><strong>Plotloom</strong><small>CREATOR REVIEW</small></span></a>
      <span className="reference-gallery-readonly">只读图像审阅</span>
    </header>
    <main className="reference-gallery" data-testid="character-reference-gallery">
      <CreatorStageNavigation projectId={projectId} />
      <section className="reference-gallery-intro">
        <div><span className="eyebrow">角色参考</span><h1>先看图像，再看技术细节</h1><p>{data.title} · 这里显示已有角色参考的选择、候选和传承关系；不会在此准备、刷新、选择或删除。</p></div>
        <div className={`reference-gallery-cast-state ${data.castStatus === "accepted" ? "current" : "stale"}`}><strong>{data.castStatus === "accepted" ? `已接受角色 r${data.accepted.revision}` : "已接受角色已过期"}</strong><span>{data.castStatus === "accepted" ? "主体来自当前已接受角色。" : "以下内容仅是保留证据，不能作为当前选择或新生成依据。"}</span></div>
      </section>
      <div className="reference-gallery-layout">
        <nav className="reference-subjects" aria-label="角色主体">
          <span>角色主体</span>{subjects.map((subject) => <button key={subject.id} type="button" className={subject.id === selected.id ? "selected" : ""} aria-pressed={subject.id === selected.id} onClick={() => setSelectedSubjectId(subject.id)}><strong>{subject.name}</strong><small>{subject.inAcceptedCast ? "已接受角色" : "仅保留的历史主体"}</small></button>)}
        </nav>
        <SubjectGallery projectId={projectId} subject={selected} data={data} />
      </div>
    </main>
  </GalleryShell>;
}

function SubjectGallery({ projectId, subject, data }: { projectId: string; subject: Subject; data: GalleryData }) {
  const assets = new Map(data.assets.map((asset) => [asset.id, asset]));
  const decisions = data.decisions.filter((decision) => decision.characterId === subject.id);
  const selectedDecision = decisions.find((decision) => decision.current);
  const historicalDecisions = decisions.filter((decision) => !decision.current);
  const candidates = candidateEntries(data.proposals, subject.id).map((candidate) => ({ ...candidate, asset: assets.get(candidate.assetId) ?? candidate.asset }));
  const incompleteDeliveries = data.proposals.filter((proposal) => proposal.characterId === subject.id)
    .flatMap((proposal) => proposal.deliveries.filter((delivery) => delivery.candidates.length === 0).map((delivery) => ({ proposal, delivery })));
  const undeliveredProposals = data.proposals.filter((proposal) => proposal.characterId === subject.id && proposal.deliveries.length === 0);
  const selectedAssetIds = new Set(selectedDecision ? [selectedDecision.primaryAssetId, ...selectedDecision.complementaryAssetIds] : []);
  const selectedAsset = selectedDecision ? assets.get(selectedDecision.primaryAssetId) : undefined;
  const currentCandidate = candidates.find((candidate) => candidate.proposal.current && candidate.delivery.state === "accepted" && candidate.asset);
  const historicalCandidate = candidates.find((candidate) => candidate.asset);
  const hero = selectedAsset ? { asset: selectedAsset, label: "当前已选择的身份参考" } : currentCandidate?.asset ? { asset: currentCandidate.asset, label: "当前候选，尚未选择" } : historicalCandidate?.asset ? { asset: historicalCandidate.asset, label: "历史候选，未被选择" } : undefined;

  return <section className="reference-subject-gallery" aria-labelledby="reference-subject-title">
    <header className="reference-subject-heading"><div><span className="eyebrow">当前主体</span><h2 id="reference-subject-title">{subject.name}</h2><p>{selectedDecision?.current ? `已选择身份参考 r${selectedDecision.referenceRevision}。候选与选择不同：仅明确选择才会成为当前身份参考。` : "尚未选择身份参考。现有候选不会因查看而自动成为选择。"}</p></div><span className={selectedDecision?.current ? "reference-state selected" : "reference-state missing"}>{selectedDecision?.current ? "已选择" : "未选择"}</span></header>
    {hero ? <figure className="reference-hero"><img src={plotloomApi.managedAssetUrl(projectId, hero.asset.id)} alt={`${subject.name} ${hero.label}`} /><figcaption><strong>{hero.label}</strong><span>{hero.asset.width} × {hero.asset.height}</span></figcaption></figure> : <div className="reference-no-image" data-testid="reference-no-image"><strong>尚无可显示的图像</strong><p>{candidates.length ? "保留记录未提供可用图像；请查看下方缺失或失败状态。" : "此主体还没有既有候选或已选择参考。"}</p></div>}
    <section className="reference-alternatives" aria-label={`${subject.name} 的候选和参考`}>
      <header><div><span className="eyebrow">候选与参考</span><h3>比较已有图像</h3></div><small>{candidates.length ? `${candidates.length} 条保留候选记录` : "没有候选记录"}</small></header>
      <div className="reference-card-grid">
        {selectedDecision && selectedDecision.complementaryAssetIds.map((assetId) => <SelectedAssetCard key={`complementary:${assetId}`} projectId={projectId} asset={assets.get(assetId)} assetId={assetId} />)}
        {candidates.map((candidate) => <CandidateCard key={candidate.id} projectId={projectId} candidate={candidate} selected={selectedAssetIds.has(candidate.assetId)} />)}
        {incompleteDeliveries.map(({ proposal, delivery }) => <DeliveryEvidenceCard key={`delivery:${delivery.id}`} proposal={proposal} delivery={delivery} />)}
        {undeliveredProposals.map((proposal) => <UndeliveredProposalCard key={`proposal:${proposal.id}`} proposal={proposal} />)}
        {historicalDecisions.flatMap((decision) => [decision.primaryAssetId, ...decision.complementaryAssetIds].map((assetId) => <HistoricalSelectionCard key={`history:${decision.id}:${assetId}`} projectId={projectId} decision={decision} asset={assets.get(assetId)} assetId={assetId} />))}
        {!selectedDecision && candidates.length === 0 && incompleteDeliveries.length === 0 && undeliveredProposals.length === 0 && historicalDecisions.length === 0 && <p className="reference-empty-list">尚未选择身份参考，也没有参考候选。</p>}
      </div>
    </section>
    {historicalDecisions.length > 0 && <details className="reference-history"><summary>历史选择说明（不作为当前参考）</summary>{historicalDecisions.map((decision) => <p key={decision.id}>r{decision.referenceRevision} · {decision.revokedAt ? "已撤销" : "已被后续选择取代"} · {decision.notes}</p>)}</details>}
  </section>;
}

function SelectedAssetCard({ projectId, asset, assetId }: { projectId: string; asset: ManagedAsset | undefined; assetId: string }) {
  return <article className="reference-card selected-reference">{asset ? <img src={plotloomApi.managedAssetUrl(projectId, asset.id)} alt="已选择的辅助身份参考" /> : <MissingAsset assetId={assetId} />}<div><span className="reference-state selected">已选择的辅助参考</span><small>{asset ? `${asset.width} × ${asset.height}` : "资产缺失"}</small></div></article>;
}

function CandidateCard({ projectId, candidate, selected }: { projectId: string; candidate: Candidate; selected: boolean }) {
  const state = selected ? ["selected", "当前已选择"] as const : candidate.proposal.current && candidate.delivery.state === "accepted" && candidate.asset ? ["candidate", "当前候选，未选择"] as const : candidate.delivery.state !== "accepted" ? ["failed", deliveryLabel(candidate.delivery.state)] as const : ["historical", candidate.proposal.current ? "候选资产缺失" : "历史 / 已过期候选"] as const;
  const direction = frozenDirection(candidate.proposal);
  return <article className="reference-card" data-testid={`reference-candidate-${candidate.assetId}`}>
    {candidate.asset ? <img src={plotloomApi.managedAssetUrl(projectId, candidate.asset.id)} alt={`${state[1]} ${candidate.role === "refinement" ? "细化" : "原始"}候选`} /> : <MissingAsset assetId={candidate.assetId} />}
    <div className="reference-card-body"><span className={`reference-state ${state[0]}`}>{state[1]}</span><strong>{candidate.role === "refinement" ? "细化候选" : "原始候选"}</strong><small>{candidate.asset ? `${candidate.asset.width} × ${candidate.asset.height}` : "未提供可用资产"}</small>{candidate.proposal.parentCandidateAssetId && <p className="reference-parent">细化自 <code>{candidate.proposal.parentCandidateAssetId.slice(0, 12)}</code></p>}{direction && <details className="reference-instructions"><summary>查看生成说明</summary><pre>{direction}</pre></details>}<details className="reference-technical"><summary>技术详情</summary><dl><div><dt>提案</dt><dd>{candidate.proposal.id}</dd></div><div><dt>请求标识</dt><dd>{candidate.proposal.requestHash}</dd></div><div><dt>交付状态</dt><dd>{candidate.delivery.state}</dd></div><div><dt>输出标识</dt><dd>{candidate.outputHash}</dd></div>{candidate.delivery.manifestHash && <div><dt>交付清单</dt><dd>{candidate.delivery.manifestHash}</dd></div>}{candidate.asset?.provenance && <div><dt>来源</dt><dd>{candidate.asset.provenance.origin}</dd></div>}</dl></details></div>
  </article>;
}

function DeliveryEvidenceCard({ proposal, delivery }: { proposal: CharacterReferenceProposal; delivery: CharacterReferenceProposal["deliveries"][number] }) {
  const direction = frozenDirection(proposal);
  return <article className="reference-card delivery-evidence"><div className="reference-missing-asset"><strong>{deliveryLabel(delivery.state)}</strong><small>{delivery.diagnosticCode || "此交付没有可显示的图像输出。"}</small></div><div className="reference-card-body"><span className="reference-state failed">{deliveryLabel(delivery.state)}</span><strong>{proposal.parentCandidateAssetId ? "细化交付" : "原始交付"}</strong>{proposal.parentCandidateAssetId && <p className="reference-parent">细化自 <code>{proposal.parentCandidateAssetId.slice(0, 12)}</code></p>}{direction && <details className="reference-instructions"><summary>查看生成说明</summary><pre>{direction}</pre></details>}<details className="reference-technical"><summary>技术详情</summary><dl><div><dt>提案</dt><dd>{proposal.id}</dd></div><div><dt>请求标识</dt><dd>{proposal.requestHash}</dd></div><div><dt>交付状态</dt><dd>{delivery.state}</dd></div>{delivery.diagnosticCode && <div><dt>诊断</dt><dd>{delivery.diagnosticCode}</dd></div>}{delivery.manifestHash && <div><dt>交付清单</dt><dd>{delivery.manifestHash}</dd></div>}</dl></details></div></article>;
}

function UndeliveredProposalCard({ proposal }: { proposal: CharacterReferenceProposal }) {
  const direction = frozenDirection(proposal);
  const state = proposal.state === "cancelled" ? "已取消，未交付" : proposal.state === "exported" ? "已导出，等待交付" : "已准备，尚未交付";
  return <article className="reference-card delivery-evidence"><div className="reference-missing-asset"><strong>{state}</strong><small>没有交付记录，因此没有可显示图像。</small></div><div className="reference-card-body"><span className="reference-state historical">{state}</span><strong>{proposal.parentCandidateAssetId ? "细化提案" : "原始提案"}</strong>{proposal.parentCandidateAssetId && <p className="reference-parent">细化自 <code>{proposal.parentCandidateAssetId.slice(0, 12)}</code></p>}{direction && <details className="reference-instructions"><summary>查看生成说明</summary><pre>{direction}</pre></details>}<details className="reference-technical"><summary>技术详情</summary><dl><div><dt>提案</dt><dd>{proposal.id}</dd></div><div><dt>请求标识</dt><dd>{proposal.requestHash}</dd></div><div><dt>提案状态</dt><dd>{proposal.state}</dd></div></dl></details></div></article>;
}

function HistoricalSelectionCard({ projectId, decision, asset, assetId }: { projectId: string; decision: CharacterReferenceDecision; asset: ManagedAsset | undefined; assetId: string }) {
  return <article className="reference-card historical-selection">{asset ? <img src={plotloomApi.managedAssetUrl(projectId, asset.id)} alt="历史身份参考，当前不可用" /> : <MissingAsset assetId={assetId} />}<div className="reference-card-body"><span className="reference-state historical">历史选择，当前不可用</span><strong>身份参考 r{decision.referenceRevision}</strong><small>{asset ? `${asset.width} × ${asset.height}` : "已选择资产缺失"}</small><details className="reference-technical"><summary>技术详情</summary><dl><div><dt>选择</dt><dd>{decision.id}</dd></div><div><dt>状态</dt><dd>{decision.revokedAt ? "revoked" : "superseded_or_stale"}</dd></div><div><dt>备注</dt><dd>{decision.notes}</dd></div>{asset?.provenance && <div><dt>来源</dt><dd>{asset.provenance.origin}</dd></div>}</dl></details></div></article>;
}

function MissingAsset({ assetId }: { assetId: string }) { return <div className="reference-missing-asset"><strong>图像不可用</strong><small>保留资产 {assetId.slice(0, 12)} 缺失或交付未产生可显示文件。</small></div>; }
function GalleryShell({ children }: { children: ReactNode }) { return <div className="reference-gallery-shell">{children}</div>; }
function EmptyState({ title, message }: { title: string; message: string }) { return <section className="reference-gallery-empty"><strong>{title}</strong><p>{message}</p></section>; }

function CreatorStageNavigation({ projectId }: { projectId: string }) {
  const workspaceUrl = (stage: string) => `?${new URLSearchParams({ project: projectId, stage }).toString()}`;
  return <nav className="creator-stage-navigation" aria-label="创作阶段"><a href={workspaceUrl("source")}>来源</a><span>故事</span><a href={workspaceUrl("bible")}>人物、地点、道具</a><span className="current" aria-current="step">美术 · 人物参考</span><a href={storyUrl(projectId)}>剧本</a><a href={workspaceUrl("storyboard")}>分镜</a><span className="unavailable">制作 · 尚未提供</span><a href={`?${new URLSearchParams({ project: projectId, view: "play" }).toString()}`}>播放</a></nav>;
}

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
function storyUrl(projectId: string): string { return `?${new URLSearchParams({ project: projectId, view: "story-prototype" }).toString()}`; }
