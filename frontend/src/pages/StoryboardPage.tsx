import { useEffect, useMemo, useRef, useState } from "react";
import type {
  ApprovalDecision,
  AudioEvent,
  MediaTask,
  RequiredEntityState,
  SceneBeatPlan,
  Shot,
  ShotBeatLink,
  StoryBible,
  StoryGraph,
  Storyboard,
  StoryboardReview,
  ValidationIssue,
} from "../types";
import { plotloomApi } from "../api";
import type { ProjectDraftQuiescence } from "../features/authoring/projectDraftQuiescence";
import { deriveRoutes, groupStoryboard } from "../model";
import {
  addAudioEvent,
  addShot,
  addShotBeatLink,
  assignCue,
  beatCoverage,
  createShot,
  cueLabel,
  cueSchedule,
  encodeStoryboardEntity,
  moveShot,
  migrateShotToScene,
  parseStoryboardEntity,
  patchAudioEvent,
  patchShot,
  patchShotBeatLink,
  removeAudioEvent,
  removeShot,
  removeShotBeatLink,
  shotRemovalImpact,
  shotSceneMigrationImpact,
  storyboardFocusKey,
  storyboardIssueEntity,
  storyboardIssueTarget,
  type ShotRemovalImpact,
  unassignCue,
  type ShotSceneMigrationImpact,
  type StoryboardIssueTarget,
} from "../storyboard-editor";
import {
  ContinuityStateEditor,
  EntityStateEditor,
  type EntityOption,
} from "../structured-fields";
import { Badge, Button, EmptyState, Field, PageHeader, Panel } from "../components";
import { ManagedMediaWorkbench } from "../managed-media";

const shotSizes: Array<{ value: Shot["shotSize"]; label: string }> = [
  { value: "extreme_wide", label: "大远景" },
  { value: "wide", label: "全景" },
  { value: "full", label: "全身" },
  { value: "medium", label: "中景" },
  { value: "close_up", label: "近景" },
  { value: "extreme_close_up", label: "特写" },
  { value: "insert", label: "插入镜头" },
];

const audioKinds: Array<{ value: AudioEvent["kind"]; label: string }> = [
  { value: "ambience", label: "环境声" },
  { value: "sound_effect", label: "音效" },
  { value: "diegetic_sound", label: "画内声音" },
  { value: "diegetic_music", label: "画内音乐" },
  { value: "score", label: "配乐" },
];

function stableId(prefix: string): string {
  return `${prefix}_${crypto.randomUUID()}`;
}

function referenceOptions(bible: StoryBible): EntityOption[] {
  return [
    ...bible.characters.map((entity) => ({ type: "character" as const, id: entity.id, label: `角色 · ${entity.name}`, states: entity.allowedStates })),
    ...bible.locations.map((entity) => ({ type: "location" as const, id: entity.id, label: `地点 · ${entity.name}`, states: entity.allowedStates })),
    ...bible.props.map((entity) => ({ type: "prop" as const, id: entity.id, label: `道具 · ${entity.name}`, states: entity.allowedStates })),
  ];
}

function GateStatusBadge({ status }: { status: "pass" | "fail" | "skipped" | "not_applicable" }) {
  const tone = status === "pass" ? "ok" : status === "fail" ? "danger" : "warning";
  return <Badge tone={tone}>{status.toUpperCase()}</Badge>;
}

function ShotMigrationConfirmation({ impact, onCancel, onConfirm }: { impact: ShotSceneMigrationImpact; onCancel: () => void; onConfirm: () => void }) {
  return <Panel className="notice warning" data-testid="shot-scene-migration-impact"><strong>镜头关系迁移确认</strong><p>将 Shot {impact.shotId} 从 {impact.fromSceneId} 迁移到 {impact.toSceneId}。Shot ID 不变，两个场景的镜头顺序会确定性归一化。</p><small>不会自动删除或迁移关联关系。迁移后跨场景的 cue 调度：{impact.crossSceneCueIds.join(", ") || "无"}；ShotBeatLink：{impact.crossSceneLinkKeys.join(", ") || "无"}。请在确认后显式调整这些关系。</small><div className="page-actions"><Button type="button" variant="primary" onClick={onConfirm}>确认迁移</Button><Button type="button" onClick={onCancel}>取消</Button></div></Panel>;
}

function ShotDeletionConfirmation({ impact, title, onCancel, onConfirm }: { impact: ShotRemovalImpact; title: string; onCancel: () => void; onConfirm: () => void }) {
  return <Panel className="notice error" data-testid="shot-deletion-impact" role="alertdialog" aria-label="镜头删除影响确认">
    <strong>删除镜头“{title}”</strong>
    <p>镜头 {impact.shotId} 将被删除；同场景镜头顺序会重新编号。以下关系不会被隐藏处理：</p>
    <ul>
      {impact.linkBeatIds.map((beatId) => <li key={`link:${beatId}`}>删除 ShotBeatLink：{impact.shotId} → {beatId}</li>)}
      {impact.unscheduledCueIds.map((cueId) => <li key={`cue:${cueId}`}>DialogueCue 将变为未调度：{cueId}</li>)}
      {!impact.linkBeatIds.length && !impact.unscheduledCueIds.length && <li>没有 ShotBeatLink 或 DialogueCue 调度关系。</li>}
    </ul>
    <div className="page-actions"><Button type="button" variant="danger" data-testid="confirm-shot-delete" onClick={onConfirm}>确认删除</Button><Button type="button" onClick={onCancel}>取消</Button></div>
  </Panel>;
}

