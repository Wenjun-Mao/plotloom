import { useEffect, useMemo, useRef, useState } from "react";
import type {
  CharacterCard,
  CharacterReferenceProposal,
  LocationCard,
  PropCard,
  StoryBible,
  ValidationIssue,
  VisualWorkbench,
} from "../types";
import { plotloomApi } from "../api";
import { Button, Field, PageHeader, Panel } from "../components";
import {
  addBibleEntity,
  bibleEntityImpacts,
  deleteBibleEntity,
  entityBySelection,
  entityForIdentity,
  entityUrlIdentity,
  issueTargetForPath,
  type BibleEntitySelection,
  type BibleEntityType,
  type BibleIssueTarget,
  type BibleReferenceContext,
} from "../bible-editor";

type StoryBiblePageProps = {
  value: StoryBible;
  stale: boolean;
  saving: boolean;
  entityId?: string;
  projectId?: string;
  storyBibleRevision?: number;
  referenceContext?: BibleReferenceContext;
  issues?: ValidationIssue[];
  onEntitySelect?: (entityId: string) => void;
  onSave: (value: StoryBible) => Promise<void>;
  onDraftChange?: (value: StoryBible) => void;
};
const splitLines = (value: string) =>
  value
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean);
const joinLines = (value: string[]) => value.join("\n");
const freshEntityId = (type: BibleEntityType) =>
  `${type}-${crypto.randomUUID()}`;

function LinesField({
  label,
  value,
  onChange,
  testId,
  field,
}: {
  label: string;
  value: string[];
  onChange: (next: string[]) => void;
  testId: string;
  field?: string;
}) {
  return (
    <Field label={label}>
      <textarea
        data-testid={testId}
        data-bible-field={field}
        rows={3}
        value={joinLines(value)}
        onChange={(event) => onChange(splitLines(event.target.value))}
      />
    </Field>
  );
}

function CharacterInspector({
  entity,
  onChange,
}: {
  entity: CharacterCard;
  onChange: (patch: Partial<CharacterCard>) => void;
}) {
  return (
    <div className="field-grid two" data-testid="character-inspector">
      <Field label="稳定 ID">
        <input
          data-bible-field="id"
          value={entity.id}
          readOnly
          aria-readonly="true"
        />
      </Field>
      <Field label="姓名">
        <input
          data-testid="character-name"
          data-bible-field="name"
          value={entity.name}
          onChange={(event) => onChange({ name: event.target.value })}
        />
      </Field>
      <Field label="叙事职责">
        <input
          data-bible-field="role"
          value={entity.role ?? ""}
          onChange={(event) => onChange({ role: event.target.value || null })}
        />
      </Field>
      <Field label="目标">
        <input
          data-bible-field="goal"
          value={entity.goal}
          onChange={(event) => onChange({ goal: event.target.value })}
        />
      </Field>
      <Field label="角色描述">
        <textarea
          data-bible-field="description"
          rows={3}
          value={entity.description}
          onChange={(event) => onChange({ description: event.target.value })}
        />
      </Field>
      <LinesField
        label="特质（每行一条）"
        value={entity.traits}
        onChange={(traits) => onChange({ traits })}
        testId="character-traits"
        field="traits"
      />
      <LinesField
        label="视觉 anchors（每行一条）"
        value={entity.visualAnchors}
        onChange={(visualAnchors) => onChange({ visualAnchors })}
        testId="character-visual-anchors"
        field="visualAnchors"
      />
      <LinesField
        label="声音 anchors（每行一条）"
        value={entity.soundAnchors}
        onChange={(soundAnchors) => onChange({ soundAnchors })}
        testId="character-sound-anchors"
        field="soundAnchors"
      />
      <LinesField
        label="语音 anchors（每行一条）"
        value={entity.voiceAnchors}
        onChange={(voiceAnchors) => onChange({ voiceAnchors })}
        testId="character-voice-anchors"
        field="voiceAnchors"
      />
      <LinesField
        label="允许状态（每行一条）"
        value={entity.allowedStates}
        onChange={(allowedStates) => onChange({ allowedStates })}
        testId="character-allowed-states"
        field="allowedStates"
      />
      <LinesField
        label="连续性规则（每行一条）"
        value={entity.continuityRules}
        onChange={(continuityRules) => onChange({ continuityRules })}
        testId="character-continuity-rules"
        field="continuityRules"
      />
    </div>
  );
}

