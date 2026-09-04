import { useEffect, useMemo, useRef, useState } from "react";
import type {
  Beat,
  ContinuityState,
  DialogueCue,
  EntityType,
  RequiredEntityState,
  SceneBeatPlan,
  StoryNode,
  ValidationIssue,
} from "../types";
import { Button, Field, PageHeader, Panel } from "../components";
import { TypedRecordEditor } from "../structured-fields";
import {
  addBeat,
  addCue,
  addScene,
  applyDeleteImpact,
  beatDeleteImpact,
  cueDeleteImpact,
  beatMigrationImpact,
  cueMigrationImpact,
  migrateBeatToScene,
  migrateCueToBeat,
  newEntityState,
  parseSceneBeatsEntityIdentity,
  patchBeat,
  patchCue,
  patchScene,
  reorderBeat,
  reorderCue,
  reorderScene,
  sceneBeatsEntityIdentity,
  sceneBeatsFocusKey,
  sceneBeatsIssueTarget,
  sceneDeleteImpact,
  type DeleteImpact,
  type SceneBeatsEntity,
  type SceneBeatsMigrationImpact,
  type StoryboardDeletionContext,
} from "../scene-beats-editor";

export interface SceneBeatsReferenceContext {
  nodes?: StoryNode[];
  characters?: { id: string; name: string; allowedStates?: string[] }[];
  locations?: { id: string; name: string; allowedStates?: string[] }[];
  props?: { id: string; name: string; allowedStates?: string[] }[];
  /** Read-only later-stage projection used solely for deletion disclosure. */
  storyboard?: StoryboardDeletionContext;
}

interface Props {
  value: SceneBeatPlan;
  stale: boolean;
  saving: boolean;
  entityId?: string;
  issues?: ValidationIssue[];
  onEntitySelect?: (entityId: string) => void;
  onSave: (value: SceneBeatPlan) => Promise<void>;
  onDraftChange?: (value: SceneBeatPlan) => void;
  referenceContext?: SceneBeatsReferenceContext;
}

const newId = () => crypto.randomUUID();
const lines = (value: string) =>
  value
    .split("\n")
    .map((item) => item.trim())
    .filter(Boolean);
const choices = (context: SceneBeatsReferenceContext, type: EntityType) =>
  type === "character"
    ? context.characters || []
    : type === "location"
      ? context.locations || []
      : context.props || [];

function EntityScope({
  entity,
  onFocus,
  children,
}: {
  entity: SceneBeatsEntity;
  onFocus: (field?: string) => void;
  children: React.ReactNode;
}) {
  return (
    <div
      tabIndex={-1}
      data-entity-key={sceneBeatsEntityIdentity(entity)}
      data-focus-key={sceneBeatsFocusKey(entity)}
      onFocus={(event) => {
        // Cue cards are nested inside beat cards. Only the nearest entity scope
        // owns focus, otherwise a cue focus would be overwritten as its beat.
        if (
          (event.target as HTMLElement).closest("[data-entity-key]") !==
          event.currentTarget
        )
          return;
        const field = (event.target as HTMLElement).dataset.focusField;
        // Buttons are deliberately outside the field-focus contract. Routing
        // their focus here can steal a pointer activation before its click
        // handler opens a structural confirmation dialog.
        if (!field) return;
        onFocus(field);
      }}
    >
      {children}
    </div>
  );
}

function focusProps(entity: SceneBeatsEntity, field: string) {
  return {
    "data-focus-key": sceneBeatsFocusKey(entity, field),
    "data-focus-field": field,
  };
}

