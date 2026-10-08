import type { CharacterCard, LocationCard, PropCard } from "../types";
import { Field } from "../components";

const splitLines = (value: string) =>
  value
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean);
const joinLines = (value: string[]) => value.join("\n");

export function LinesField({
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

export function CharacterInspector({
  entity,
  onChange,
}: {
  entity: CharacterCard;
  onChange: (patch: Partial<CharacterCard>) => void;
}) {
  return (
    <div className="field-grid two" data-testid="character-inspector">
      <Field label="固定标识（ID）">
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
        label="视觉特征（每行一条）"
        value={entity.visualAnchors}
        onChange={(visualAnchors) => onChange({ visualAnchors })}
        testId="character-visual-anchors"
        field="visualAnchors"
      />
      <LinesField
        label="声音特征（每行一条）"
        value={entity.soundAnchors}
        onChange={(soundAnchors) => onChange({ soundAnchors })}
        testId="character-sound-anchors"
        field="soundAnchors"
      />
      <LinesField
        label="声线特征（每行一条）"
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

export function WorldEntityInspector({
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
      <Field label="固定标识（ID）">
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
        label="视觉特征（每行一条）"
        value={entity.visualAnchors}
        onChange={(visualAnchors) => onChange({ visualAnchors })}
        testId={`${type}-visual-anchors`}
        field="visualAnchors"
      />
      <LinesField
        label="声音特征（每行一条）"
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
