import type { Dispatch, SetStateAction } from "react";
import type { ImageJob, ReviewedKeyframe } from "../../../types";
import { Badge, Button, Field } from "../../../components";
import {
  type ImageJobDraftTarget,
  useImageJobDirectionDraft,
} from "../../../visual-intent-drafts";

type ImageJobDirection = ReturnType<typeof useImageJobDirectionDraft>;
type DeliveryCandidate = ImageJob["deliveries"][number]["candidates"][number];

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
  imageJobRefreshNotice: Record<string, string>;
  selectedBinding: ReviewedKeyframe | undefined;
  onPrepare: () => void;
  onCopy: (jobId: string) => void;
  onRefresh: (jobId: string) => void;
  onCancel: (jobId: string) => void;
}) {
  return (
      <section className="image-job-panel" data-testid="image-job-panel">
        <div className="section-title">
          <span>Codex image jobs · P1.5</span>
          <strong>Prepare → Send → Generate → Auto-check → Select</strong>
        </div>
        {!imageExchangeConfigured && (
          <div className="notice warning">
            尚未配置同机 exchange root。设置{" "}
            <code>PLOTLOOM_IMAGE_EXCHANGE_ROOT</code> 后重启服务；不会回退到外部
            API。
          </div>
        )}
        <p className="muted">
          当前 storyboard Approval 冻结单镜头请求和角色映射后，专用同机 specialist
          接收不可变 package；delivery 会自动检查并只在通过既有验证后显示为候选。队列接受不代表生成、delivery、Approval 或选择。H3/Qwen 不参与此流程。
        </p>
        {imageJobPrerequisite && (
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
        <Field label={imageJobTarget.kind === "keyframe_adaptation" ? "冻结的画面呈现 / 比例适配方向" : "冻结的画面呈现 / 细化变化"}>
          <textarea
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
            Approval、分镜或参考上下文。文本已保留但不会自动提交。
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
              方向草稿会以当前分镜 revision 与目标上下文作 CAS 保存到项目；切换镜头、目标或刷新后可按其原始上下文恢复。
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
            准备{imageJobTarget.kind === "keyframe_adaptation" ? "关键帧比例适配" : imageJobTarget.kind === "refinement" ? "参考细化" : "原始"}{" "}
            image job
          </Button>
        </div>
        <div className="image-job-history">
          {imageJobs.map((job) => (
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
                  {job.current ? job.state.toUpperCase() : "INAPPLICABLE"}
                </Badge>
              </div>
              <small>
                冻结请求 {job.requestHash.slice(0, 12)} ·{" "}
                {job.deliveries.length
                  ? `${job.deliveries.length} delivery receipt`
                  : job.state === "exported"
                    ? "已导出，等待 delivery"
                    : "尚未导出 assignment"}
              </small>
              <div className="button-row">
                <Button
                  data-testid={`copy-image-job-${job.id}`}
                  variant="quiet"
                  disabled={
                    readOnly ||
                    busy ||
                    !job.current ||
                    job.state === "cancelled"
                  }
                  onClick={() => void onCopy(job.id)}
                >
                  发送给 specialist
                </Button>
                <Button
                  data-testid={`refresh-image-job-${job.id}`}
                  variant="quiet"
                  disabled={readOnly || busy}
                  onClick={() => void onRefresh(job.id)}
                >
                  立即检查 delivery
                </Button>
                <Button
                  variant="danger"
                  disabled={readOnly || busy || job.state === "cancelled"}
                  onClick={() => void onCancel(job.id)}
                >
                  取消
                </Button>
              </div>
              {imageJobRefreshNotice[job.id] && (
                <small className="notice" role="status">
                  {imageJobRefreshNotice[job.id]}
                </small>
              )}
              {job.deliveries.map((delivery) => (
                <div className="image-job-delivery" key={delivery.id}>
                  <small>
                    {delivery.deliveryId ?? "rejected before identity"} ·{" "}
                    {delivery.state}
                    {delivery.diagnosticCode
                      ? ` · ${delivery.diagnosticCode}`
                      : ""}
                  </small>
                  {delivery.candidates.map((candidate) => (
                    <div className="button-row" key={candidate.id}>
                      <small>
                        候选 {candidate.assetId.slice(0, 8)} · {candidate.role}
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
          {!imageJobs.length && (
            <small>
              尚无 P1 job。完成前置条件并准备后，可复制 assignment 给指定的
              Codex specialist。
            </small>
          )}
        </div>
      </section>

  );
}