function WorldEntityInspector({
  type,
  entity,
  onChange,
}: {
  type: "location" | "prop";
  entity: LocationCard | PropCard;
  onChange: (patch: Partial<LocationCard | PropCard>) => void;
}) {
  const label = type === "location" ? "地点" : "道具";
  return (
    <div className="field-grid two" data-testid={`${type}-inspector`}>
      <Field label="稳定 ID">
        <input
          data-bible-field="id"
          value={entity.id}
          readOnly
          aria-readonly="true"
        />
      </Field>
      <Field label={`${label}名称`}>
        <input
          data-testid={`${type}-name`}
          data-bible-field="name"
          value={entity.name}
          onChange={(event) => onChange({ name: event.target.value })}
        />
      </Field>
      <Field label={`${label}描述`}>
        <textarea
          data-bible-field="description"
          rows={3}
          value={entity.description}
          onChange={(event) => onChange({ description: event.target.value })}
        />
      </Field>
      <LinesField
        label="视觉 anchors（每行一条）"
        value={entity.visualAnchors}
        onChange={(visualAnchors) => onChange({ visualAnchors })}
        testId={`${type}-visual-anchors`}
        field="visualAnchors"
      />
      <LinesField
        label="声音 anchors（每行一条）"
        value={entity.soundAnchors}
        onChange={(soundAnchors) => onChange({ soundAnchors })}
        testId={`${type}-sound-anchors`}
        field="soundAnchors"
      />
      <LinesField
        label="允许状态（每行一条）"
        value={entity.allowedStates}
        onChange={(allowedStates) => onChange({ allowedStates })}
        testId={`${type}-allowed-states`}
        field="allowedStates"
      />
      <LinesField
        label="连续性规则（每行一条）"
        value={entity.continuityRules}
        onChange={(continuityRules) => onChange({ continuityRules })}
        testId={`${type}-continuity-rules`}
        field="continuityRules"
      />
    </div>
  );
}

