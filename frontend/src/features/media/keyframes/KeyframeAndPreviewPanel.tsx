import type { Dispatch, SetStateAction } from "react";
import type {
  ImageJob,
  ManagedAsset,
  ReviewedKeyframe,
  Shot,
  StillPreview,
  StoryboardReview,
  VisualIntent,
  VisualWorkbench,
} from "../../../types";
import { plotloomApi } from "../../../api";
import { Badge, Button, Field } from "../../../components";
import { useVisualIntentDraft } from "../../../visual-intent-drafts";

type IntentEditor = ReturnType<typeof useVisualIntentDraft>;
type IdentityMapping = NonNullable<
  NonNullable<ImageJob["request"]["frozenSnapshot"]>["characterIdentity"]
>[number];

function stateTone(state: StillPreview["state"]): "ok" | "warning" | "danger" {
  return state === "current" ? "ok" : state === "stale" ? "warning" : "danger";
}

function stateGuidance(state: StillPreview["state"]): string | null {
  if (state === "stale")
    return "冻结历史仍可检查；当前选择或意图已变化，重新审核后创建新的预览。";
  if (state === "revoked")
    return "冻结历史仍可检查；先恢复当前 storyboard Approval，才能创建新的预览。";
  if (state === "missing")
    return "冻结历史引用的存储字节不可读取；不要把它当作可用关键帧。";
  if (state === "corrupt")
    return "冻结历史的完整性校验失败；停止使用并调查存储或 receipt。";
  return null;
}