function ContinuityEditor({
  label,
  value,
  context,
  entity,
  field,
  onFocus,
  onChange,
}: {
  label: string;
  value: ContinuityState;
  context: SceneBeatsReferenceContext;
  entity: SceneBeatsEntity;
  field: "entryState" | "exitState";
  onFocus: (field?: string) => void;
  onChange: (value: ContinuityState) => void;
}) {
  const patchEntity = (index: number, patch: Partial<RequiredEntityState>) =>
    onChange({
      ...value,
      entityStates: value.entityStates.map((item, current) =>
        current === index ? { ...item, ...patch } : item,
      ),
    });
  return (
    <fieldset
      className="field-grid two compact"
      tabIndex={-1}
      {...focusProps(entity, field)}
      data-testid={`continuity-${label}`}
      onFocus={() => onFocus(field)}
    >
      <legend>{label}</legend>
      <div tabIndex={-1} {...focusProps(entity, `${field}.facts`)}>
        <TypedRecordEditor
          label="事实"
          value={value.facts}
          onChange={(facts) => onChange({ ...value, facts })}
          testId={`continuity-facts-${entity.id}-${field}`}
          focusKey={sceneBeatsFocusKey(entity, `${field}.facts`)}
          focusField={`${field}.facts`}
        />
      </div>
      <Field label="连续性备注（每行一条）">
        <textarea
          {...focusProps(entity, `${field}.notes`)}
          rows={3}
          value={value.notes.join("\n")}
          onChange={(event) =>
            onChange({ ...value, notes: lines(event.target.value) })
          }
        />
      </Field>
      <Field label="画面方向">
        <input
          {...focusProps(entity, `${field}.screenDirection`)}
          value={value.screenDirection || ""}
          onChange={(event) =>
            onChange({ ...value, screenDirection: event.target.value || null })
          }
        />
      </Field>
      <Field label="光线">
        <input
          {...focusProps(entity, `${field}.lighting`)}
          value={value.lighting || ""}
          onChange={(event) =>
            onChange({ ...value, lighting: event.target.value || null })
          }
        />
      </Field>
      <Field label="声音">
        <input
          {...focusProps(entity, `${field}.sound`)}
          value={value.sound || ""}
          onChange={(event) =>
            onChange({ ...value, sound: event.target.value || null })
          }
        />
      </Field>
      <div className="field">
        <span>实体状态</span>
        {value.entityStates.map((state, index) => (
          <div
            className="field-grid two compact"
            key={`${state.entityType}:${state.entityId}:${index}`}
          >
            <select
              {...focusProps(
                entity,
                `${field}.entityStates.${index}.entityType`,
              )}
              aria-label="实体类型"
              value={state.entityType}
              onChange={(event) =>
                patchEntity(index, {
                  entityType: event.target.value as EntityType,
                  entityId: "",
                  state: "",
                })
              }
            >
              <option value="character">角色</option>
              <option value="location">地点</option>
              <option value="prop">道具</option>
            </select>
            <select
              {...focusProps(entity, `${field}.entityStates.${index}.entityId`)}
              aria-label="实体"
              value={state.entityId}
              onChange={(event) =>
                patchEntity(index, { entityId: event.target.value })
              }
            >
              <option value="">选择实体</option>
              {choices(context, state.entityType).map((item) => (
                <option key={item.id} value={item.id}>
                  {item.name} · {item.id}
                </option>
              ))}
            </select>
            <input
              {...focusProps(entity, `${field}.entityStates.${index}.state`)}
              aria-label="状态"
              value={state.state}
              onChange={(event) =>
                patchEntity(index, { state: event.target.value })
              }
            />
            <Button
              type="button"
              variant="quiet"
              onClick={() =>
                onChange({
                  ...value,
                  entityStates: value.entityStates.filter(
                    (_, current) => current !== index,
                  ),
                })
              }
            >
              移除状态
            </Button>
          </div>
        ))}
        <Button
          type="button"
          variant="quiet"
          onClick={() =>
            onChange({
              ...value,
              entityStates: [...value.entityStates, newEntityState()],
            })
          }
        >
          ＋ 实体状态
        </Button>
      </div>
    </fieldset>
  );
}

function DeleteConfirmation({
  impact,
  onCancel,
  onConfirm,
}: {
  impact: DeleteImpact;
  onCancel: () => void;
  onConfirm: () => void;
}) {
  const summary = [
    `${impact.sceneIds.length} 个场景`,
    `${impact.beatIds.length} 个节拍`,
    `${impact.cueIds.length} 条 cue`,
  ].join("、");
  return (
    <div
      className="modal"
      role="alertdialog"
      aria-modal="true"
      aria-labelledby="scene-beats-delete-title"
      data-testid="delete-impact"
    >
      <button
        className="modal-backdrop"
        aria-label="取消删除"
        onClick={onCancel}
      />
      <section className="modal-card compact">
        <header>
          <div>
            <span>Structural deletion</span>
            <h2 id="scene-beats-delete-title">删除影响确认</h2>
          </div>
        </header>
        <div className="modal-body">
          <p>将删除 {summary}。删除会精确级联下级记录，不保留悬挂引用。</p>
          <ul className="deletion-impact-list">
            <li>
              <strong>删除场景</strong>：{impact.sceneIds.join(", ") || "无"}
            </li>
            <li>
              <strong>删除节拍</strong>：{impact.beatIds.join(", ") || "无"}
            </li>
            <li>
              <strong>删除 DialogueCue</strong>：
              {impact.cueIds.join(", ") || "无"}
            </li>
            <li>
              <strong>保留但会重新排序的场景</strong>：
              {impact.retainedSceneIds.join(", ") || "无"}
            </li>
            <li>
              <strong>保留但会重新排序的节拍</strong>：
              {impact.retainedBeatIds.join(", ") || "无"}
            </li>
          </ul>
          <section className="deletion-downstream" data-testid="downstream-storyboard-refs">
            <strong>下游分镜引用（保留但会变为 stale）</strong>
            {impact.retainedStoryboardReferences.length > 0 ? <ul>{impact.retainedStoryboardReferences.map((reference) => <li key={`${reference.kind}:${reference.path}`}><code>{reference.kind} · {reference.id}</code> · <code>{reference.path}</code></li>)}</ul> : <p>没有引用这些删除记录的分镜字段。</p>}
            <small>此确认不会修改、级联删除或重排分镜数据；请在分镜工作台显式处理这些 stale 引用。</small>
          </section>
          <p className="danger-copy">
            确认后只会修改当前未保存草稿；仍需点击“保存节拍计划”才会写入规范项目。
          </p>
        </div>
        <footer>
          <Button type="button" onClick={onCancel}>
            取消
          </Button>
          <Button
            type="button"
            variant="danger"
            autoFocus
            data-testid="confirm-delete"
            onClick={onConfirm}
          >
            确认删除
          </Button>
        </footer>
      </section>
    </div>
  );
}