function StoryFirstCharacterReferences({
  projectId,
  bible,
  storyBibleRevision,
  readOnly,
}: {
  projectId?: string;
  bible: StoryBible;
  storyBibleRevision?: number;
  readOnly: boolean;
}) {
  const [proposals, setProposals] = useState<CharacterReferenceProposal[]>([]);
  const [workbench, setWorkbench] = useState<VisualWorkbench>();
  const [characterId, setCharacterId] = useState("");
  const [direction, setDirection] = useState("");
  const [parentCandidateAssetId, setParentCandidateAssetId] = useState("");
  const [reviewer, setReviewer] = useState("creator/product reviewer");
  const [notes, setNotes] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [assignment, setAssignment] = useState("");
  const [assignmentCopied, setAssignmentCopied] = useState(false);
  const refresh = async () => {
    if (!projectId) return;
    const [nextProposals, nextWorkbench] = await Promise.all([
      plotloomApi.getCharacterReferenceProposals(projectId),
      plotloomApi.getVisualWorkbench(projectId),
    ]);
    setProposals(nextProposals.proposals);
    setWorkbench(nextWorkbench);
  };
  useEffect(() => {
    if (!characterId && bible.characters[0])
      setCharacterId(bible.characters[0].id);
  }, [bible.characters, characterId]);
  useEffect(() => {
    void refresh().catch((loadError) =>
      setError(
        loadError instanceof Error ? loadError.message : "无法读取角色参考",
      ),
    );
  }, [projectId]); // eslint-disable-line react-hooks/exhaustive-deps
  const candidates = proposals
    .filter(
      (proposal) => proposal.current && proposal.characterId === characterId,
    )
    .flatMap((proposal) =>
      proposal.deliveries.flatMap((delivery) =>
        delivery.candidates.map((candidate) => ({ proposal, candidate })),
      ),
    );
  const currentDecision = workbench?.characterReferences.decisions.find(
    (decision) => decision.characterId === characterId && decision.current,
  );
  const state = workbench?.characterReferences.states.find(
    (item) => item.characterId === characterId,
  );
  const prepare = async () => {
    if (!projectId || !storyBibleRevision || !characterId || !direction.trim())
      return;
    setBusy(true);
    setError("");
    try {
      await plotloomApi.prepareCharacterReferenceProposal(projectId, {
        characterId,
        castRevision: storyBibleRevision,
        visualDirection: direction.trim(),
        parentCandidateAssetId: parentCandidateAssetId || undefined,
      });
      setDirection("");
      setParentCandidateAssetId("");
      await refresh();
    } catch (proposalError) {
      setError(
        proposalError instanceof Error
          ? proposalError.message
          : "无法准备 proposal",
      );
    } finally {
      setBusy(false);
    }
  };
  const selectReference = async (assetId: string) => {
    if (!projectId || !characterId || !reviewer.trim() || !notes.trim()) return;
    setBusy(true);
    setError("");
    try {
      await plotloomApi.selectCharacterReference(projectId, {
        characterId,
        authority: "cast",
        primaryAssetId: assetId,
        complementaryAssetIds: [],
        expectedReferenceRevision: state?.revision ?? 0,
        reviewer: reviewer.trim(),
        notes: notes.trim(),
      });
      await refresh();
    } catch (selectionError) {
      setError(
        selectionError instanceof Error
          ? selectionError.message
          : "无法选择身份参考",
      );
    } finally {
      setBusy(false);
    }
  };
  const copyProposal = async (proposalId: string) => {
    if (!projectId) return;
    setBusy(true);
    setError("");
    try {
      const copied = await plotloomApi.copyCharacterReferenceProposal(
        projectId,
        proposalId,
      );
      setAssignment(copied.assignment);
      setAssignmentCopied(false);
      try {
        await navigator.clipboard.writeText(copied.assignment);
        setAssignmentCopied(true);
      } catch {
        /* Selectable fallback remains visible. */
      }
      await refresh();
    } catch (copyError) {
      setError(
        copyError instanceof Error
          ? copyError.message
          : "无法复制 proposal assignment",
      );
    } finally {
      setBusy(false);
    }
  };
  const refreshProposal = async (proposalId: string) => {
    if (!projectId) return;
    setBusy(true);
    setError("");
    try {
      await plotloomApi.refreshCharacterReferenceProposal(
        projectId,
        proposalId,
      );
      await refresh();
    } catch (refreshError) {
      setError(
        refreshError instanceof Error
          ? refreshError.message
          : "无法检查 proposal delivery",
      );
    } finally {
      setBusy(false);
    }
  };
  return (
    <Panel className="form-card" data-testid="story-first-character-references">
      <div className="section-title">
        <span>Story-first character references · P1.5</span>
        <strong>No Shot, downstream stage, or Approval required</strong>
      </div>
      <p className="muted">
        保存 Story Bible 后可探索角色外观、细化 proposal candidate，并由
        creator/product reviewer 显式选择或替换身份参考。Codex
        的工程/视觉评估必须标注为 Codex，不是 human/product decision。
      </p>
      {error && (
        <div role="alert" className="notice warning">
          {error}
        </div>
      )}
      <div className="field-grid two compact">
        <Field label="角色">
          <select
            data-testid="story-first-proposal-character"
            value={characterId}
            disabled={readOnly || busy}
            onChange={(event) => setCharacterId(event.target.value)}
          >
            {bible.characters.map((character) => (
              <option value={character.id} key={character.id}>
                {character.name} · {character.id}
              </option>
            ))}
          </select>
        </Field>
        <Field label="已保存 Story Bible revision">
          <input readOnly value={storyBibleRevision ?? "先保存 Story Bible"} />
        </Field>
        <Field label="细化父候选">
          <select
            data-testid="story-first-proposal-parent"
            value={parentCandidateAssetId}
            disabled={readOnly || busy}
            onChange={(event) => setParentCandidateAssetId(event.target.value)}
          >
            <option value="">原始 proposal</option>
            {candidates.map(({ candidate }) => (
              <option value={candidate.assetId} key={candidate.assetId}>
                {candidate.assetId.slice(0, 8)} · {candidate.role}
              </option>
            ))}
          </select>
        </Field>
        <Field label="选择者（creator/product 或 Codex）">
          <input
            data-testid="story-first-reference-reviewer"
            value={reviewer}
            disabled={readOnly || busy}
            onChange={(event) => setReviewer(event.target.value)}
          />
        </Field>
      </div>
      <Field label="探索性视觉方向">
        <textarea
          data-testid="story-first-proposal-direction"
          rows={2}
          value={direction}
          disabled={readOnly || busy}
          onChange={(event) => setDirection(event.target.value)}
        />
      </Field>
      <Field label="选择/替换说明">
        <textarea
          data-testid="story-first-reference-notes"
          rows={2}
          value={notes}
          disabled={readOnly || busy}
          onChange={(event) => setNotes(event.target.value)}
        />
      </Field>
      <div className="button-row">
        <Button
          data-testid="story-first-prepare-proposal"
          variant="primary"
          disabled={
            readOnly || busy || !storyBibleRevision || !direction.trim()
          }
          onClick={() => void prepare()}
        >
          准备 proposal assignment
        </Button>
        <small>不会创建 Shot、Approval 或自动选择。</small>
      </div>
      {assignment && (
        <Field label="交给 Codex specialist 的 proposal assignment">
          <textarea
            data-testid="story-first-assignment"
            readOnly
            rows={2}
            value={assignment}
          />
          <small>
            {assignmentCopied
              ? "已复制到系统剪贴板。"
              : "浏览器未允许剪贴板访问；请手动选择并复制。"}
          </small>
        </Field>
      )}
      {proposals
        .filter((proposal) => proposal.characterId === characterId)
        .map((proposal) => (
          <div className="button-row" key={proposal.id}>
            <small>
              {proposal.parentCandidateAssetId ? "refinement" : "proposal"} ·{" "}
              {proposal.current ? "current" : "history/stale"} ·{" "}
              {proposal.state}
            </small>
            <Button
              data-testid={`story-first-copy-${proposal.id}`}
              variant="quiet"
              disabled={readOnly || busy || !proposal.current}
              onClick={() => void copyProposal(proposal.id)}
            >
              Copy assignment
            </Button>
            <Button
              data-testid={`story-first-refresh-${proposal.id}`}
              variant="quiet"
              disabled={readOnly || busy}
              onClick={() => void refreshProposal(proposal.id)}
            >
              检查 delivery
            </Button>
          </div>
        ))}
      <div
        className="frozen-review-comparison"
        data-testid="story-first-reference-comparison"
      >
        {currentDecision &&
          workbench &&
          [
            currentDecision.primaryAssetId,
            ...currentDecision.complementaryAssetIds,
          ].map((assetId, index) => {
            const asset = workbench.assets.find((item) => item.id === assetId);
            return asset && projectId ? (
              <article className="media-candidate" key={asset.id}>
                <img
                  src={plotloomApi.managedAssetUrl(projectId, asset.id)}
                  alt={`current ${index === 0 ? "primary" : "complementary"} reference`}
                />
                <strong>
                  current {index === 0 ? "primary" : "complementary"} · r
                  {currentDecision.referenceRevision}
                </strong>
                <small>{asset.id.slice(0, 8)}</small>
              </article>
            ) : null;
          })}
        {workbench?.characterReferences.decisions
          .filter(
            (decision) =>
              decision.characterId === characterId && !decision.current,
          )
          .flatMap((decision) =>
            [decision.primaryAssetId, ...decision.complementaryAssetIds].map(
              (assetId, index) => {
                const asset = workbench.assets.find(
                  (item) => item.id === assetId,
                );
                return asset && projectId ? (
                  <article
                    className="media-candidate"
                    key={`history-${decision.id}-${asset.id}`}
                  >
                    <img
                      src={plotloomApi.managedAssetUrl(projectId, asset.id)}
                      alt={`historical ${index === 0 ? "primary" : "complementary"} reference`}
                    />
                    <strong>
                      reference history{" "}
                      {index === 0 ? "primary" : "complementary"} · r
                      {decision.referenceRevision}
                    </strong>
                    <small>
                      {asset.id.slice(0, 8)} ·{" "}
                      {decision.revokedAt ? "revoked" : "replaced"}
                    </small>
                  </article>
                ) : null;
              },
            ),
          )}
        {proposals
          .filter((proposal) => proposal.characterId === characterId)
          .flatMap((proposal) =>
            proposal.deliveries.flatMap((delivery) =>
              delivery.candidates.map((candidate) =>
                candidate.asset && projectId ? (
                  <article className="media-candidate" key={candidate.id}>
                    <img
                      src={plotloomApi.managedAssetUrl(
                        projectId,
                        candidate.asset.id,
                      )}
                      alt="proposal candidate"
                    />
                    <strong>
                      {proposal.parentCandidateAssetId
                        ? "refinement"
                        : "proposal"}{" "}
                      · {proposal.current ? "current" : "history/stale"}
                    </strong>
                    <small>{candidate.assetId.slice(0, 8)}</small>
                    <Button
                      data-testid={`story-first-refine-${candidate.assetId}`}
                      variant="quiet"
                      disabled={readOnly || busy || !proposal.current}
                      onClick={() =>
                        setParentCandidateAssetId(candidate.assetId)
                      }
                    >
                      用于细化
                    </Button>
                    <Button
                      data-testid={`story-first-select-${candidate.assetId}`}
                      variant="quiet"
                      disabled={
                        readOnly || busy || !reviewer.trim() || !notes.trim()
                      }
                      onClick={() => void selectReference(candidate.assetId)}
                    >
                      选择/替换参考
                    </Button>
                  </article>
                ) : null,
              ),
            ),
          )}
      </div>
    </Panel>
  );
}

