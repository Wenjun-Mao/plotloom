// Disposable browser owner. Every command is recorded locally; no dispatch.
import { createRoot } from "react-dom/client";
import { AutopilotWorkspace, AutopilotLaunch, AutopilotProgress } from "../src/features/autopilot/AutopilotWorkspace";
import { autopilotApi } from "../src/features/autopilot/api";
import { specialistsApi } from "../src/features/specialists/api";
import { fixtureMaterial, fixtureRun } from "../tests/autopilot-fixture";
import type { Handoff } from "../src/features/autopilot/contracts";
import { plotloomApi } from "../src/api";
import { evidenceReadsFixture, geometryReadsFixture } from "../tests/autopilot-delivery-fixture";
import "../src/styles.css";
const initial = new URLSearchParams(location.search).get("state");
const localGeometry = geometryReadsFixture();
const evidence = initial === "geometry" ? localGeometry.reads : evidenceReadsFixture();
let evidenceFailed = false;
plotloomApi.getManagedAssets = async () => {
  if (initial === "evidence-failure" && !evidenceFailed) { evidenceFailed = true; throw new Error("Disposable evidence read failure"); }
  return { assets: evidence.assets };
};
plotloomApi.getCharacterReferenceProposals = async () => ({ configured: true, proposals: evidence.characters });
plotloomApi.getArtReferenceProposals = async () => ({ configured: true, proposals: evidence.art });
plotloomApi.getImageJobs = async () => ({ configured: true, jobs: evidence.images });
const longBlocker = "The saved project contains a retained manual edit that no longer matches the frozen source and briefing context. Review the accepted source, story outline, route map, character descriptions, art direction, and the active workflow revision before continuing. No automatic preparation can proceed until the complete currentness chain has been checked.";
let current = initial?.startsWith("fresh") ? null : initial === "blocked-long"
  ? { ...fixtureRun, state: "blocked" as const, blocker: { code: "source_context_changed", message: longBlocker } }
  : { ...fixtureRun, state: initial?.startsWith("running") ? "running" as const : fixtureRun.state };
let progressReads = 0;
let handoffReadFailed = false;
const writes: unknown[] = [];
function record(value: unknown) { writes.push(value); document.getElementById("fixture-writes")!.textContent = JSON.stringify(writes); }
autopilotApi.current = async () => {
  if (initial === "handoff-uncommitted" && writes.length && !handoffReadFailed) {
    handoffReadFailed = true; throw new Error("Disposable reconciliation read failure");
  }
  if (initial === "fresh-progress" && current?.state === "running") {
    progressReads += 1;
    current = progressReads >= 3 ? { ...fixtureRun, revision: 15 } : { ...fixtureRun, state: "running", phase: progressReads === 1 ? "outline" : "references", revision: 12 + progressReads };
  }
  if (initial === "running-retry") {
    progressReads += 1;
    if (progressReads === 2) throw new Error("Disposable transient read failure");
    if (progressReads >= 3) current = fixtureRun;
  }
  return current;
};
autopilotApi.launchContext = async () => ({ eligible: current === null, briefRevision: 1 });
autopilotApi.review = async () => {
  const result = { ...structuredClone(fixtureMaterial), runRevision: current?.revision ?? fixtureMaterial.runRevision };
  if (initial === "geometry") result.bundle.frames[0].geometryPreparation = localGeometry.geometry;
  return result;
};
autopilotApi.start = async (_id, body) => { record(["start", body]); current = { ...fixtureRun, state: "running" }; return current; };
autopilotApi.control = async (_id, _revision, action) => { record(["control", action]); current = { ...fixtureRun, state: action === "pause" ? "paused" : action === "resume" ? "running" : action === "cancel" ? "cancelled" : "taken_over" }; return current; };
autopilotApi.handoff = async (_id, body: Handoff) => { record(["handoff", body]);
  if (initial === "handoff-uncommitted") throw new Error("Disposable handoff not committed");
  current = { ...fixtureRun, state: "handed_off", handoff: { receiptId: "human-fixture" } };
  if (initial === "handoff-unknown") throw new Error("Disposable handoff acknowledgment lost");
  return current; };
specialistsApi.settings = async () => ({ text: { name: "文字测试助手", taskId: "text-fixture" }, image: { name: "图片测试助手", taskId: "image-fixture" }, busy: false });
createRoot(document.getElementById("root")!).render(<main><h1>灯塔素材准备 · 一次审阅</h1><p>Disposable fixture · no generation or creative acceptance.</p><pre id="fixture-writes">[]</pre>
  <AutopilotWorkspace projectId="disposable" revision={1} readOnly={false} onChanged={async () => undefined} onVideo={() => record(["manual-video-navigation"])}>
    <section className="recommended-workflow-guide" aria-label="自动素材进度"><AutopilotProgress /></section>
    <AutopilotLaunch saved dirty={false} disabled={false} visualDirection="2D 动画；水彩；低饱和" /><p>故事的全部路线与镜头在这里汇成可审阅的素材包。</p>
  </AutopilotWorkspace>
</main>);
