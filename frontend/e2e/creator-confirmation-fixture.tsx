// Test-only entrypoint: synthetic actions, no provider or retained project writes.
import { useState } from "react";
import { createRoot } from "react-dom/client";
import { plotloomApi } from "../src/api";
import { demoProject } from "../src/demo";
import { VideoSegmentReview } from "../src/video-segment-review";
import { VideoPilotPanel } from "../src/video-pilot";
import { StoryboardPage } from "../src/pages/StoryboardPage";
import type { VideoJob } from "../src/types";
import "../src/styles.css";

const candidate = (id: string): VideoJob => ({
  id, projectId: "disposable", state: "ingested", lifecycleStatus: "active", inputStatus: "current", current: true, selected: false, selectionRevision: 7,
  requestedSeconds: 5, cancelRequestedAt: null, providerPredictionId: null, outputHash: "fixture", observed: null, error: null, reviews: [], segments: [],
  snapshot: { shot: { id: "shot_01", title: "Disposable test original", sceneId: demoProject.storyboard.shots[0].sceneId } },
});
let candidates = [candidate("disposable-one"), candidate("disposable-two")];
const writes: unknown[] = [];
function record(value: unknown) { writes.push(value); document.getElementById("fixture-writes")!.textContent = JSON.stringify(writes); }
plotloomApi.getVideoPilotBudget = async () => ({ limitSeconds: 0, reservedSeconds: 0, remainingSeconds: 0, attempts: [] });
plotloomApi.getVideoBackend = async () => ({ enabled: false });
plotloomApi.getVideoJobs = async () => ({ jobs: candidates });
plotloomApi.getVideoEndFrame = async () => ({ revision: 0, assetId: null });
plotloomApi.getManagedAssets = async () => ({ assets: [] });
plotloomApi.reviewVideoJob = async (...args) => { record(["reject", ...args]); return {} as never; };
plotloomApi.discardVideoJob = async (...args) => { record(["single", ...args]); candidates = candidates.filter(job => job.id !== args[1]); return {} as never; };
plotloomApi.discardUnselectedVideoJobs = async (...args) => { record(["bulk", ...args]); candidates = candidates.filter(job => !args[2].includes(job.id)); return {} as never; };

function Fixture() {
  const [revision, setRevision] = useState(7);
  return <main><h1>Disposable creator confirmation fixture</h1><p>Test-only synthetic media/actions. No provider calls, persistent writes or creative acceptance.</p>
    <pre id="fixture-writes">[]</pre><button onClick={() => setRevision(value => value + 1)}>Invalidate fixture revision</button>
    <section aria-label="Rejection fixture"><VideoSegmentReview projectId="disposable" job={{ ...candidate("disposable-reject"), selectionRevision: revision }} readOnly={false} onRefresh={async () => undefined} /></section>
    <section aria-label="Deletion fixture"><VideoPilotPanel projectId="disposable" shot={demoProject.storyboard.shots[0]} selectionRevision={revision} mediaReadPhase="ready" readOnly={false}
      storyboard={demoProject.storyboard} sceneBeats={demoProject.sceneBeats} graph={demoProject.storyGraph} /></section>
    <section aria-label="Coverage fixture"><StoryboardPage bible={demoProject.storyBible} graph={demoProject.storyGraph} sceneBeats={demoProject.sceneBeats}
      value={demoProject.storyboard} stale={false} mediaTasks={{}} saving={false} readOnly={false} entityId={`shot:${demoProject.storyboard.shots[0].id}`} onSave={async () => undefined}
      onDraftChange={draft => { if (draft.shotBeatLinks.length !== demoProject.storyboard.shotBeatLinks.length) record(["coverage", draft.shotBeatLinks]); }} /></section>
  </main>;
}
createRoot(document.getElementById("root")!).render(<Fixture />);