function MigrationConfirmation({
  impact,
  onCancel,
  onConfirm,
}: {
  impact: SceneBeatsMigrationImpact;
  onCancel: () => void;
  onConfirm: () => void;
}) {
  const subject = impact.kind === "beat" ? "节拍" : "DialogueCue";
  return (
    <Panel
      className="notice warning"
      data-testid="relationship-migration-impact"
    >
      <strong>关系迁移确认</strong>
      <p>
        将 {subject} {impact.targetId} 从 {impact.fromParentId} 迁移到{" "}
        {impact.toParentId}。稳定 ID 保持不变；受影响的顺序和 scene.beatIds
        会确定性归一化。
      </p>
      <small>
        关联 cue：{impact.affectedCueIds.join(", ") || "无"}
        。不会自动重写分镜中的 cue 调度或
        ShotBeatLink/coverage；如存在跨场景关系，请在分镜工作台显式调整。
      </small>
      <div className="page-actions">
        <Button
          type="button"
          variant="primary"
          data-testid="confirm-relationship-migration"
          onClick={onConfirm}
        >
          确认迁移
        </Button>
        <Button type="button" onClick={onCancel}>
          取消
        </Button>
      </div>
    </Panel>
  );
}

function CueCard({
  cue,
  characters,
  beats = [],
  onFocus,
  onPatch,
  onMigrate = () => undefined,
  onMove,
  onDelete,
}: {
  cue: DialogueCue;
  characters?: SceneBeatsReferenceContext["characters"];
  beats?: Beat[];
  onFocus: (field?: string) => void;
  onPatch: (patch: Partial<Omit<DialogueCue, "id" | "beatId">>) => void;
  onMigrate?: (beatId: string) => void;
  onMove: (direction: -1 | 1) => void;
  onDelete: () => void;
}) {
  const entity: SceneBeatsEntity = { kind: "cue", id: cue.id };
  const usesSpeaker = cue.speakerId !== null;
  return (
    <EntityScope entity={entity} onFocus={onFocus}>
      <Panel className="beat-card" data-testid={`cue-card-${cue.id}`}>
        <div className="section-bar">
          <div>
            <span className="eyebrow">DialogueCue · {cue.id}</span>
            <strong>顺序 {cue.order}</strong>
          </div>
          <div className="page-actions">
            <Button type="button" variant="quiet" onClick={() => onMove(-1)}>
              ↑
            </Button>
            <Button type="button" variant="quiet" onClick={() => onMove(1)}>
              ↓
            </Button>
            <Button type="button" variant="danger" onClick={onDelete}>
              删除 cue
            </Button>
          </div>
        </div>
        <div className="field-grid two compact">
          {beats.length > 0 && (
            <Field label="所属节拍">
              <select
                {...focusProps(entity, "beatId")}
                aria-label="迁移 cue 到节拍"
                value={cue.beatId}
                onChange={(event) => onMigrate(event.target.value)}
              >
                {beats.map((beat) => (
                  <option key={beat.id} value={beat.id}>
                    {beat.order}. {beat.description || beat.id} · {beat.id}
                  </option>
                ))}
              </select>
            </Field>
          )}
          <Field label="发声来源">
            <select
              {...focusProps(entity, usesSpeaker ? "speakerId" : "voiceOver")}
              value={usesSpeaker ? "speaker" : "voiceOver"}
              onChange={(event) =>
                event.target.value === "speaker" && characters?.[0]
                  ? onPatch({ speakerId: characters[0].id, voiceOver: null })
                  : onPatch({
                      speakerId: null,
                      voiceOver: cue.voiceOver || "旁白",
                    })
              }
            >
              <option value="speaker" disabled={!characters?.length}>
                角色
              </option>
              <option value="voiceOver">画外音</option>
            </select>
          </Field>
          {usesSpeaker ? (
            <Field label="说话角色">
              <select
                {...focusProps(entity, "speakerId")}
                value={cue.speakerId || ""}
                onChange={(event) =>
                  onPatch({ speakerId: event.target.value, voiceOver: null })
                }
              >
                {characters?.map((character) => (
                  <option key={character.id} value={character.id}>
                    {character.name} · {character.id}
                  </option>
                ))}
              </select>
            </Field>
          ) : (
            <Field label="画外音身份">
              <input
                {...focusProps(entity, "voiceOver")}
                value={cue.voiceOver || "旁白"}
                onChange={(event) =>
                  onPatch({
                    speakerId: null,
                    voiceOver: event.target.value || "旁白",
                  })
                }
              />
            </Field>
          )}
          <Field label="语言">
            <input
              {...focusProps(entity, "language")}
              value={cue.language}
              onChange={(event) => onPatch({ language: event.target.value })}
            />
          </Field>
          <Field label="Delivery">
            <select
              {...focusProps(entity, "delivery")}
              value={cue.delivery}
              onChange={(event) =>
                onPatch({
                  delivery: event.target.value as DialogueCue["delivery"],
                })
              }
            >
              <option value="measured">measured</option>
              <option value="natural">natural</option>
              <option value="brisk">brisk</option>
            </select>
          </Field>
          <Field label="预估时长（毫秒）">
            <input
              {...focusProps(entity, "estimatedDurationUnits")}
              type="number"
              min={1}
              value={cue.estimatedDurationUnits}
              onChange={(event) =>
                onPatch({
                  estimatedDurationUnits: Math.max(
                    1,
                    Number(event.target.value) || 1,
                  ),
                })
              }
            />
          </Field>
          <Field label="表演备注">
            <input
              {...focusProps(entity, "performanceNotes")}
              value={cue.performanceNotes}
              onChange={(event) =>
                onPatch({ performanceNotes: event.target.value })
              }
            />
          </Field>
        </div>
        <Field label="对白文本">
          <textarea
            {...focusProps(entity, "text")}
            rows={3}
            value={cue.text}
            onChange={(event) => onPatch({ text: event.target.value })}
          />
        </Field>
      </Panel>
    </EntityScope>
  );
}

