import { useState, type Dispatch, type SetStateAction } from "react";
import type { ImageJob, ReviewedKeyframe } from "../../../types";
import { Badge, Button, Field } from "../../../components";
import {
  type ImageJobDraftTarget,
  useImageJobDirectionDraft,
} from "../../../visual-intent-drafts";
import type { MediaReadPhase } from "../useMediaWorkbenchData";
import { shotImageJobs } from "./image-job-visibility";
import { imageJobNotice } from "./image-job-state";

type ImageJobDirection = ReturnType<typeof useImageJobDirectionDraft>;
type DeliveryCandidate = ImageJob["deliveries"][number]["candidates"][number];
const imageJobStateLabel: Record<ImageJob["state"], string> = { prepared: "已准备", exported: "待交付", delivered: "已交付", cancelled: "已取消" };
const deliveryStateLabel: Record<ImageJob["deliveries"][number]["state"], string> = { accepted: "交付检查通过", inapplicable: "当前不适用", rejected: "交付检查未通过" };
const candidateRoleLabel: Record<DeliveryCandidate["role"], string> = { original: "原始图片", refinement: "参考细化", keyframe_adaptation: "关键帧比例适配" };

export function ImageJobPanel({
  imageExchangeConfigured,
  prerequisite: imageJobPrerequisite,
  target: imageJobTarget,
  setTarget: setImageJobTarget,
  eligibleRefinementCandidates,
  direction: imageJobDirection,
  mediaDraftsEnabled,
  readOnly,
  busy,
  imageJobs,
  shotId,
  mediaReadPhase = "ready",
  imageJobRefreshNotice,
  selectedBinding,
  onPrepare,
  onCopy,
  onRefresh,
  onCancel,
}: {
  imageExchangeConfigured: boolean;
  prerequisite: string | null;
  target: ImageJobDraftTarget;
  setTarget: Dispatch<SetStateAction<ImageJobDraftTarget>>;
  eligibleRefinementCandidates: DeliveryCandidate[];
  direction: ImageJobDirection;
  mediaDraftsEnabled: boolean;
  readOnly: boolean;
  busy: boolean;
  imageJobs: ImageJob[];
  shotId?: string;
  mediaReadPhase?: MediaReadPhase;
  imageJobRefreshNotice: Record<string, string>;
  selectedBinding: ReviewedKeyframe | undefined;
  onPrepare: () => void;
  onCopy: (jobId: string) => void;
  onRefresh: (jobId: string) => void;
  onCancel: (jobId: string) => void;
}) {
  const [showProjectHistory, setShowProjectHistory] = useState(false);
  const scopedJobs = shotImageJobs(imageJobs, shotId);
  const visibleJobs = showProjectHistory ? imageJobs : scopedJobs;
  const mediaKnown = mediaReadPhase === "ready";
  return (
      <section className="image-job-panel" data-testid="image-job-panel">
        <div className="section-title">
          <span>镜头图片</span>
          <strong>准备任务 → 发送 → 等待交付 → 审核选择</strong>
        </div>
        {!mediaKnown && <small role="status">{mediaReadPhase === "loading" ? "正在读取图片请求与配置状态…" : "图片请求与配置状态暂时未知，请刷新媒体状态。"}</small>}
        {mediaKnown && !imageExchangeConfigured && (
          <div className="notice warning">
            图片任务的本机交付目录尚未配置，请联系管理员。技术设置为{" "}
            <code>PLOTLOOM_IMAGE_EXCHANGE_ROOT</code>；不会自动改用其他图像服务。
          </div>
        )}
        <p className="muted">
          当前分镜须先通过批准。准备任务会固定当前镜头和角色参考；发送后由图像生成助手执行。结果通过检查后才会显示为候选，还需要你审核选择。排队不代表生成完成，也不会自动批准或选用。
        </p>
        {mediaKnown && imageJobPrerequisite && (
          <div className="notice warning" data-testid="image-job-prerequisite">
            {imageJobPrerequisite}
          </div>
        )}
        <Field label="请求目标">
          <select
            data-testid="image-job-target"
            value={
              imageJobTarget.kind === "original"
                ? "original"
                : imageJobTarget.kind === "refinement"
                  ? `refinement:${imageJobTarget.parentCandidateAssetId}`
                  : `keyframe_adaptation:${imageJobTarget.profileId}`
            }
            disabled={readOnly || busy}
            onChange={(event) => {
              const value = event.target.value;
              setImageJobTarget(
                value === "original"
                  ? { kind: "original" }
                  : value.startsWith("refinement:") ? {
                      kind: "refinement",
                      parentCandidateAssetId: value.slice("refinement:".length),
                    } : imageJobTarget.kind === "keyframe_adaptation"
                      ? imageJobTarget
                      : { kind: "original" },
              );
            }}
          >
            <option value="original">原始图 · 当前已批准镜头</option>
            {eligibleRefinementCandidates.map((candidate) => (
              <option
                key={candidate.assetId}
                value={`refinement:${candidate.assetId}`}
              >
                参考细化 · 当前已审核候选 {candidate.assetId.slice(0, 8)}
              </option>
            ))}
            {imageJobTarget.kind === "keyframe_adaptation" && (
              <option value={`keyframe_adaptation:${imageJobTarget.profileId}`}>
                比例适配 · 当前审核关键帧 → {imageJobTarget.profileLabel}
              </option>
            )}
          </select>
        </Field>
        <Field label={imageJobTarget.kind === "keyframe_adaptation" ? "冻结的画面呈现 / 比例适配方向" : "冻结的画面呈现 / 细化变化"} required>
          <textarea
            aria-required="true"
            data-testid="image-job-presentation-change"
            rows={3}
            value={imageJobDirection.value}
            disabled={readOnly || busy}
            onChange={(event) => imageJobDirection.update(event.target.value)}
            placeholder={imageJobTarget.kind === "keyframe_adaptation"
              ? "例如：扩展为完整竖幅构图；保留人物身份、服装、空间与镜头意图，不保留黑边。"
              : "例如：保持父图构图，在实用控制台灯下提升面部清晰度。"}
          />
        </Field>
        {imageJobDirection.stale && (
          <div
            className="notice warning"
            role="status"
            data-testid="image-job-direction-stale"
          >
            这个会话草稿来自旧的
            分镜批准、镜头或参考上下文。文本已保留但不会自动提交。
            <Button
              variant="quiet"
              onClick={imageJobDirection.recoverForCurrentContext}
            >
              确认后恢复到当前上下文
            </Button>
            <Button variant="quiet" onClick={imageJobDirection.clear}>
              放弃此草稿
            </Button>
          </div>
        )}
        {imageJobDirection.dirty && !imageJobDirection.stale && (
          <div className="button-row">
            <small data-testid="image-job-direction-draft">
              方向草稿按当前分镜版本和目标保存；切换镜头、目标或刷新后可恢复。若上下文已变化，系统不会用旧草稿覆盖新版本。
            </small>
            <Button
              data-testid="discard-image-job-direction"
              variant="quiet"
              onClick={imageJobDirection.clear}
            >
              放弃此草稿
            </Button>
          </div>
        )}
        {imageJobDirection.storageFailed && (
          <small role="alert">
            浏览器暂时无法保存方向草稿；请保持本页打开并在准备前复制文本。
          </small>
        )}
        {imageJobDirection.serverConflict && (
          <small role="alert">服务器上的方向草稿已更新；当前文本未覆盖它。请重新载入或明确放弃本地版本。</small>
        )}
        <div className="button-row">
          <Button
            data-testid="prepare-image-job"
            variant="primary"
            disabled={
              readOnly ||
              busy ||
              !!imageJobPrerequisite ||
              imageJobDirection.stale ||
              (mediaDraftsEnabled && (
                !imageJobDirection.serverReady
                || imageJobDirection.serverRevision < 1
                || imageJobDirection.serverConflict
              )) ||
              !imageJobDirection.value.trim()
            }
            onClick={() => void onPrepare()}
          >
            准备{imageJobTarget.kind === "keyframe_adaptation" ? "关键帧比例适配" : imageJobTarget.kind === "refinement" ? "参考细化" : "原始图片"}任务
          </Button>
        </div>
        {mediaKnown && shotId && scopedJobs.length < imageJobs.length && <Button variant="quiet" onClick={() => setShowProjectHistory(!showProjectHistory)}>
          {showProjectHistory ? "只看当前镜头请求" : `查看全项目请求历史（${imageJobs.length}）`}
        </Button>}
        <div className="image-job-history">
          {visibleJobs.map((job) => (
            <article
              key={job.id}
              className="image-job-card"
              data-testid={`image-job-${job.id}`}
            >
              <div>
                <strong>
                  {job.request.kind === "keyframe_adaptation" ? "关键帧比例适配" : job.request.kind === "refinement" ? "参考细化" : "原始图"} ·{" "}
                  {job.id.slice(0, 15)}
                </strong>{" "}
                <Badge tone={job.current ? "ok" : "warning"}>
                  {job.current ? imageJobStateLabel[job.state] : "不适用（历史）"}
                </Badge>
              </div>
              {showProjectHistory && <small>镜头：{job.request.frozenSnapshot?.shot?.id ?? "历史请求未记录镜头"}</small>}
              <small>
                冻结请求 {job.requestHash.slice(0, 12)} ·{" "}
                {job.deliveries.length
                  ? `${job.deliveries.length} 项交付记录`
                  : job.state === "exported"
                    ? "任务已导出，等待交付"
                    : "尚无交付记录"}
              </small>
              <div className="button-row">
                <Button
                  data-testid={`copy-image-job-${job.id}`}
                  variant="quiet"
                  disabled={
                    readOnly ||
                    busy ||
                    !mediaKnown ||
                    !job.current ||
                    job.state !== "prepared"
                  }
                  onClick={() => void onCopy(job.id)}
                >
                  发送给图像生成助手
                </Button>
                <Button
                  data-testid={`refresh-image-job-${job.id}`}
                  variant="quiet"
                  disabled={readOnly || busy}
                  onClick={() => void onRefresh(job.id)}
                >
                  立即检查交付
                </Button>
                <Button
                  variant="danger"
                  disabled={readOnly || busy || job.state === "cancelled"}
                  onClick={() => void onCancel(job.id)}
                >
                  取消
                </Button>
              </div>
              {imageJobNotice(job, imageJobRefreshNotice[job.id]) && (
                <small className="notice" role="status">
                  {imageJobNotice(job, imageJobRefreshNotice[job.id])}
                </small>
              )}
              {job.deliveries.map((delivery) => (
                <div className="image-job-delivery" key={delivery.id}>
                  <small>
                    {delivery.deliveryId ?? "未能核验交付标识"} ·{" "}
                    {deliveryStateLabel[delivery.state]}
                    {delivery.diagnosticCode
                      ? ` · ${delivery.diagnosticCode}`
                      : ""}
                  </small>
                  {delivery.candidates.map((candidate) => (
                    <div className="button-row" key={candidate.id}>
                      <small>
                        候选 {candidate.assetId.slice(0, 8)} · {candidateRoleLabel[candidate.role]}
                      </small>
                      <Button
                        data-testid={`prepare-refinement-${candidate.assetId}`}
                        variant="quiet"
                        disabled={
                          readOnly ||
                          busy ||
                          !job.current ||
                          selectedBinding?.assetId !== candidate.assetId
                        }
                        onClick={() =>
                          setImageJobTarget({
                            kind: "refinement",
                            parentCandidateAssetId: candidate.assetId,
                          })
                        }
                      >
                        选择此已审核候选作为细化目标
                      </Button>
                    </div>
                  ))}
                </div>
              ))}
            </article>
          ))}
          {mediaKnown && !visibleJobs.length && (
            <small>
              {shotId && !showProjectHistory ? "当前镜头尚无图片任务。" : "尚无图片任务。"}完成前置条件并准备后，可发送给指定的图像生成助手。
            </small>
          )}
        </div>
      </section>

  );
}