export function StoryboardPage({
  bible,
  graph,
  sceneBeats,
  value,
  stale,
  mediaTasks,
  saving,
  entityId,
  issues = [],
  onEntitySelect,
  onNavigateIssue,
  onReturnToBridge,
  review = null,
  onReviewChange,
  onSave,
  onDraftChange,
  projectId,
  revision,
  storyBibleRevision,
  contentHash,
  mediaDraftsEnabled = false,
  mediaDraftQuiescence,
}: {
  bible: StoryBible;
  graph: StoryGraph;
  sceneBeats: SceneBeatPlan;
  value: Storyboard;
  stale: boolean;
  mediaTasks: Record<string, MediaTask>;
  saving: boolean;
  entityId?: string;
  issues?: ValidationIssue[];
  onEntitySelect?: (entityId: string) => void;
  onNavigateIssue?: (stage: "beats" | "storyboard", entityId: string) => void;
  onReturnToBridge?: () => void;
  // The workspace owns the review projection because the Inspector and this
  // editor must make decisions from the same revision and gate receipt.
  review?: StoryboardReview | null;
  onReviewChange?: (review: StoryboardReview | null) => void;
  onSave: (storyboard: Storyboard) => Promise<void>;
  onDraftChange?: (storyboard: Storyboard) => void;
  projectId?: string;
  revision?: number;
  storyBibleRevision?: number;
  contentHash?: string | null;
  mediaDraftsEnabled?: boolean;
  mediaDraftQuiescence?: ProjectDraftQuiescence;
}) {
  const [storyboard, setStoryboard] = useState(value);
  const routes = useMemo(() => deriveRoutes(graph), [graph]);
  const [routeId, setRouteId] = useState("");
  const [selectedShotId, setSelectedShotId] = useState(value.shots[0]?.id ?? "");
  const [reviewError, setReviewError] = useState("");
  const [reviewer, setReviewer] = useState("");
  const [reviewNote, setReviewNote] = useState("");
  const [localError, setLocalError] = useState("");
  const [newLinkBeatId, setNewLinkBeatId] = useState("");
  const [newLinkRole, setNewLinkRole] = useState<ShotBeatLink["role"]>("supporting");
  const [pendingSceneMigration, setPendingSceneMigration] = useState<ShotSceneMigrationImpact | null>(null);
  const [pendingShotDeletion, setPendingShotDeletion] = useState<ShotRemovalImpact | null>(null);
  const [issueFocus, setIssueFocus] = useState<StoryboardIssueTarget | null>(null);
  const lastIssueSignature = useRef<string | undefined>(undefined);
  const storyboardDetails = useRef<HTMLDetailsElement>(null);
  const approvalActions = useRef<HTMLDetailsElement>(null);
  const enteredUnapprovedEditing = useRef(false);
  const reviewProjectId = useRef(projectId);
  const issueSignature = JSON.stringify(issues);

  useEffect(() => {
    if (reviewProjectId.current !== projectId) {
      reviewProjectId.current = projectId;
      enteredUnapprovedEditing.current = false;
    }
    if (!review) return;
    if (!review.activeApproval) {
      enteredUnapprovedEditing.current = true;
      if (storyboardDetails.current) storyboardDetails.current.open = true;
      if (approvalActions.current) approvalActions.current.open = true;
    } else if (!enteredUnapprovedEditing.current) {
      // Reopening an already-approved board starts at media review. A creator
      // who just approved an open edit session does not lose their draft view.
      if (storyboardDetails.current) storyboardDetails.current.open = false;
      if (approvalActions.current) approvalActions.current.open = false;
    }
  }, [projectId, Boolean(review), review?.activeApproval?.id, review?.gateEvaluation?.gateSetVersion]);

  const update = (next: Storyboard | ((current: Storyboard) => Storyboard)) => {
    setStoryboard((current) => {
      const updated = typeof next === "function" ? next(current) : next;
      onDraftChange?.(updated);
      return updated;
    });
  };
  const selectShot = (shotId: string) => {
    setSelectedShotId(shotId);
    onEntitySelect?.(encodeStoryboardEntity({ kind: "shot", shotId }));
  };
  const revealStoryboardEditor = () => {
    if (storyboardDetails.current) storyboardDetails.current.open = true;
    requestAnimationFrame(() => document.getElementById("storyboard-structure")?.scrollIntoView({ block: "start" }));
  };
  const editShot = (shotId: string) => {
    selectShot(shotId);
    revealStoryboardEditor();
  };
  const focusIssue = (issue: ValidationIssue) => {
    const target = storyboardIssueTarget(storyboard, issue);
    if (!target) return;
    if (storyboardDetails.current) storyboardDetails.current.open = true;
    setSelectedShotId(target.entity.shotId);
    onEntitySelect?.(encodeStoryboardEntity(target.entity));
    setIssueFocus(target);
  };

  useEffect(() => {
    const parsed = parseStoryboardEntity(entityId ?? "");
    const shotId = parsed?.shotId;
    if (shotId && storyboard.shots.some((shot) => shot.id === shotId)) {
      setSelectedShotId(shotId);
    } else if (!entityId && storyboard.shots[0]) {
      setSelectedShotId(storyboard.shots[0].id);
    } else {
      setSelectedShotId("");
    }
  }, [entityId, storyboard.shots]);

  useEffect(() => {
    if (!issues.length) { lastIssueSignature.current = undefined; setIssueFocus(null); return; }
    if (issueSignature === lastIssueSignature.current) return;
    lastIssueSignature.current = issueSignature;
    const issue = issues.find((candidate) => storyboardIssueTarget(storyboard, candidate));
    if (issue) focusIssue(issue);
  }, [issueSignature, issues, storyboard]);

  useEffect(() => {
    if (!issueFocus || selectedShotId !== issueFocus.entity.shotId) return;
    if (storyboardDetails.current) storyboardDetails.current.open = true;
    const key = storyboardFocusKey(issueFocus);
    const target = [...document.querySelectorAll<HTMLElement>("[data-focus-key]")]
      .find((element) => element.dataset.focusKey === key)
      ?? [...document.querySelectorAll<HTMLElement>("[data-focus-key]")]
        .find((element) => issueFocus.field.includes(".") && element.dataset.focusKey === storyboardFocusKey({ ...issueFocus, field: issueFocus.field.split(".")[0] }))
      ?? [...document.querySelectorAll<HTMLElement>("[data-entity-key]")]
        .find((element) => element.dataset.entityKey === encodeStoryboardEntity(issueFocus.entity));
    let disclosure = target?.closest("details");
    while (disclosure) { disclosure.open = true; disclosure = disclosure.parentElement?.closest("details") ?? null; }
    target?.focus();
  }, [issueFocus, selectedShotId]);

  const route = routes.find((candidate) => candidate.id === routeId);
  const visible = groupStoryboard(storyboard, sceneBeats, route);
  const requestedShotId = entityId ? parseStoryboardEntity(entityId)?.shotId : undefined;
  const unresolvedEntity = Boolean(entityId && (!requestedShotId || !storyboard.shots.some((shot) => shot.id === requestedShotId)));
  const selectedShot = unresolvedEntity || (requestedShotId && selectedShotId !== requestedShotId)
    ? undefined : storyboard.shots.find((shot) => shot.id === selectedShotId);
  const selectedImageTask = selectedShot ? mediaTasks[`${selectedShot.id}:image`] : undefined;
  const selectedVideoTask = selectedShot ? mediaTasks[`${selectedShot.id}:video`] : undefined;
  const allEntityOptions = useMemo(() => referenceOptions(bible), [bible]);
  const scopedStateOptions = selectedShot ? allEntityOptions.filter((option) => (
    option.type === "character" ? selectedShot.characterIds.includes(option.id)
      : option.type === "location" ? selectedShot.locationId === option.id
        : selectedShot.propIds.includes(option.id)
  )) : [];
  const schedule = useMemo(() => cueSchedule(storyboard), [storyboard]);
  const coverage = useMemo(() => beatCoverage(storyboard, sceneBeats.beats), [storyboard, sceneBeats.beats]);
  const sceneCues = selectedShot ? sceneBeats.dialogueCues.filter((cue) => {
    const beat = sceneBeats.beats.find((candidate) => candidate.id === cue.beatId);
    return beat?.sceneId === selectedShot.sceneId;
  }).sort((left, right) => {
    const leftBeat = sceneBeats.beats.find((beat) => beat.id === left.beatId)?.order ?? 0;
    const rightBeat = sceneBeats.beats.find((beat) => beat.id === right.beatId)?.order ?? 0;
    return leftBeat - rightBeat || left.order - right.order;
  }) : [];
  const sceneBeatsForShot = selectedShot
    ? sceneBeats.beats.filter((beat) => beat.sceneId === selectedShot.sceneId).sort((left, right) => left.order - right.order)
    : [];
  const linksForShot = selectedShot
    ? storyboard.shotBeatLinks.filter((link) => link.shotId === selectedShot.id)
    : [];

  const applyShotPatch = (patch: Partial<Shot>) => {
    if (!selectedShot) return;
    update((current) => patchShot(current, selectedShot.id, patch));
  };
  const applyShotTransform = (transform: (shot: Shot) => Shot) => {
    if (!selectedShot) return;
    update((current) => patchShot(current, selectedShot.id, transform(current.shots.find((shot) => shot.id === selectedShot.id)!)));
  };
  const addShotToScene = (sceneId: string) => {
    const scene = sceneBeats.scenes.find((candidate) => candidate.id === sceneId);
    if (!scene) return;
    const order = storyboard.shots.filter((shot) => shot.sceneId === sceneId).length + 1;
    const shot = createShot(stableId("shot"), sceneId, order, {
      characterIds: scene.characterIds,
      locationId: scene.locationId,
      entryState: scene.entryState,
      exitState: scene.exitState,
    });
    update((current) => addShot(current, shot));
    selectShot(shot.id);
  };
  const requestShotSceneMigration = (sceneId: string) => {
    if (!selectedShot || selectedShot.sceneId === sceneId) return;
    try {
      setPendingSceneMigration(shotSceneMigrationImpact(storyboard, sceneBeats, selectedShot.id, sceneId));
      setLocalError("");
    } catch (error) {
      setLocalError(error instanceof Error ? error.message : "无法迁移镜头");
    }
  };
  const deleteSelectedShot = () => {
    if (!selectedShot) return;
    setPendingShotDeletion(shotRemovalImpact(storyboard, selectedShot.id));
  };
  const confirmShotDeletion = () => {
    if (!pendingShotDeletion) return;
    const removed = storyboard.shots.find((shot) => shot.id === pendingShotDeletion.shotId);
    if (!removed) { setPendingShotDeletion(null); return; }
    const next = removeShot(storyboard, removed.id);
    update(next);
    const replacement = next.shots.find((shot) => shot.sceneId === removed.sceneId) ?? next.shots[0];
    setSelectedShotId(replacement?.id ?? "");
    onEntitySelect?.(replacement ? encodeStoryboardEntity({ kind: "shot", shotId: replacement.id }) : "");
    setPendingShotDeletion(null);
  };
  const toggleCue = (cueId: string, checked: boolean) => {
    if (!selectedShot) return;
    try {
      update((current) => checked ? assignCue(current, selectedShot.id, cueId) : unassignCue(current, selectedShot.id, cueId));
      setLocalError("");
    } catch (error) {
      setLocalError(error instanceof Error ? error.message : "对白调度失败");
    }
  };
  const addCoverageLink = () => {
    if (!selectedShot || !newLinkBeatId) return;
    try {
      update((current) => addShotBeatLink(current, {
        shotId: selectedShot.id,
        beatId: newLinkBeatId,
        role: newLinkRole,
        coverageWeight: 1,
      }));
      setNewLinkBeatId(""); setLocalError("");
    } catch (error) {
      setLocalError(error instanceof Error ? error.message : "覆盖关系创建失败");
    }
  };
  const decide = async (decision: ApprovalDecision["decision"]) => {
    if (!projectId || !contentHash || revision === undefined || !review?.gateEvaluation || !reviewer.trim()) return;
    setReviewError("");
    try {
      await plotloomApi.decideStoryboardApproval(projectId, {
        expectedRevision: revision,
        contentHash,
        decision,
        reviewer,
        gateSetVersion: review.gateEvaluation.gateSetVersion,
        note: reviewNote.trim() || undefined,
      });
      const nextReview = await plotloomApi.getStoryboardReview(projectId);
      onReviewChange?.(nextReview);
      setReviewNote("");
    } catch (error) {
      setReviewError(error instanceof Error ? error.message : "Approval 决定未保存");
    }
  };
  const navigateGate = (path: Array<string | number>) => {
    const [root, identity] = path;
    if (root === "shots" && identity !== undefined) {
      const target = storyboardIssueEntity(storyboard, { code: "gate", path: `shots.${identity}`, message: "" });
      if (target) editShot(target.shotId);
    } else if (root === "shotBeatLinks" && identity !== undefined) {
      const target = storyboardIssueEntity(storyboard, { code: "gate", path: `shotBeatLinks.${identity}`, message: "" });
      if (target) editShot(target.shotId);
    } else if (root === "scenes" && identity !== undefined) {
      onNavigateIssue?.("beats", `scene:${identity}`);
    } else if (root === "beats" && identity !== undefined) {
      onNavigateIssue?.("beats", `beat:${identity}`);
    } else if (root === "dialogueCues" && identity !== undefined) {
      onNavigateIssue?.("beats", `cue:${identity}`);
    }
  };
  const requiredGatesPass = Boolean(review?.gateEvaluation?.results.every((gate) => !gate.required || gate.status === "pass"));

  return <div className="page storyboard-page" data-testid="storyboard-editor">
    <PageHeader title="分镜工作台" description="镜头、对白、声音、实体状态与节拍覆盖都在同一份可审计合同中。" actions={<>
      <Field label="路径过滤"><select value={routeId} onChange={(event) => setRouteId(event.target.value)}><option value="">全部场景</option>{routes.map((item, index) => <option key={item.id} value={item.id}>路径 {index + 1} · {item.label}</option>)}</select></Field>
      <Button variant="primary" disabled={saving} onClick={() => void onSave(storyboard)}>{saving ? "正在保存…" : "保存分镜"}</Button>
    </>} />
    {stale && <div className="notice warning"><strong>分镜已过期</strong><span>上游合同发生变化。现有手工镜头仍保留；请审阅差异后从合适阶段重建。</span></div>}
    <div className="notice"><strong>媒体工作流</strong><span>选择镜头后，在下方查看原片、调整并预览片段，再明确决定是否用于故事。关键帧、参考素材与准备步骤可展开；未配置视频后端时仍可查看已有候选。</span></div>
    {unresolvedEntity && <div className="notice warning" role="alert" data-testid="unknown-storyboard-entity">请求的镜头不属于当前分镜；未打开其他镜头。请从镜头列表重新选择。</div>}
    <ManagedMediaWorkbench projectId={projectId} storyboard={storyboard} bible={bible} graph={graph} sceneBeats={sceneBeats} routeId={route?.id} storyboardRevision={revision} storyBibleRevision={storyBibleRevision} mediaDraftsEnabled={mediaDraftsEnabled} draftQuiescence={mediaDraftQuiescence} selectedShot={selectedShot} review={review} draftChanged={JSON.stringify(storyboard) !== JSON.stringify(value)} readOnly={saving} onSelectShot={selectShot} onEditShot={revealStoryboardEditor} onReturnToBridge={onReturnToBridge} onReview={() => {
      if (storyboardDetails.current) storyboardDetails.current.open = true;
      if (approvalActions.current) approvalActions.current.open = true;
      requestAnimationFrame(() => {
        const panel = document.getElementById("storyboard-review");
        panel?.scrollIntoView({ block: "start" });
        panel?.focus({ preventScroll: true });
      });
    }} />
    {(issues.length > 0 || localError) && <Panel className="issue-summary"><strong>需要修正</strong>{localError && <p role="alert">{localError}</p>}{issues.map((issue) => <button key={`${issue.code}:${issue.path}`} onClick={() => focusIssue(issue)}>{issue.code} · {issue.path}<small>{issue.message}</small></button>)}</Panel>}

    {pendingSceneMigration && <ShotMigrationConfirmation impact={pendingSceneMigration} onCancel={() => setPendingSceneMigration(null)} onConfirm={() => { const migration = pendingSceneMigration; update((current) => migrateShotToScene(current, migration.shotId, migration.toSceneId)); setPendingSceneMigration(null); }} />}
    {pendingShotDeletion && <ShotDeletionConfirmation impact={pendingShotDeletion} title={storyboard.shots.find((shot) => shot.id === pendingShotDeletion.shotId)?.title ?? pendingShotDeletion.shotId} onCancel={() => setPendingShotDeletion(null)} onConfirm={confirmShotDeletion} />}
    <details className="storyboard-editor-disclosure" id="storyboard-structure" ref={storyboardDetails}>
      <summary>分镜结构与详细编辑 · {storyboard.shots.length} 个镜头</summary>
    <div className="storyboard-layout">
      <div className="shot-groups">
        {!visible.length && <EmptyState title="这条路径没有分镜">切换到“全部场景”或先生成 storyboard 阶段。</EmptyState>}
        {visible.map((group, groupIndex) => <section className="shot-group" key={group.sceneId}>
          <header><div><span>{String(groupIndex + 1).padStart(2, "0")}</span><strong>{group.title}</strong></div><div><small>{group.shots.length} shots · node {group.storyNodeId}</small><Button variant="quiet" data-testid={`add-shot-${group.sceneId}`} onClick={() => addShotToScene(group.sceneId)}>＋ 镜头</Button></div></header>
          <div className="shot-strip">
            {group.shots.map((shot) => {
              const imageTask = mediaTasks[`${shot.id}:image`];
              const shotLinks = storyboard.shotBeatLinks.filter((link) => link.shotId === shot.id);
              return <article key={shot.id} data-entity-key={encodeStoryboardEntity({ kind: "shot", shotId: shot.id })} className={`shot-card ${shot.id === selectedShotId ? "selected" : ""}`} onClick={() => editShot(shot.id)}>
                <button className="shot-select" aria-label={`编辑镜头 ${shot.title}`} onClick={(event) => { event.stopPropagation(); editShot(shot.id); }}>
                  <div className="shot-frame">{imageTask?.outputUri ? <img src={imageTask.outputUri} alt={`${shot.title} 历史关键帧`} /> : <span>{String(shot.order).padStart(2, "0")}</span>}{stale && <Badge tone="warning">STALE</Badge>}</div>
                  <div className="shot-copy"><strong>{shot.title}</strong><small>{shot.shotSize} · {shot.durationUnits}ms · {shotLinks.length} links</small><p>{shot.action}</p></div>
                </button>
                <div className="media-controls"><small>图片：查看关键帧与参考素材</small><small>视频：在上方工作台审核片段</small></div>
              </article>;
            })}
          </div>
        </section>)}
      </div>

      <Panel className="shot-inspector" data-focus-key={selectedShot ? storyboardFocusKey({ entity: { kind: "shot", shotId: selectedShot.id }, field: "entity" }) : undefined} tabIndex={selectedShot ? -1 : undefined}>
        <div className="section-title"><span>Shot inspector</span><strong>{selectedShot?.title || "选择镜头"}</strong></div>
        {selectedShot && <>
          <Field label="镜头 ID"><input data-focus-key={storyboardFocusKey({ entity: { kind: "shot", shotId: selectedShot.id }, field: "id" })} readOnly value={selectedShot.id} /></Field>
          <Field label="所属场景"><select data-focus-key={storyboardFocusKey({ entity: { kind: "shot", shotId: selectedShot.id }, field: "sceneId" })} aria-label="迁移镜头到场景" value={selectedShot.sceneId} onChange={(event) => requestShotSceneMigration(event.target.value)}>{sceneBeats.scenes.map((scene) => <option key={scene.id} value={scene.id}>{scene.title || scene.id} · {scene.id}</option>)}</select></Field>
          <div className="button-row"><Button variant="quiet" onClick={() => update((current) => moveShot(current, selectedShot.id, -1))}>上移</Button><Button variant="quiet" onClick={() => update((current) => moveShot(current, selectedShot.id, 1))}>下移</Button><Button variant="danger" onClick={deleteSelectedShot}>删除镜头</Button></div>
          <Field label="标题"><input data-focus-key={storyboardFocusKey({ entity: { kind: "shot", shotId: selectedShot.id }, field: "title" })} value={selectedShot.title} onChange={(event) => applyShotPatch({ title: event.target.value })} /></Field>
          <div className="field-grid two compact"><Field label="景别"><select data-focus-key={storyboardFocusKey({ entity: { kind: "shot", shotId: selectedShot.id }, field: "shotSize" })} value={selectedShot.shotSize} onChange={(event) => applyShotPatch({ shotSize: event.target.value as Shot["shotSize"] })}>{shotSizes.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}</select></Field><Field label="时长（毫秒）"><input data-focus-key={storyboardFocusKey({ entity: { kind: "shot", shotId: selectedShot.id }, field: "durationUnits" })} type="number" min={1} value={selectedShot.durationUnits} onChange={(event) => applyShotPatch({ durationUnits: Math.max(1, Number(event.target.value)) })} /></Field></div>
          <div className="field-grid two compact"><Field label="机位角度"><input data-focus-key={storyboardFocusKey({ entity: { kind: "shot", shotId: selectedShot.id }, field: "cameraAngle" })} value={selectedShot.cameraAngle} onChange={(event) => applyShotPatch({ cameraAngle: event.target.value })} /></Field><Field label="运镜"><input data-focus-key={storyboardFocusKey({ entity: { kind: "shot", shotId: selectedShot.id }, field: "cameraMovement" })} value={selectedShot.cameraMovement} onChange={(event) => applyShotPatch({ cameraMovement: event.target.value })} /></Field></div>
          <Field label="构图"><textarea data-focus-key={storyboardFocusKey({ entity: { kind: "shot", shotId: selectedShot.id }, field: "composition" })} rows={2} value={selectedShot.composition} onChange={(event) => applyShotPatch({ composition: event.target.value })} /></Field>
          <div className="field-grid two compact"><Field label="视觉意图"><textarea data-focus-key={storyboardFocusKey({ entity: { kind: "shot", shotId: selectedShot.id }, field: "visualIntent" })} rows={2} value={selectedShot.visualIntent} onChange={(event) => applyShotPatch({ visualIntent: event.target.value })} /></Field><Field label="动态意图"><textarea data-focus-key={storyboardFocusKey({ entity: { kind: "shot", shotId: selectedShot.id }, field: "motionIntent" })} rows={2} value={selectedShot.motionIntent} onChange={(event) => applyShotPatch({ motionIntent: event.target.value })} /></Field></div>
          <Field label="动作"><textarea data-focus-key={storyboardFocusKey({ entity: { kind: "shot", shotId: selectedShot.id }, field: "action" })} rows={4} value={selectedShot.action} onChange={(event) => applyShotPatch({ action: event.target.value })} /></Field>
          <Field label="转场"><input data-focus-key={storyboardFocusKey({ entity: { kind: "shot", shotId: selectedShot.id }, field: "transition" })} value={selectedShot.transition} onChange={(event) => applyShotPatch({ transition: event.target.value })} /></Field>

          <fieldset className="structured-editor" data-focus-key={storyboardFocusKey({ entity: { kind: "shot", shotId: selectedShot.id }, field: "characterIds" })} tabIndex={-1}><legend>角色引用</legend>{bible.characters.map((character) => <label className="check-row" key={character.id}><input type="checkbox" checked={selectedShot.characterIds.includes(character.id)} onChange={(event) => applyShotPatch({ characterIds: event.target.checked ? [...selectedShot.characterIds, character.id] : selectedShot.characterIds.filter((id) => id !== character.id) })} />{character.name} · {character.id}</label>)}</fieldset>
          <Field label="地点引用"><select data-focus-key={storyboardFocusKey({ entity: { kind: "shot", shotId: selectedShot.id }, field: "locationId" })} value={selectedShot.locationId ?? ""} onChange={(event) => applyShotPatch({ locationId: event.target.value || null })}><option value="">无</option>{bible.locations.map((location) => <option key={location.id} value={location.id}>{location.name} · {location.id}</option>)}</select></Field>
          <fieldset className="structured-editor" data-focus-key={storyboardFocusKey({ entity: { kind: "shot", shotId: selectedShot.id }, field: "propIds" })} tabIndex={-1}><legend>道具引用</legend>{bible.props.map((prop) => <label className="check-row" key={prop.id}><input type="checkbox" checked={selectedShot.propIds.includes(prop.id)} onChange={(event) => applyShotPatch({ propIds: event.target.checked ? [...selectedShot.propIds, prop.id] : selectedShot.propIds.filter((id) => id !== prop.id) })} />{prop.name} · {prop.id}</label>)}</fieldset>
          <EntityStateEditor focusKey={storyboardFocusKey({ entity: { kind: "shot", shotId: selectedShot.id }, field: "requiredEntityStates" })} label="镜头要求的实体状态" value={selectedShot.requiredEntityStates} options={scopedStateOptions} onChange={(requiredEntityStates: RequiredEntityState[]) => applyShotPatch({ requiredEntityStates })} />
          <ContinuityStateEditor focusKey={storyboardFocusKey({ entity: { kind: "shot", shotId: selectedShot.id }, field: "entryState" })} label="镜头入口连续性" value={selectedShot.entryState} options={allEntityOptions} onChange={(entryState) => applyShotPatch({ entryState })} />
          <ContinuityStateEditor focusKey={storyboardFocusKey({ entity: { kind: "shot", shotId: selectedShot.id }, field: "exitState" })} label="镜头出口连续性" value={selectedShot.exitState} options={allEntityOptions} onChange={(exitState) => applyShotPatch({ exitState })} />

          <fieldset className="structured-editor" data-focus-key={storyboardFocusKey({ entity: { kind: "shot", shotId: selectedShot.id }, field: "cueIds" })} tabIndex={-1}><legend>对白调度</legend>{sceneCues.map((cue) => {
            const scheduledBy = schedule.get(cue.id) ?? [];
            const elsewhere = scheduledBy.some((shotId) => shotId !== selectedShot.id);
            return <label className="check-row" key={cue.id}><input type="checkbox" checked={selectedShot.cueIds.includes(cue.id)} disabled={elsewhere} onChange={(event) => toggleCue(cue.id, event.target.checked)} /><span>{cueLabel(cue)}{elsewhere ? ` · 已由 ${scheduledBy.join(", ")} 调度` : ""}</span></label>;
          })}{!sceneCues.length && <small>此场景没有 DialogueCue。</small>}<small>已调度对白 {selectedShot.cueIds.reduce((total, id) => total + (sceneBeats.dialogueCues.find((cue) => cue.id === id)?.estimatedDurationUnits ?? 0), 0)} / {selectedShot.durationUnits}ms</small></fieldset>

          <fieldset className="structured-editor" data-focus-key={storyboardFocusKey({ entity: { kind: "shot", shotId: selectedShot.id }, field: "audioPlan" })} tabIndex={-1}><legend>AudioPlan</legend>{selectedShot.audioPlan.events.map((event) => <div className="audio-event-card" key={event.id}><Field label="事件 ID"><input data-focus-key={storyboardFocusKey({ entity: { kind: "shot", shotId: selectedShot.id }, field: `audioPlan.events.${event.id}.id` })} readOnly value={event.id} /></Field><Field label="类型"><select data-focus-key={storyboardFocusKey({ entity: { kind: "shot", shotId: selectedShot.id }, field: `audioPlan.events.${event.id}.kind` })} value={event.kind} onChange={(change) => applyShotTransform((shot) => patchAudioEvent(shot, event.id, { kind: change.target.value as AudioEvent["kind"] }))}>{audioKinds.map((kind) => <option key={kind.value} value={kind.value}>{kind.label}</option>)}</select></Field><Field label="描述"><input data-focus-key={storyboardFocusKey({ entity: { kind: "shot", shotId: selectedShot.id }, field: `audioPlan.events.${event.id}.description` })} value={event.description} onChange={(change) => applyShotTransform((shot) => patchAudioEvent(shot, event.id, { description: change.target.value }))} /></Field><div className="field-grid two compact"><Field label="开始（毫秒）"><input data-focus-key={storyboardFocusKey({ entity: { kind: "shot", shotId: selectedShot.id }, field: `audioPlan.events.${event.id}.startOffsetUnits` })} type="number" min={0} value={event.startOffsetUnits} onChange={(change) => applyShotTransform((shot) => patchAudioEvent(shot, event.id, { startOffsetUnits: Math.max(0, Number(change.target.value)) }))} /></Field><Field label="时长（毫秒）"><input data-focus-key={storyboardFocusKey({ entity: { kind: "shot", shotId: selectedShot.id }, field: `audioPlan.events.${event.id}.durationUnits` })} type="number" min={1} value={event.durationUnits} onChange={(change) => applyShotTransform((shot) => patchAudioEvent(shot, event.id, { durationUnits: Math.max(1, Number(change.target.value)) }))} /></Field></div><Button variant="quiet" onClick={() => applyShotTransform((shot) => removeAudioEvent(shot, event.id))}>删除声音事件</Button></div>)}<Button variant="quiet" onClick={() => applyShotTransform((shot) => addAudioEvent(shot, { id: stableId("audio"), kind: "ambience", description: "新声音事件", startOffsetUnits: 0, durationUnits: Math.min(1000, shot.durationUnits) }))}>＋ 声音事件</Button></fieldset>

          <fieldset className="structured-editor"><legend>ShotBeatLink</legend>{linksForShot.map((link) => <div className="coverage-link" key={`${link.shotId}:${link.beatId}`} data-entity-key={encodeStoryboardEntity({ kind: "link", shotId: link.shotId, beatId: link.beatId })} data-focus-key={storyboardFocusKey({ entity: { kind: "link", shotId: link.shotId, beatId: link.beatId }, field: "entity" })} tabIndex={-1}><strong>{link.beatId}</strong><select data-focus-key={storyboardFocusKey({ entity: { kind: "link", shotId: link.shotId, beatId: link.beatId }, field: "role" })} value={link.role} onChange={(event) => { try { update((current) => patchShotBeatLink(current, link.shotId, link.beatId, { role: event.target.value as ShotBeatLink["role"] })); setLocalError(""); } catch (error) { setLocalError(error instanceof Error ? error.message : "覆盖角色修改失败"); } }}><option value="primary">PRIMARY</option><option value="supporting">SUPPORTING</option></select><input data-focus-key={storyboardFocusKey({ entity: { kind: "link", shotId: link.shotId, beatId: link.beatId }, field: "coverageWeight" })} aria-label="覆盖权重" type="number" min={0} max={1} step={0.1} value={link.coverageWeight} onChange={(event) => update((current) => patchShotBeatLink(current, link.shotId, link.beatId, { coverageWeight: Number(event.target.value) }))} /><Button variant="quiet" onClick={() => { if (window.confirm(`移除 ${link.shotId} → ${link.beatId} 的 ${link.role.toUpperCase()} 覆盖？`)) update((current) => removeShotBeatLink(current, link.shotId, link.beatId)); }}>移除</Button></div>)}<div className="structured-row"><select aria-label="新增覆盖的节拍" value={newLinkBeatId} onChange={(event) => setNewLinkBeatId(event.target.value)}><option value="">选择同场景 Beat</option>{sceneBeatsForShot.map((beat) => <option key={beat.id} value={beat.id}>{beat.order}. {beat.description} · {beat.id}</option>)}</select><select aria-label="新增覆盖角色" value={newLinkRole} onChange={(event) => setNewLinkRole(event.target.value as ShotBeatLink["role"])}><option value="primary">PRIMARY</option><option value="supporting">SUPPORTING</option></select><Button variant="quiet" disabled={!newLinkBeatId} onClick={addCoverageLink}>添加覆盖</Button></div></fieldset>

          <details className="prompt-details"><summary>历史关键帧任务 Prompt</summary><textarea readOnly rows={6} value={selectedImageTask?.derivedPrompt || "ProductionSnapshot 流程开放后，服务端派生 Prompt 才会显示在这里。"} /></details>
          <details className="prompt-details"><summary>历史视频任务 Prompt</summary><textarea readOnly rows={6} value={selectedVideoTask?.derivedPrompt || "ProductionSnapshot 流程开放后，服务端派生 Prompt 才会显示在这里。"} /></details>
          {selectedVideoTask?.outputUri && <a className="output-link" href={selectedVideoTask.outputUri} target="_blank" rel="noreferrer">打开历史生成视频</a>}
        </>}
      </Panel>

      <Panel className="shot-inspector review-inspector" id="storyboard-review" tabIndex={-1}>
        <div className="section-title"><span>Coverage & review</span><strong>{review?.activeApproval ? "已批准" : "等待批准"}</strong></div>
        {reviewError && <div className="notice warning" role="alert">{reviewError}</div>}
        {!review?.gateEvaluation && <div className="notice"><strong>尚无 Gate receipt</strong><span>保存有效的 V2 分镜后，服务端会原子生成评审门。</span></div>}
        {review?.activeApproval && <div className="notice"><strong>当前批准：{review.activeApproval.reviewer}</strong><span>revision {review.activeApproval.subjectRevision} · {review.activeApproval.createdAt}</span></div>}
        {review?.decisions.length ? <details><summary>Approval 历史 · {review.decisions.length}</summary>{review.decisions.map((closure) => <div className="approval-history" key={closure.decision.id}><strong>{closure.decision.decision.toUpperCase()} · {closure.decision.reviewer}</strong><small>{closure.active ? "ACTIVE" : closure.staleReasons.join("；")}</small></div>)}</details> : null}
        <details className="approval-actions" ref={approvalActions}><summary>批准或撤销分镜 · 需填写本地审核人标签</summary>
          <small>这是对当前分镜版本的独立批准决定，不是播放片段的可选审核记录。</small>
          <Field label="审核人标签" hint="此标签用于批准记录，必须填写；它不是已认证身份。"><input value={reviewer} onChange={(event) => setReviewer(event.target.value)} /></Field>
          <Field label="评审备注（可选）"><textarea rows={3} value={reviewNote} onChange={(event) => setReviewNote(event.target.value)} /></Field>
          <div className="button-row"><Button variant="primary" disabled={!reviewer.trim() || stale || !requiredGatesPass || Boolean(review?.activeApproval)} onClick={() => void decide("approve")}>批准当前分镜</Button><Button variant="quiet" disabled={!reviewer.trim() || !review?.activeApproval} onClick={() => void decide("revoke")}>撤销批准</Button></div>
        </details>
        <details open={coverage.some((item) => item.primaryShotIds.length !== 1)}><summary>节拍覆盖详情 · {coverage.length} 项</summary><div className="coverage-summary">{coverage.map((item) => <div key={item.beatId}><span>{item.beatId}</span><Badge tone={item.primaryShotIds.length === 1 ? "ok" : "danger"}>PRIMARY {item.primaryShotIds.length}</Badge><small>SUPPORTING {item.supportingShotIds.length}</small></div>)}</div></details>
        {review?.gateEvaluation && <details open={!requiredGatesPass}><summary>质量门详情 · {review.gateEvaluation.results.length} 项 · {requiredGatesPass ? "必需门已通过" : "必需门未通过"}</summary><div className="gate-list">{review.gateEvaluation.results.map((gate) => <button key={gate.id} className={`gate-row ${gate.status}`} onClick={() => navigateGate(gate.entityPath)}><GateStatusBadge status={gate.status} /><span><strong>{gate.gateId}</strong><small>{gate.reason}{gate.entityPath.length ? ` · ${gate.entityPath.join(" › ")}` : ""}</small></span></button>)}</div></details>}
      </Panel>
    </div>
    </details>
  </div>;
}
