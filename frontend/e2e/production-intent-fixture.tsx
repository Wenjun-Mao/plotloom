import { createRoot } from "react-dom/client";
import { H3DirectionsReview } from "../src/h3-directions-review";
import { VideoBatchPanel } from "../src/features/video-batch/VideoBatchPanel";
import type { VideoJobPrepareBody } from "../src/api";
import "../src/styles.css";
import "../src/features/video-batch/video-batch.css";
const single = new URLSearchParams(location.search).get("single") === "1";
const buildRequest = (seed: number, idempotencyKey: string): VideoJobPrepareBody => ({ approvalId: "approval", shotId: "shot", storyboardRevision: 1,
  expectedSelectionRevision: 1, seed, idempotencyKey, profileId: "h3_vertical_8", aspectPolicy: "reject_mismatch", requestedDurationSeconds: 15,
  resolution: "576x1024", audio: true, playbackIntent: "segment_required" });
createRoot(document.getElementById("root")!).render(<main style={{ maxWidth: 1100, margin: "auto", padding: 24 }}>
  <h1>制作意图授权测试</h1><p>仅使用合成 HTTP 数据；没有实际助手检查或视频生成。</p>
  {single ? <H3DirectionsReview projectId="project" shotId="shot" sourceIdentity="browser-single" sourceReady disabled={false} buildRequest={buildRequest}
    keyframeHash={"a".repeat(64)} quality={8} requestedSeconds={15} frameCount={362}
    onFreeze={async (value, seed, key) => { (window as unknown as { frozen: unknown }).frozen = { value, seed, key }; }} />
    : <VideoBatchPanel projectId="project" disabled={false} dirty={false} />}
</main>);