export function KeyframeAndPreviewPanel({
  projectId,
  workbench,
  selectedShot,
  selectedBinding,
  keptAssetId,
  retainedIdentityMapping,
  assetById,
  intentEditor,
  activeIntent,
  compatibility,
  setCompatibility,
  readOnly,
  busy,
  mediaDraftsEnabled,
  review,
  maxPreviewLength,
  previewLength,
  setPreviewLength,
  previewShotIds,
  missingPreviewShotIds,
  identityReviewMissingShotIds,
  preview,
  previewId,
  frameIndex,
  setFrameIndex,
  playing,
  setPlaying,
  onSaveIntent,
  onSelectKeyframe,
  onCreatePreview,
  onSelectPreview,
}: {
  projectId?: string;
  workbench: VisualWorkbench;
  selectedShot: Shot | undefined;
  selectedBinding: ReviewedKeyframe | undefined;
  keptAssetId: string;
  retainedIdentityMapping: IdentityMapping[];
  assetById: Map<string, ManagedAsset>;
  intentEditor: IntentEditor;
  activeIntent: VisualIntent | undefined;
  compatibility: string;
  setCompatibility: Dispatch<SetStateAction<string>>;
  readOnly: boolean;
  busy: boolean;
  mediaDraftsEnabled: boolean;
  review: StoryboardReview | null | undefined;
  maxPreviewLength: number;
  previewLength: number;
  setPreviewLength: Dispatch<SetStateAction<number>>;
  previewShotIds: string[];
  missingPreviewShotIds: string[];
  identityReviewMissingShotIds: string[];
  preview: StillPreview | undefined;
  previewId: string;
  frameIndex: number;
  setFrameIndex: Dispatch<SetStateAction<number>>;
  playing: boolean;
  setPlaying: Dispatch<SetStateAction<boolean>>;
  onSaveIntent: () => void;
  onSelectKeyframe: () => void;
  onCreatePreview: () => void;
  onSelectPreview: (previewId: string) => void;
}) {
  const intentDraft = intentEditor.value;
  const setIntentDraft = intentEditor.update;
  const currentApproval = review?.activeApproval;
  return (
    <>
      {!selectedBinding &&
        keptAssetId &&
        retainedIdentityMapping.length > 0 && (
          <section
            className="intent-editor"
            data-testid="frozen-reference-history"
            aria-label="历史候选的冻结身份参考"
          >
            <strong>历史候选的冻结身份参考 · inapplicable/history</strong>
            <p className="muted">
              当前 reference 已替换或关联选择已失效。该候选与其冻结
              primary/complementary 参考仍可检查；它不会改用当前
              reference，也不能重新进入 preview。
            </p>
            <div className="frozen-review-comparison">
              <article className="media-candidate">
                {projectId && assetById.get(keptAssetId) ? (
                  <>
                    <img
                      src={plotloomApi.managedAssetUrl(projectId, keptAssetId)}
                      alt="historic selected candidate"
                    />
                    <strong>
                      historic candidate · {keptAssetId.slice(0, 8)}
                    </strong>
                  </>
                ) : (
                  <small>Historic candidate bytes are unavailable.</small>
                )}
              </article>
              {retainedIdentityMapping.flatMap((mapping) =>
                mapping.assets.map((asset, index) => {
                  const frozenAsset = assetById.get(asset.assetId);
                  return (
                    <article
                      className="media-candidate"
                      key={`historic:${mapping.referenceDecisionId}:${asset.assetId}`}
                      data-testid={`frozen-reference-history-${asset.assetId}`}
                    >
                      {projectId && frozenAsset ? (
                        <img
                          src={plotloomApi.managedAssetUrl(
                            projectId,
                            frozenAsset.id,
                          )}
                          alt={`${mapping.characterId} historic frozen ${index === 0 ? "primary" : "complementary"} reference`}
                        />
                      ) : (
                        <small>
                          Frozen asset {asset.assetId.slice(0, 8)} is
                          unavailable.
                        </small>
                      )}
                      <strong>
                        {mapping.characterId} ·{" "}
                        {index === 0 ? "primary" : `complementary ${index}`} ·
                        frozen r{mapping.referenceRevision}
                      </strong>
                      <small>
                        historic decision{" "}
                        {mapping.referenceDecisionId.slice(0, 8)} ·{" "}
                        {asset.originalHash.slice(0, 12)}
                      </small>
                    </article>
                  );
                }),
              )}
            </div>
          </section>
        )}
      {keptAssetId && (
        <section className="intent-editor" aria-label="可审核视觉意图">
          <strong>为保留候选记录可审核意图 · shot_keyframe</strong>
          {intentEditor.dirty && (
            <div className="notice warning" role="status">
              <span>
                {intentEditor.stale
                  ? "已保存意图已有新版本；草稿未被覆盖。"
                  : "有未保存的意图草稿；切换镜头或候选不会丢失。先保存再审核选择。"}
              </span>
              <Button variant="quiet" onClick={intentEditor.clear}>
                放弃草稿，载入已保存意图
              </Button>
            </div>
          )}
          {intentEditor.storageFailed && (
            <small role="alert">
              浏览器暂时无法保存会话草稿，请保持本页打开并保存意图。
            </small>
          )}
          {intentEditor.serverConflict && (
            <small role="alert">服务器上的视觉意图草稿已更新；当前文本未覆盖它。请重新载入或明确放弃本地版本。</small>
          )}
          <div className="field-grid two compact">
            <Field label="身份意图">
              <textarea
                rows={2}
                disabled={readOnly || busy}
                value={intentDraft.identityIntent}
                onChange={(event) =>
                  setIntentDraft((draft) => ({
                    ...draft,
                    identityIntent: event.target.value,
                  }))
                }
              />
            </Field>
            <Field label="构图意图">
              <textarea
                rows={2}
                disabled={readOnly || busy}
                value={intentDraft.compositionIntent}
                onChange={(event) =>
                  setIntentDraft((draft) => ({
                    ...draft,
                    compositionIntent: event.target.value,
                  }))
                }
              />
            </Field>
            <Field label="风格意图">
              <textarea
                rows={2}
                disabled={readOnly || busy}
                value={intentDraft.styleIntent}
                onChange={(event) =>
                  setIntentDraft((draft) => ({
                    ...draft,
                    styleIntent: event.target.value,
                  }))
                }
              />
            </Field>
            <Field label="来源引用（每行一项）">
              <textarea
                data-testid="visual-intent-source-refs"
                rows={2}
                disabled={readOnly || busy}
                value={intentDraft.sourceRefs}
                onChange={(event) =>
                  setIntentDraft((draft) => ({
                    ...draft,
                    sourceRefs: event.target.value,
                  }))
                }
              />
            </Field>
          </div>
          <div className="button-row">
            <Button
              data-testid="save-visual-intent"
              variant="quiet"
              disabled={readOnly || busy || intentEditor.stale || (mediaDraftsEnabled && (
                !intentEditor.serverReady
                || intentEditor.serverRevision < 1
                || intentEditor.serverConflict
              ))}
              onClick={() => void onSaveIntent()}
            >
              {activeIntent ? `细化意图 r${activeIntent.revision}` : "保存意图"}
            </Button>
            {activeIntent && (
              <small>
                已保存 r{activeIntent.revision}；审核选择会固定这一版本。
              </small>
            )}
          </div>
        </section>
      )}
      <Field label="审核兼容性说明">
        <textarea
          rows={2}
          placeholder="说明此参考与当前已批准镜头为何兼容"
          disabled={readOnly || busy}
          value={compatibility}
          onChange={(event) => setCompatibility(event.target.value)}
        />
      </Field>
      <div className="button-row">
        <Button
          variant="primary"
          data-testid="select-reviewed-keyframe"
          disabled={
            readOnly ||
            busy ||
            intentEditor.dirty ||
            !keptAssetId ||
            !selectedShot ||
            !currentApproval ||
            !activeIntent ||
            !compatibility.trim()
          }
          onClick={() => void onSelectKeyframe()}
        >
          为当前 Shot 审核选择
        </Button>
        <Field label="连续预览镜头数">
          <select
            data-testid="preview-subset-length"
            value={Math.min(previewLength, maxPreviewLength || 1)}
            disabled={readOnly || busy || !maxPreviewLength}
            onChange={(event) => setPreviewLength(Number(event.target.value))}
          >
            {Array.from(
              { length: maxPreviewLength },
              (_, index) => index + 1,
            ).map((length) => (
              <option value={length} key={length}>
                {length}
              </option>
            ))}
          </select>
        </Field>
        <Button
          variant="primary"
          data-testid="create-still-preview"
          disabled={
            readOnly ||
            busy ||
            !previewShotIds.length ||
            !!missingPreviewShotIds.length ||
            !!identityReviewMissingShotIds.length ||
            !currentApproval
          }
          onClick={() => void onCreatePreview()}
        >
          创建连续 still animatic
        </Button>
      </div>
      {!currentApproval && (
        <small className="notice warning">
          需要当前 storyboard Approval；导入、比较和意图细化仍可继续。
        </small>
      )}
      {!!previewShotIds.length && (
        <small>
          {previewShotIds.join(" → ")} ·{" "}
          {missingPreviewShotIds.length
            ? `尚缺 ${missingPreviewShotIds.length} 个审核关键帧：${missingPreviewShotIds.join("、")}`
            : identityReviewMissingShotIds.length
              ? `尚缺 ${identityReviewMissingShotIds.length} 个身份感知关键帧的人工复核：${identityReviewMissingShotIds.join("、")}`
              : "所有镜头已有当前审核关键帧和所需身份复核，可冻结预览。"}
        </small>
      )}
      <div className="preview-history">
        <strong>冻结预览历史</strong>
        {workbench.previews.map((item) => (
          <button
            key={item.id}
            className={item.id === previewId ? "selected" : ""}
            onClick={() => onSelectPreview(item.id)}
          >
            {item.manifest.shotIds.join(" → ")}{" "}
            <Badge tone={stateTone(item.state)}>
              {item.state.toUpperCase()}
            </Badge>
          </button>
        ))}
      </div>
      {preview && (
        <AnimaticPlayer
          preview={preview}
          projectId={projectId}
          frameIndex={frameIndex}
          playing={playing}
          onSeek={setFrameIndex}
          onPlay={() => setPlaying((current) => !current)}
        />
      )}
    </>
  );
}

