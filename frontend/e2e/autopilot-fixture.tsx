// Disposable browser owner. Every command is recorded locally; no dispatch.
import { createRoot } from "react-dom/client";
import { AutopilotWorkspace, AutopilotLaunch } from "../src/features/autopilot/AutopilotWorkspace";
import { autopilotApi } from "../src/features/autopilot/api";
import { specialistsApi } from "../src/features/specialists/api";
import { fixtureMaterial, fixtureRun } from "../tests/autopilot-fixture";
import type { Handoff } from "../src/features/autopilot/contracts";
import "../src/styles.css";
const initial = new URLSearchParams(location.search).get("state");
let current = initial === "fresh" ? null : { ...fixtureRun, state: initial === "running" ? "running" as const : fixtureRun.state };
const writes: unknown[] = [];
function record(value: unknown) { writes.push(value); document.getElementById("fixture-writes")!.textContent = JSON.stringify(writes); }
autopilotApi.current = async () => current;
autopilotApi.launchContext = async () => ({ eligible: current === null, briefRevision: 1 });
autopilotApi.review = async () => structuredClone(fixtureMaterial);
autopilotApi.start = async (_id, body) => { record(["start", body]); current = { ...fixtureRun, state: "running" }; return current; };
autopilotApi.control = async (_id, _revision, action) => { record(["control", action]); current = { ...fixtureRun, state: action === "pause" ? "paused" : action === "resume" ? "running" : action === "cancel" ? "cancelled" : "taken_over" }; return current; };
autopilotApi.handoff = async (_id, body: Handoff) => { record(["handoff", body]); current = { ...fixtureRun, state: "handed_off", handoff: { receiptId: "human-fixture" } }; return current; };
specialistsApi.settings = async () => ({ text: { name: "文字测试助手", taskId: "text-fixture" }, image: { name: "图片测试助手", taskId: "image-fixture" }, busy: false });
createRoot(document.getElementById("root")!).render(<main><h1>灯塔素材准备 · 一次审阅</h1><p>Disposable fixture · no generation or creative acceptance.</p><pre id="fixture-writes">[]</pre>
  <AutopilotWorkspace projectId="disposable" revision={1} readOnly={false} onChanged={async () => undefined} onVideo={() => record(["manual-video-navigation"])}>
    <AutopilotLaunch saved dirty={false} disabled={false} /><p>故事的全部路线与镜头在这里汇成可审阅的素材包。</p>
  </AutopilotWorkspace>
</main>);