export function StoryBiblePage({
  value,
  stale,
  saving,
  entityId,
  projectId,
  storyBibleRevision,
  referenceContext,
  issues = [],
  onEntitySelect,
  onSave,
  onDraftChange,
}: StoryBiblePageProps) {
  const [draft, setDraft] = useState(value);
  const [localSelection, setLocalSelection] = useState<BibleEntitySelection>();
  const [pendingDeletion, setPendingDeletion] =
    useState<BibleEntitySelection>();
  const [issueFocus, setIssueFocus] = useState<BibleIssueTarget>();
  const previousEntityId = useRef(entityId);
  const lastIssueSignature = useRef<string | undefined>(undefined);
  const issueSignature = JSON.stringify(issues);
  useEffect(() => setDraft(value), [value]);
  useEffect(() => {
    const previous = previousEntityId.current;
    previousEntityId.current = entityId;
    if (previous && !entityId) setLocalSelection(undefined);
  }, [entityId]);
  const selection = entityForIdentity(draft, entityId) ?? localSelection;
  const selectedEntity = entityBySelection(draft, selection);
  const impacts = useMemo(
    () =>
      pendingDeletion
        ? bibleEntityImpacts(pendingDeletion, referenceContext)
        : [],
    [pendingDeletion, referenceContext],
  );
  const update = (next: StoryBible | ((current: StoryBible) => StoryBible)) =>
    setDraft((current) => {
      const updated = typeof next === "function" ? next(current) : next;
      onDraftChange?.(updated);
      return updated;
    });
  const selectEntity = (next: BibleEntitySelection | undefined) => {
    setLocalSelection(next);
    onEntitySelect?.(next ? entityUrlIdentity(next.type, next.id) : "");
  };
  const addEntity = (type: BibleEntityType) => {
    const id = freshEntityId(type);
    update((current) => addBibleEntity(current, type, id));
    selectEntity({ type, id });
  };
  const updateEntity = (patch: Record<string, unknown>) => {
    if (!selection) return;
    update((current) => {
      const collection =
        selection.type === "character"
          ? "characters"
          : selection.type === "location"
            ? "locations"
            : "props";
      return {
        ...current,
        [collection]: current[collection].map((entity) =>
          entity.id === selection.id ? { ...entity, ...patch } : entity,
        ),
      } as StoryBible;
    });
  };
  const confirmDelete = () => {
    if (!pendingDeletion || impacts.length) return;
    update(
      (current) =>
        deleteBibleEntity(current, pendingDeletion, referenceContext).bible,
    );
    selectEntity(undefined);
    setPendingDeletion(undefined);
  };
  const focusIssue = (issue: ValidationIssue) => {
    const target = issueTargetForPath(draft, issue.path);
    if (!target) return;
    if (target.entity) selectEntity(target.entity);
    setIssueFocus(target);
  };
  useEffect(() => {
    if (!issues.length) {
      lastIssueSignature.current = undefined;
      setIssueFocus(undefined);
      return;
    }
    if (issueSignature === lastIssueSignature.current) return;
    lastIssueSignature.current = issueSignature;
    const issue = issues.find((candidate) =>
      issueTargetForPath(draft, candidate.path),
    );
    if (issue) focusIssue(issue);
  }, [draft, issueSignature, issues]);
  useEffect(() => {
    if (!issueFocus) return;
    if (
      issueFocus.entity &&
      (selection?.type !== issueFocus.entity.type ||
        selection.id !== issueFocus.entity.id)
    )
      return;
    const target = [
      ...document.querySelectorAll<HTMLElement>("[data-bible-field]"),
    ].find((element) => element.dataset.bibleField === issueFocus.field);
    target?.focus();
  }, [issueFocus, selection?.id, selection?.type]);
  const entities: Array<{
    type: BibleEntityType;
    title: string;
    items: CharacterCard[] | LocationCard[] | PropCard[];
  }> = [
    { type: "character", title: "角色卡", items: draft.characters },
    { type: "location", title: "地点", items: draft.locations },
    { type: "prop", title: "道具", items: draft.props },
  ];

  return (
    <div className="page" data-testid="story-bible-editor">
      <PageHeader
        eyebrow="02 · Canon"
        title="故事圣经"
        description="人物、地点与道具只在这里定义；下游阶段只引用稳定 ID。"
        actions={
          <>
            <span className={`stage-chip ${stale ? "stale" : "ready"}`}>
              {stale ? "上游已变更" : "当前版本"}
            </span>
            <Button
              variant="primary"
              disabled={saving}
              onClick={() => void onSave(draft)}
            >
              {saving ? "正在保存…" : "保存故事圣经"}
            </Button>
          </>
        }
      />
      <Panel className="form-card">
        <div className="field-grid two">
          <Field label="Logline">
            <textarea
              data-bible-field="logline"
              rows={3}
              value={draft.logline}
              onChange={(event) =>
                update({ ...draft, logline: event.target.value })
              }
            />
          </Field>
          <Field label="故事前提">
            <textarea
              data-bible-field="premise"
              rows={3}
              value={draft.premise}
              onChange={(event) =>
                update({ ...draft, premise: event.target.value })
              }
            />
          </Field>
          <Field label="类型">
            <input
              data-bible-field="genre"
              value={draft.genre}
              onChange={(event) =>
                update({ ...draft, genre: event.target.value })
              }
            />
          </Field>
          <Field label="基调">
            <input
              data-bible-field="tone"
              value={draft.tone}
              onChange={(event) =>
                update({ ...draft, tone: event.target.value })
              }
            />
          </Field>
          <Field label="受众">
            <input
              data-bible-field="audience"
              value={draft.audience}
              onChange={(event) =>
                update({ ...draft, audience: event.target.value })
              }
            />
          </Field>
          <Field label="叙事承诺">
            <textarea
              data-bible-field="narrativePromise"
              rows={3}
              value={draft.narrativePromise}
              onChange={(event) =>
                update({ ...draft, narrativePromise: event.target.value })
              }
            />
          </Field>
          <Field label="统一视觉语言">
            <textarea
              data-bible-field="visualLanguage"
              rows={3}
              value={draft.visualLanguage}
              onChange={(event) =>
                update({ ...draft, visualLanguage: event.target.value })
              }
            />
          </Field>
          <LinesField
            label="主题（每行一条）"
            value={draft.themes}
            onChange={(themes) => update({ ...draft, themes })}
            testId="bible-themes"
            field="themes"
          />
          <LinesField
            label="世界规则（每行一条）"
            value={draft.worldRules}
            onChange={(worldRules) => update({ ...draft, worldRules })}
            testId="bible-world-rules"
            field="worldRules"
          />
          <LinesField
            label="已知事实（每行一条）"
            value={draft.knownFacts}
            onChange={(knownFacts) => update({ ...draft, knownFacts })}
            testId="bible-known-facts"
            field="knownFacts"
          />
          <LinesField
            label="待解问题（每行一条）"
            value={draft.openQuestions}
            onChange={(openQuestions) => update({ ...draft, openQuestions })}
            testId="bible-open-questions"
            field="openQuestions"
          />
          <LinesField
            label="来源备注（每行一条）"
            value={draft.sourceNotes}
            onChange={(sourceNotes) => update({ ...draft, sourceNotes })}
            testId="bible-source-notes"
            field="sourceNotes"
          />
        </div>
      </Panel>
      {issues.length > 0 && (
        <Panel className="form-card" data-testid="bible-issues">
          <span className="eyebrow">Validation issues</span>
          <h2>需要处理的问题</h2>
          {issues.map((issue, index) => (
            <Button
              key={`${issue.code}:${issue.path}:${index}`}
              variant="quiet"
              onClick={() => focusIssue(issue)}
            >
              {issue.code} · {issue.path} · {issue.message}
            </Button>
          ))}
        </Panel>
      )}
      {entities.map(({ type, title, items }) => (
        <section key={type} data-testid={`${type}-collection`}>
          <div className="section-bar">
            <div>
              <span className="eyebrow">Stable identity</span>
              <h2>{title}</h2>
            </div>
            <Button
              variant="quiet"
              data-testid={`add-${type}`}
              onClick={() => addEntity(type)}
            >
              ＋ 新
              {type === "character"
                ? "角色"
                : type === "location"
                  ? "地点"
                  : "道具"}
            </Button>
          </div>
          <div className="card-grid">
            {items.map((entity, index) => (
              <Panel
                className={`character-card ${selection?.type === type && selection.id === entity.id ? "selected" : ""}`}
                key={entity.id}
              >
                <div className="card-index">
                  {String(index + 1).padStart(2, "0")}
                </div>
                <strong>{entity.name || "未命名实体"}</strong>
                <small>{entity.id}</small>
                <p>{entity.description || "尚未填写描述"}</p>
                <Button
                  variant="quiet"
                  data-testid={`select-${type}-${entity.id}`}
                  onClick={() => selectEntity({ type, id: entity.id })}
                >
                  编辑此
                  {type === "character"
                    ? "角色"
                    : type === "location"
                      ? "地点"
                      : "道具"}
                </Button>
              </Panel>
            ))}
          </div>
        </section>
      ))}
      {selection && selectedEntity && (
        <Panel className="form-card" data-testid="bible-entity-rail">
          <div className="section-bar">
            <div>
              <span className="eyebrow">Type-specific inspector</span>
              <h2>
                {selection.type === "character"
                  ? "角色检查器"
                  : selection.type === "location"
                    ? "地点检查器"
                    : "道具检查器"}
              </h2>
            </div>
            <Button
              variant="danger"
              data-testid="request-entity-delete"
              onClick={() => setPendingDeletion(selection)}
            >
              删除
            </Button>
          </div>
          {selection.type === "character" ? (
            <CharacterInspector
              entity={selectedEntity as CharacterCard}
              onChange={updateEntity}
            />
          ) : (
            <WorldEntityInspector
              type={selection.type}
              entity={selectedEntity as LocationCard | PropCard}
              onChange={updateEntity}
            />
          )}
        </Panel>
      )}
      {pendingDeletion && (
        <Panel className="form-card">
          <div data-testid="bible-delete-dialog" role="alertdialog">
            <span className="eyebrow">Deletion review</span>
            <h2>
              删除 {pendingDeletion.type} · {pendingDeletion.id}
            </h2>
            {impacts.length > 0 ? (
              <>
                <p>
                  删除已拒绝。请先在下游场景、镜头、状态或对白中解除以下引用；编辑器不会隐藏级联删除。
                </p>
                <ul>
                  {impacts.map((impact) => (
                    <li key={`${impact.path}:${impact.kind}`}>
                      <strong>{impact.kind}</strong> · {impact.path} ·{" "}
                      {impact.message}
                    </li>
                  ))}
                </ul>
                <Button
                  variant="quiet"
                  onClick={() => setPendingDeletion(undefined)}
                >
                  关闭
                </Button>
              </>
            ) : (
              <>
                <p>没有已知下游引用。确认后将只删除这个实体。</p>
                <Button
                  variant="danger"
                  data-testid="confirm-entity-delete"
                  onClick={confirmDelete}
                >
                  确认删除
                </Button>
                <Button
                  variant="quiet"
                  onClick={() => setPendingDeletion(undefined)}
                >
                  取消
                </Button>
              </>
            )}
          </div>
        </Panel>
      )}
    </div>
  );
}