function AnimaticPlayer({
  preview,
  projectId,
  frameIndex,
  playing,
  onSeek,
  onPlay,
}: {
  preview: StillPreview;
  projectId?: string;
  frameIndex: number;
  playing: boolean;
  onSeek: (index: number) => void;
  onPlay: () => void;
}) {
  const frame = preview.manifest.frames[frameIndex];
  return (
    <div className="still-animatic" data-testid="still-animatic">
      <div>
        <Badge tone={stateTone(preview.state)}>
          {preview.state.toUpperCase()}
        </Badge>
        <strong>
          {" "}
          Reviewed still animatic · {preview.manifest.shotIds.join(" → ")}
        </strong>
      </div>
      {stateGuidance(preview.state) && (
        <small className="notice warning">{stateGuidance(preview.state)}</small>
      )}
      {frame && projectId && (
        <img
          src={plotloomApi.managedAssetUrl(projectId, frame.assetId)}
          alt={`Shot ${frame.shotId} reviewed still`}
        />
      )}
      <div className="button-row">
        <Button
          data-testid="animatic-play-pause"
          variant="primary"
          onClick={onPlay}
        >
          {playing ? "暂停" : "播放"}
        </Button>
        <Button
          variant="quiet"
          onClick={() => onSeek(Math.max(0, frameIndex - 1))}
        >
          上一镜头
        </Button>
        <Button
          variant="quiet"
          onClick={() =>
            onSeek(Math.min(preview.manifest.frames.length - 1, frameIndex + 1))
          }
        >
          下一镜头
        </Button>
        <input
          data-testid="animatic-seek"
          type="range"
          min={0}
          max={Math.max(0, preview.manifest.frames.length - 1)}
          value={frameIndex}
          onChange={(event) => onSeek(Number(event.target.value))}
        />
      </div>
      <small>
        {frame
          ? `${frame.shotId} · ${frame.durationMs}ms · frozen ${preview.manifestHash.slice(0, 12)}`
          : "空预览"}
      </small>
    </div>
  );
}