function BeatCard({
  beat,
  context,
  scenes = [],
  beats = [],
  cues,
  onFocus,
  onPatch,
  onMigrate = () => undefined,
  onMove,
  onDelete,
  onAddCue,
  onPatchCue,
  onMigrateCue = () => undefined,
  onMoveCue,
  onDeleteCue,
}: {
  beat: Beat;
  context: SceneBeatsReferenceContext;
  scenes?: SceneBeatPlan["scenes"];
  beats?: Beat[];
  cues: DialogueCue[];
  onFocus: (field?: string) => void;
  onPatch: (patch: Partial<Omit<Beat, "id" | "sceneId">>) => void;
  onMigrate?: (sceneId: string) => void;
  onMove: (direction: -1 | 1) => void;
  onDelete: () => void;
  onAddCue: () => void;
  onPatchCue: (
    id: string,
    patch: Partial<Omit<DialogueCue, "id" | "beatId">>,
  ) => void;
  onMigrateCue?: (id: string, beatId: string) => void;
  onMoveCue: (id: string, direction: -1 | 1) => void;
  onDeleteCue: (id: string) => void;
}) {
  const entity: SceneBeatsEntity = { kind: "beat", id: beat.id };
  return (
    <EntityScope entity={entity} onFocus={onFocus}>
      <Panel className="beat-card" data-testid={`beat-card-${beat.id}`}>
        <div className="section-bar">
          <div>
            <span className="eyebrow">Beat · {beat.id}</span>
            <h3>顺序 {beat.order}</h3>
          </div>
          <div className="page-actions">
            <Button type="button" variant="quiet" onClick={() => onMove(-1)}>
              ↑
            </Button>
            <Button type="button" variant="quiet" onClick={() => onMove(1)}>
              ↓
            </Button>
            <Button type="button" variant="danger" onClick={onDelete}>
              删除节拍
            </Button>
          </div>
        </div>
        <div className="field-grid two">
          <Field label="所属场景">
            <select
              {...focusProps(entity, "sceneId")}
              aria-label="迁移节拍到场景"
              value={beat.sceneId}
              onChange={(event) => onMigrate(event.target.value)}
            >
              {scenes.map((scene) => (
                <option key={scene.id} value={scene.id}>
                  {scene.order}. {scene.title || scene.id} · {scene.id}
                </option>
              ))}
            </select>
          </Field>
          <Field label="节拍描述">
            <textarea
              {...focusProps(entity, "description")}
              rows={3}
              value={beat.description}
              onChange={(event) => onPatch({ description: event.target.value })}
            />
          </Field>
          <Field label="可见事件">
            <textarea
              {...focusProps(entity, "visibleEvent")}
              rows={3}
              value={beat.visibleEvent}
              onChange={(event) =>
                onPatch({ visibleEvent: event.target.value })
              }
            />
          </Field>
          <Field label="叙事目的">
            <textarea
              {...focusProps(entity, "purpose")}
              rows={2}
              value={beat.purpose}
              onChange={(event) => onPatch({ purpose: event.target.value })}
            />
          </Field>
          <Field label="即时结果">
            <textarea
              {...focusProps(entity, "immediateResult")}
              rows={2}
              value={beat.immediateResult}
              onChange={(event) =>
                onPatch({ immediateResult: event.target.value })
              }
            />
          </Field>
          <Field label="戏剧变化">
            <textarea
              {...focusProps(entity, "dramaticChange")}
              rows={2}
              value={beat.dramaticChange}
              onChange={(event) =>
                onPatch({ dramaticChange: event.target.value })
              }
            />
          </Field>
          <Field label="连续性 anchors（每行一条）">
            <textarea
              {...focusProps(entity, "continuityAnchors")}
              rows={2}
              value={beat.continuityAnchors.join("\n")}
              onChange={(event) =>
                onPatch({ continuityAnchors: lines(event.target.value) })
              }
            />
          </Field>
          <TypedRecordEditor
            label="连续性 delta"
            value={beat.continuityDelta}
            onChange={(continuityDelta) => onPatch({ continuityDelta })}
            testId={`continuity-delta-${beat.id}`}
            focusKey={sceneBeatsFocusKey(entity, "continuityDelta")}
            focusField="continuityDelta"
          />
        </div>
        <ContinuityEditor
          label="节拍入口连续性"
          value={beat.entryState}
          context={context}
          entity={entity}
          field="entryState"
          onFocus={onFocus}
          onChange={(entryState) => onPatch({ entryState })}
        />
        <ContinuityEditor
          label="节拍出口连续性"
          value={beat.exitState}
          context={context}
          entity={entity}
          field="exitState"
          onFocus={onFocus}
          onChange={(exitState) => onPatch({ exitState })}
        />
        <div className="section-bar">
          <div>
            <span className="eyebrow">Canonical dialogue</span>
            <h3>DialogueCue</h3>
          </div>
          <Button type="button" variant="quiet" onClick={onAddCue}>
            ＋ 添加 cue
          </Button>
        </div>
        {cues.map((cue) => (
          <CueCard
            key={cue.id}
            cue={cue}
            characters={context.characters}
            beats={beats}
            onFocus={onFocus}
            onPatch={(patch) => onPatchCue(cue.id, patch)}
            onMigrate={(beatId) => onMigrateCue(cue.id, beatId)}
            onMove={(direction) => onMoveCue(cue.id, direction)}
            onDelete={() => onDeleteCue(cue.id)}
          />
        ))}
      </Panel>
    </EntityScope>
  );
}

