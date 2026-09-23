import { useEffect, useState } from "react";
import { plotloomApi } from "../../api";
import { Button } from "../../components";
import { currentBridgeCut } from "../../production-bridge-handoff";
import type { ProductionBridgeState, Shot, StoryboardReview, VideoBackend, VisualWorkbench } from "../../types";
import type { MediaReadPhase } from "./useMediaWorkbenchData";

interface ReadonlySources {
  projectId: string;
  storyboardRevision?: number;
  retryEpoch: number;
  bridge?: ProductionBridgeState;
  backend?: VideoBackend;
  bridgeError?: string;
  backendError?: string;
}

function ownerAction(id: string) {
  document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" });
}

/** Explain existing owner state only; this view never approves or prepares media. */
export function ShotPreparationSummary({
  projectId, shot, storyboardRevision, draftChanged, review, workbench, mediaReadPhase,
  onRetryMedia, onReview, onReturnToBridge,
}: {
  projectId?: string;
  shot: Shot;
  storyboardRevision?: number;
  draftChanged: boolean;
  review: StoryboardReview | null | undefined;
  workbench: VisualWorkbench;
  mediaReadPhase: MediaReadPhase;
  onRetryMedia?: () => void;
  onReview?: () => void;
  onReturnToBridge?: () => void;
}) {
  const [sources, setSources] = useState<ReadonlySources>();
  const [retryEpoch, setRetryEpoch] = useState(0);
  useEffect(() => {
    if (!projectId) return;
    const controller = new AbortController();
    setSources(undefined);
    void Promise.allSettled([
      plotloomApi.getProductionBridge(projectId, controller.signal),
      plotloomApi.getVideoBackend(controller.signal),
    ]).then(([bridge, backend]) => {
      if (controller.signal.aborted) return;
      setSources({
        projectId,
        storyboardRevision,
        retryEpoch,
        bridge: bridge.status === "fulfilled" ? bridge.value : undefined,
        backend: backend.status === "fulfilled" ? backend.value : undefined,
        bridgeError: bridge.status === "rejected" ? "投产来源暂不可读取" : undefined,
        backendError: backend.status === "rejected" ? "视频能力暂不可读取" : undefined,
      });
    });
    return () => controller.abort();
  }, [projectId, storyboardRevision, retryEpoch]);

  const current = sources && sources.projectId === projectId && sources.storyboardRevision === storyboardRevision && sources.retryEpoch === retryEpoch ? sources : undefined;
  const cut = currentBridgeCut(current?.bridge, storyboardRevision, shot.id);
  const sourceMatches = Boolean(cut && shot.durationUnits === cut.seconds * 1000 && !draftChanged);
  const approvalCurrent = Boolean(
    !draftChanged && review?.activeApproval && review.head.status === "ready" &&
    review.head.revision === storyboardRevision &&
    review.activeApproval.subjectRevision === storyboardRevision,
  );
  const selectedKeyframe = mediaReadPhase === "ready" && approvalCurrent
    ? workbench.reviewedKeyframes.find((item) => item.shotId === shot.id && workbench.assets.some((asset) => asset.id === item.assetId))
    : undefined;
  const referenceStatus = shot.characterIds.map((characterId) => {
    const state = workbench.characterReferences.states.find((item) => item.characterId === characterId);
    const decision = workbench.characterReferences.decisions.find((item) => item.id === state?.activeDecisionId);
    return { characterId, status: state?.current && decision?.current ? "已选择当前参考" : state || decision ? "参考已过期或撤销" : "缺少身份参考" };
  });
  const qualified = current?.backend?.qualifiedDurationSeconds;
  const exactSeconds = cut?.seconds ?? shot.durationUnits / 1000;
  const segmentEligible = exactSeconds === 6 && qualified?.includes(8);
  const durationStatus = !qualified ? "未知"
    : segmentEligible
      ? `6 秒不在原片请求目录（${qualified.join(" / ")} 秒）；若来源绑定、批准及关键帧均为当前，可请求 8 秒原片后准备连续 144 帧候选播放片段。原片输出须核验，片段须经人工听看并明确选择；${current?.backend?.enabled ? "当前后端已配置" : "当前后端未配置，暂不能提交请求"}`
      : qualified.includes(exactSeconds)
        ? `${exactSeconds} 秒在当前请求目录内；不代表生成输出物理时长或媒体可用`
        : `${exactSeconds} 秒不在当前请求目录（${qualified.join(" / ")} 秒）；不能通过选择其他时长绕过精确来源约束`;

  return <section className="notice shot-preparation-summary" data-testid="shot-preparation-summary" aria-label="当前镜头准备状态">
    <strong>当前镜头准备状态 · {shot.id}</strong>
    {!current && <p>正在读取投产来源与视频能力；暂不判定准备状态。</p>}
    {current?.bridgeError && <p>{current.bridgeError}；来源绑定未知。</p>}
    {current?.backendError && <p>{current.backendError}；时长兼容性未知。</p>}
    {(current?.bridgeError || current?.backendError) && <Button variant="quiet" onClick={() => setRetryEpoch((value) => value + 1)}>重试来源与视频能力读取</Button>}
    {mediaReadPhase === "error" && <p className="warning">媒体证据读取失败；当前角色参考与关键帧状态未知。<Button variant="quiet" onClick={onRetryMedia}>重试媒体读取</Button></p>}
    {current?.bridge && (!cut || !sourceMatches) && <p className="warning" data-testid="bridge-source-unavailable">
      {current.bridge.status === "stale" ? "投产提案已过期；此镜头不具有当前投产来源绑定。"
        : cut ? "镜头时长或未保存编辑与已安装 F5 来源不一致；先审阅并保存当前合同，不能将其视为来源匹配。"
          : "当前镜头不属于此已确认投产提案，或分镜版本已变化；来源坐标不适用。"}
    </p>}
    {cut && <p>F5 来源：{cut.sectionId} / 第 {cut.episode} 集 / 场次 {cut.sceneIndex} / 段 {cut.segmentIndex} / 段内场次 {cut.segmentSceneIndex} / cut {cut.sourceCutIndex}；精确来源时长 {cut.seconds} 秒{sourceMatches ? " · 当前绑定" : " · 绑定未确认"}。</p>}
    <ul>
      <li>分镜批准：{approvalCurrent ? `当前批准 ${review!.activeApproval!.id.slice(0, 8)}` : review?.decisions.length ? "无当前批准（历史决定不适用）" : "缺少当前批准"}。<Button variant="quiet" onClick={onReview}>前往分镜审核</Button></li>
      <li>角色身份参考：{mediaReadPhase === "loading" ? "正在读取" : mediaReadPhase === "error" ? "未知（读取失败）" : referenceStatus.length ? referenceStatus.map((item) => `${item.characterId} ${item.status}`).join("；") : "此镜头无可见角色，不适用"}。{referenceStatus.length > 0 && <Button variant="quiet" onClick={() => ownerAction("shot-character-references")}>查看身份参考</Button>}</li>
      <li>美术参考：F3 场景/道具选择由美术参考工作区持有；当前镜头媒体准备未消费这些决定，不计为已选关键帧。</li>
      <li>审核关键帧：{mediaReadPhase === "loading" ? "正在读取" : mediaReadPhase === "error" ? "未知（读取失败）" : selectedKeyframe ? `当前选择 ${selectedKeyframe.assetId.slice(0, 8)}` : approvalCurrent ? "缺少当前审核关键帧" : "无当前批准，关键帧不可用"}。<Button variant="quiet" onClick={() => ownerAction("shot-keyframe-review")}>查看关键帧</Button></li>
      <li>视频后端：{!current?.backend ? "未知" : current.backend.enabled ? "已配置" : "未配置；不能准备或提交视频"}。</li>
      <li data-testid="shot-duration-compatibility">时长目录：{durationStatus}。</li>
    </ul>
    {onReturnToBridge && <Button variant="quiet" onClick={onReturnToBridge}>返回分镜评审</Button>}
    <small>此摘要只解释现有合同和当前证据；不是投产许可、媒体质量审核或可播放证明。</small>
  </section>;
}