export function SceneBeatsPage({
  value,
  stale,
  saving,
  entityId,
  onEntitySelect,
  onSave,
  onDraftChange,
  referenceContext = {},
  issues = [],
}: Props) {
  const [plan, setPlan] = useState(value);
  const [selectedId, setSelectedId] = useState(value.scenes[0]?.id || "");
  const [pendingDelete, setPendingDelete] = useState<DeleteImpact | null>(null);
  const [pendingMigration, setPendingMigration] = useState<{
    impact: SceneBeatsMigrationImpact;
    apply: () => void;
  } | null>(null);
  const [focus, setFocus] = useState<{
    entity: SceneBeatsEntity;
    field: string;
  } | null>(null);
  const lastIssueSignature = useRef<string | undefined>(undefined);
  const previousEntityId = useRef(entityId);
  const issueSignature = JSON.stringify(issues);
  const issueTarget = useMemo(
    () =>
      issues.map((issue) => sceneBeatsIssueTarget(plan, issue)).find(Boolean),
    [issues, plan],
  );
  const update = (
    next: SceneBeatPlan | ((current: SceneBeatPlan) => SceneBeatPlan),
  ) =>
    setPlan((current) => {
      const updated = typeof next === "function" ? next(current) : next;
      onDraftChange?.(updated);
      return updated;
    });
  const selectEntity = (
    entity: SceneBeatsEntity,
    field = "entity",
    emit = true,
  ) => {
    const sceneId =
      entity.kind === "scene"
        ? entity.id
        : entity.kind === "beat"
          ? plan.beats.find((beat) => beat.id === entity.id)?.sceneId
          : plan.beats.find(
              (beat) =>
                beat.id ===
                plan.dialogueCues.find((cue) => cue.id === entity.id)?.beatId,
            )?.sceneId;
    if (!sceneId || !plan.scenes.some((scene) => scene.id === sceneId)) return;
    setSelectedId(sceneId);
    setFocus({ entity, field });
    if (emit) onEntitySelect?.(sceneBeatsEntityIdentity(entity));
  };
  useEffect(() => {
    const requested = parseSceneBeatsEntityIdentity(entityId);
    if (requested) selectEntity(requested, "entity", false);
  }, [entityId, plan]);
  useEffect(() => {
    const previous = previousEntityId.current;
    previousEntityId.current = entityId;
    if (previous && !entityId) {
      const firstSceneId = plan.scenes[0]?.id || "";
      setSelectedId(firstSceneId);
      setFocus(
        firstSceneId
          ? { entity: { kind: "scene", id: firstSceneId }, field: "entity" }
          : null,
      );
    }
  }, [entityId, plan.scenes]);
  useEffect(() => {
    if (!issues.length) {
      lastIssueSignature.current = undefined;
      return;
    }
    if (!issueTarget || issueSignature === lastIssueSignature.current) return;
    lastIssueSignature.current = issueSignature;
    selectEntity(issueTarget.entity, issueTarget.field);
  }, [issueSignature, issueTarget, issues.length]);
  useEffect(() => {
    if (!focus) return;
    const key = sceneBeatsFocusKey(focus.entity, focus.field);
    const target =
      [...document.querySelectorAll<HTMLElement>("[data-focus-key]")].find(
        (element) => element.dataset.focusKey === key,
      ) ||
      [...document.querySelectorAll<HTMLElement>("[data-entity-key]")].find(
        (element) =>
          element.dataset.entityKey === sceneBeatsEntityIdentity(focus.entity),
      );
    target?.focus();
  }, [focus, selectedId]);
  const selected = plan.scenes.find((scene) => scene.id === selectedId);
  const beats = plan.beats
    .filter((beat) => beat.sceneId === selectedId)
    .sort((left, right) => left.order - right.order);
  const confirmDelete = () => {
    if (!pendingDelete) return;
    const next = applyDeleteImpact(plan, pendingDelete);
    update(next);
    if (pendingDelete.sceneIds.includes(selectedId))
      setSelectedId(next.scenes[0]?.id || "");
    setPendingDelete(null);
  };
  const requestBeatMigration = (beatId: string, sceneId: string) => {
    try {
      const impact = beatMigrationImpact(plan, beatId, sceneId);
      if (impact.fromParentId === impact.toParentId) return;
      setPendingMigration({
        impact,
        apply: () =>
          update((current) => migrateBeatToScene(current, beatId, sceneId)),
      });
    } catch {
      /* Select options are plan-owned; malformed drafts retain their current relation. */
    }
  };
  const requestCueMigration = (cueId: string, beatId: string) => {
    try {
      const impact = cueMigrationImpact(plan, cueId, beatId);
      if (impact.fromParentId === impact.toParentId) return;
      setPendingMigration({
        impact,
        apply: () =>
          update((current) => migrateCueToBeat(current, cueId, beatId)),
      });
    } catch {
      /* Select options are plan-owned; malformed drafts retain their current relation. */
    }
  };
  const focusScene = (sceneId: string) =>
    selectEntity({ kind: "scene", id: sceneId });
  return (
    <div className="page" data-testid="scene-beats-page">
      <PageHeader
        eyebrow="04 · Scene decomposition"
        title="场景、节拍与对白"
        description="场景按剧情节点排序；节拍与 DialogueCue 用稳定 ID 和结构化连续性数据驱动分镜。"
        actions={
          <>
            <span className={`stage-chip ${stale ? "stale" : "ready"}`}>
              {stale
                ? "剧情图已变化"
                : `${plan.scenes.length} 个场景 · ${plan.beats.length} 个节拍`}
            </span>
            <Button
              variant="primary"
              disabled={saving}
              onClick={() => void onSave(plan)}
            >
              {saving ? "正在保存…" : "保存节拍计划"}
            </Button>
          </>
        }
      />
      {issues.length > 0 && (
        <Panel className="notice error" data-testid="scene-beats-issues">
          <strong>需要修复的合同问题</strong>
          <ul>
            {issues.map((issue, index) => {
              const target = sceneBeatsIssueTarget(plan, issue);
              return (
                <li key={`${issue.code}:${issue.path}:${index}`}>
                  <button
                    type="button"
                    data-entity-key={
                      target
                        ? sceneBeatsEntityIdentity(target.entity)
                        : undefined
                    }
                    onClick={() =>
                      target && selectEntity(target.entity, target.field)
                    }
                  >
                    <code>{issue.path}</code> · {issue.message}
                  </button>
                </li>
              );
            })}
          </ul>
        </Panel>
      )}
      {pendingDelete && (
        <DeleteConfirmation
          impact={pendingDelete}
          onCancel={() => setPendingDelete(null)}
          onConfirm={confirmDelete}
        />
      )}
      {pendingMigration && (
        <MigrationConfirmation
          impact={pendingMigration.impact}
          onCancel={() => setPendingMigration(null)}
          onConfirm={() => {
            const apply = pendingMigration.apply;
            setPendingMigration(null);
            apply();
          }}
        />
      )}
      <div className="beats-layout">
        <nav
          className="scene-rail"
          aria-label="场景列表"
          data-testid="scene-list"
        >
          {plan.scenes.map((scene) => (
            <button
              key={scene.id}
              data-testid={`scene-card-${scene.id}`}
              data-entity-key={sceneBeatsEntityIdentity({
                kind: "scene",
                id: scene.id,
              })}
              className={scene.id === selectedId ? "active" : ""}
              onClick={() => focusScene(scene.id)}
            >
              <span>{scene.order.toString().padStart(2, "0")}</span>
              <strong>{scene.title || scene.id}</strong>
              <small>
                {plan.beats.filter((beat) => beat.sceneId === scene.id).length}{" "}
                beats · {scene.storyNodeId || "未绑定节点"}
              </small>
            </button>
          ))}
          <Button
            type="button"
            variant="quiet"
            onClick={() =>
              update(
                addScene(plan, newId, referenceContext.nodes?.[0]?.id || ""),
              )
            }
          >
            ＋ 添加场景
          </Button>
        </nav>
        <div className="beat-editor" data-testid="scene-editor">
          {!selected && (
            <Panel className="empty-state">
              <strong>尚无场景</strong>
              <p>先创建场景，再添加节拍与对白。</p>
            </Panel>
          )}
          {selected && (
            <EntityScope
              entity={{ kind: "scene", id: selected.id }}
              onFocus={(field) =>
                selectEntity({ kind: "scene", id: selected.id }, field)
              }
            >
              <Panel className="form-card">
                <div className="section-bar">
                  <div>
                    <span className="eyebrow">
                      DramaticScene · {selected.id}
                    </span>
                    <h2>{selected.title || "未命名场景"}</h2>
                  </div>
                  <div className="page-actions">
                    <Button
                      type="button"
                      variant="quiet"
                      onClick={() =>
                        update(reorderScene(plan, selected.id, -1))
                      }
                    >
                      ↑ 场景
                    </Button>
                    <Button
                      type="button"
                      variant="quiet"
                      onClick={() => update(reorderScene(plan, selected.id, 1))}
                    >
                      ↓ 场景
                    </Button>
                    <Button
                      type="button"
                      variant="danger"
                      onClick={() =>
                        setPendingDelete(sceneDeleteImpact(plan, selected.id, referenceContext.storyboard))
                      }
                    >
                      删除场景
                    </Button>
                  </div>
                </div>
                <div className="field-grid two">
                  <Field label="稳定 ID">
                    <input
                      {...focusProps({ kind: "scene", id: selected.id }, "id")}
                      readOnly
                      value={selected.id}
                    />
                  </Field>
                  <Field label="剧情节点">
                    <select
                      {...focusProps(
                        { kind: "scene", id: selected.id },
                        "storyNodeId",
                      )}
                      value={selected.storyNodeId}
                      onChange={(event) =>
                        update(
                          patchScene(plan, selected.id, {
                            storyNodeId: event.target.value,
                          }),
                        )
                      }
                    >
                      <option value="">选择节点</option>
                      {referenceContext.nodes?.map((node) => (
                        <option key={node.id} value={node.id}>
                          {node.title} · {node.id}
                        </option>
                      ))}
                    </select>
                  </Field>
                  <Field label="场景标题">
                    <input
                      {...focusProps(
                        { kind: "scene", id: selected.id },
                        "title",
                      )}
                      value={selected.title}
                      onChange={(event) =>
                        update(
                          patchScene(plan, selected.id, {
                            title: event.target.value,
                          }),
                        )
                      }
                    />
                  </Field>
                  <Field label="戏剧目标">
                    <input
                      {...focusProps(
                        { kind: "scene", id: selected.id },
                        "objective",
                      )}
                      value={selected.objective}
                      onChange={(event) =>
                        update(
                          patchScene(plan, selected.id, {
                            objective: event.target.value,
                          }),
                        )
                      }
                    />
                  </Field>
                  <Field label="地点">
                    <select
                      {...focusProps(
                        { kind: "scene", id: selected.id },
                        "locationId",
                      )}
                      value={selected.locationId || ""}
                      onChange={(event) =>
                        update(
                          patchScene(plan, selected.id, {
                            locationId: event.target.value || null,
                          }),
                        )
                      }
                    >
                      <option value="">未指定</option>
                      {referenceContext.locations?.map((location) => (
                        <option key={location.id} value={location.id}>
                          {location.name} · {location.id}
                        </option>
                      ))}
                    </select>
                  </Field>
                  <Field label="时长预算（毫秒）">
                    <input
                      {...focusProps(
                        { kind: "scene", id: selected.id },
                        "durationBudgetUnits",
                      )}
                      type="number"
                      min={1}
                      value={selected.durationBudgetUnits}
                      onChange={(event) =>
                        update(
                          patchScene(plan, selected.id, {
                            durationBudgetUnits: Math.max(
                              1,
                              Number(event.target.value) || 1,
                            ),
                          }),
                        )
                      }
                    />
                  </Field>
                  <Field label="出场角色（多选）">
                    <select
                      {...focusProps(
                        { kind: "scene", id: selected.id },
                        "characterIds",
                      )}
                      multiple
                      value={selected.characterIds}
                      onChange={(event) =>
                        update(
                          patchScene(plan, selected.id, {
                            characterIds: [
                              ...event.currentTarget.selectedOptions,
                            ].map((option) => option.value),
                          }),
                        )
                      }
                    >
                      {referenceContext.characters?.map((character) => (
                        <option key={character.id} value={character.id}>
                          {character.name} · {character.id}
                        </option>
                      ))}
                    </select>
                  </Field>
                  <Field label="声明的 beat IDs">
                    <textarea
                      {...focusProps(
                        { kind: "scene", id: selected.id },
                        "beatIds",
                      )}
                      readOnly
                      rows={3}
                      value={selected.beatIds.join("\n")}
                    />
                  </Field>
                </div>
                <ContinuityEditor
                  label="场景入口连续性"
                  value={selected.entryState}
                  context={referenceContext}
                  entity={{ kind: "scene", id: selected.id }}
                  field="entryState"
                  onFocus={(field) =>
                    selectEntity({ kind: "scene", id: selected.id }, field)
                  }
                  onChange={(entryState) =>
                    update(patchScene(plan, selected.id, { entryState }))
                  }
                />
                <ContinuityEditor
                  label="场景出口连续性"
                  value={selected.exitState}
                  context={referenceContext}
                  entity={{ kind: "scene", id: selected.id }}
                  field="exitState"
                  onFocus={(field) =>
                    selectEntity({ kind: "scene", id: selected.id }, field)
                  }
                  onChange={(exitState) =>
                    update(patchScene(plan, selected.id, { exitState }))
                  }
                />
              </Panel>
            </EntityScope>
          )}{" "}
          {selected && (
            <>
              <div className="section-bar">
                <div>
                  <span className="eyebrow">Beat order</span>
                  <h2>节拍</h2>
                </div>
                <Button
                  type="button"
                  variant="quiet"
                  onClick={() => update(addBeat(plan, selected.id, newId))}
                >
                  ＋ 添加节拍
                </Button>
              </div>
              {beats.map((beat) => (
                <BeatCard
                  key={beat.id}
                  beat={beat}
                  context={referenceContext}
                  scenes={plan.scenes}
                  beats={plan.beats}
                  cues={plan.dialogueCues
                    .filter((cue) => cue.beatId === beat.id)
                    .sort((left, right) => left.order - right.order)}
                  onFocus={(field) =>
                    selectEntity({ kind: "beat", id: beat.id }, field)
                  }
                  onPatch={(patch) => update(patchBeat(plan, beat.id, patch))}
                  onMigrate={(sceneId) =>
                    requestBeatMigration(beat.id, sceneId)
                  }
                  onMove={(direction) =>
                    update(reorderBeat(plan, beat.id, direction))
                  }
                  onDelete={() =>
                    setPendingDelete(beatDeleteImpact(plan, beat.id, referenceContext.storyboard))
                  }
                  onAddCue={() => update(addCue(plan, beat.id, newId))}
                  onPatchCue={(id, patch) => update(patchCue(plan, id, patch))}
                  onMigrateCue={requestCueMigration}
                  onMoveCue={(id, direction) =>
                    update(reorderCue(plan, id, direction))
                  }
          onDeleteCue={(id) => setPendingDelete(cueDeleteImpact(plan, id, referenceContext.storyboard))}
                />
              ))}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
