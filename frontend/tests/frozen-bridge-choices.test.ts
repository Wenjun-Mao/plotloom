import { act, createElement } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { BranchingVideoPreview } from "../src/branching-video-preview";
import { plotloomApi } from "../src/api";
import { selectedBridgeChoicesEligible } from "../src/features/media/selected-bridge-choice";
import type { RuntimeChoice, VideoJob } from "../src/types";
import { branchingFixture } from "./video-pilot-fixtures";
import { bindBridgePlayback } from "./bridge-playback-fixtures";
import { bridgeState } from "./production-bridge-fixture";

(globalThis as typeof globalThis & { IS_REACT_ACT_ENVIRONMENT: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
let host: HTMLDivElement; let root: Root;
beforeEach(() => {
  host = document.createElement("div"); document.body.append(host); root = createRoot(host);
  vi.spyOn(HTMLMediaElement.prototype,"pause").mockImplementation(() => undefined);
  vi.spyOn(HTMLMediaElement.prototype,"play").mockResolvedValue(undefined);
});
afterEach(async () => { await act(async () => root.unmount()); host.remove(); vi.restoreAllMocks(); });

function frozenStory() {
  const fixture = branchingFixture();
  // Smallest filmed story: one opening choice and two ending clips.
  fixture.graph.startNodeId = "decision";
  fixture.graph.nodes = fixture.graph.nodes.filter(node=>node.id!=="scene");
  fixture.graph.nodes.find(node=>node.id==="decision")!.kind="start";
  fixture.graph.edges = fixture.graph.edges.filter(edge=>edge.sourceNodeId!=="scene");
  fixture.sceneBeats.scenes = fixture.sceneBeats.scenes.filter(scene=>scene.storyNodeId!=="scene");
  fixture.storyboard.shots = fixture.storyboard.shots.filter(shot=>shot.sceneId!=="scene-scene");
  fixture.selected = fixture.selected.filter(job=>job.id!=="scene-job");
  const choice: RuntimeChoice = { choiceId:"choice-1",sectionId:"decision",prompt:"今晚要去赴约吗？",outcomes:[
    {outcomeId:"edge-2",endingSectionId:"left",label:"留下",consequence:"留在家中。"},
    {outcomeId:"edge-3",endingSectionId:"right",label:"赴约",consequence:"走向约定地点。"},
  ] };
  fixture.graph.edges.filter(edge => edge.kind === "choice").forEach(edge => {
    edge.choiceText = choice.outcomes.find(outcome => outcome.outcomeId === edge.id)!.label;
  });
  const media = bindBridgePlayback(fixture.selected.map(job => ({...job,current:false,inputStatus:"stale"})),fixture.sceneBeats.scenes,[choice]);
  media.installation.status = "outdated";
  media.installation.staleReasons = ["accepted F5 receiving policy changed"];
  return {...fixture,...media,choice};
}
const show = (fixture: ReturnType<typeof frozenStory>) => act(async () => root.render(createElement(BranchingVideoPreview,{
  projectId:"project",jobs:fixture.jobs,graph:fixture.graph,storyboard:fixture.storyboard,sceneBeats:fixture.sceneBeats,
})));
async function finish(id: string) {
  const player = host.querySelector(`[data-testid="branching-video-job-${id}"]`);
  expect(player).not.toBeNull();
  await act(async () => { player!.dispatchEvent(new Event("ended",{bubbles:true})); await Promise.resolve(); });
}
function choiceButtons() { return [...host.querySelectorAll<HTMLButtonElement>('[data-testid="branching-choices"] button')]; }

it.each(["outdated","current"] as const)("plays the actual F5 hook journey with %s generation installation", async status => {
  const fixture = frozenStory();
  fixture.installation.status = status;
  if(status === "current") fixture.installation.staleReasons=[];
  const before = JSON.stringify(fixture.installation);
  const bridge = vi.spyOn(plotloomApi,"getProductionBridge").mockResolvedValue(bridgeState({status:"stale",installation:fixture.installation}));
  const media = vi.spyOn(plotloomApi,"getVideoJobs").mockResolvedValue({jobs:fixture.jobs});
  await show(fixture);
  expect(bridge).toHaveBeenCalled(); expect(media).toHaveBeenCalled();
  expect(choiceButtons()).toEqual([]);
  expect(host.querySelector('[data-testid="branching-video-job-decision-job"]')).not.toBeNull();
  expect(choiceButtons()).toEqual([]);
  await finish("decision-job");
  expect(host.querySelector('[data-testid="branching-choice-question"]')?.textContent).toBe(fixture.choice.prompt);
  expect(choiceButtons().map(button=>button.textContent)).toEqual(["留下","赴约"]);
  await act(async () => { choiceButtons().find(button=>button.textContent==="赴约")!.click(); await Promise.resolve(); });
  expect(host.querySelector('[data-testid="branching-video-job-right-job"]')?.getAttribute("src")).toBe(plotloomApi.selectedVideoPlaybackUrl("project","right-job"));
  expect(host.querySelector('[data-testid="branching-video-job-left-job"]')).toBeNull();
  expect(host.textContent).toContain("选择历史：赴约");
  expect(JSON.stringify(fixture.installation)).toBe(before);
  expect(fixture.jobs.every(job=>!job.current && job.inputStatus==="stale")).toBe(true);
});

it.each(["source","approval","selection"])("withdraws choices and ending playback after fresh %s withdrawal", async _reason => {
  const fixture = frozenStory(); let fresh: VideoJob[] = fixture.jobs;
  vi.spyOn(plotloomApi,"getProductionBridge").mockResolvedValue(bridgeState({status:"stale",installation:fixture.installation}));
  vi.spyOn(plotloomApi,"getVideoJobs").mockImplementation(async () => ({jobs:fresh}));
  await show(fixture); await finish("decision-job");
  expect(choiceButtons()).toHaveLength(2);
  // The backend withdraws these same selected/segment flags for actual source,
  // approval or selection changes. The displayed snapshot may still be cached.
  fresh = fixture.jobs.map(job=>({...job,selected:false,playbackSegment:null}));
  await act(async () => { choiceButtons()[1].click(); await Promise.resolve(); });
  expect(host.querySelector("video")).toBeNull();
  expect(choiceButtons()).toEqual([]);
  expect(host.textContent).toContain("不一致");
});

it.each(["project","admission","revision","proposalHash","canonicalRevision","cut","scene","duration","segment","selectionRevision","graph"])(
  "refuses mismatched %s identity before mounting playback or choices", async defect => {
    const fixture = frozenStory(); const installation = structuredClone(fixture.installation);
    const fresh: VideoJob[] = structuredClone(fixture.jobs);
    if(defect==="project") fresh[0].projectId="another-story";
    if(defect==="admission") installation.admissionId="another-admission";
    if(defect==="revision") installation.proposalRevision+=1;
    if(defect==="proposalHash") installation.proposalContentHash="e".repeat(64);
    if(defect==="canonicalRevision") installation.installedStageRevisions.story_graph+=1;
    if(defect==="cut") installation.cuts[0].composition="Another source composition";
    if(defect==="scene") installation.scenes[0].sceneId="another-scene";
    if(defect==="duration") fresh[0].playbackSegment!.authoredDurationUnits=5000;
    if(defect==="segment") fresh[0].playbackSegment!.id="another-segment";
    if(defect==="selectionRevision") fresh[0].selectionRevision+=1;
    if(defect==="graph") fixture.graph.edges.find(edge=>edge.kind==="choice")!.choiceText="Another option";
    vi.spyOn(plotloomApi,"getProductionBridge").mockResolvedValue(bridgeState({installation}));
    vi.spyOn(plotloomApi,"getVideoJobs").mockResolvedValue({jobs:fresh});
    await show(fixture);
    expect(host.querySelector("video")).toBeNull(); expect(choiceButtons()).toEqual([]);
    expect(host.textContent).toContain("不一致");
  },
);

it("cannot use one selected clip to admit another installation's full choice set", () => {
  const fixture = frozenStory();
  expect(selectedBridgeChoicesEligible("project",fixture.installation,[fixture.jobs[0]],fixture.jobs)).toBe(false);
  expect(selectedBridgeChoicesEligible("another-story",fixture.installation,fixture.jobs,fixture.jobs)).toBe(false);
});

it("waits for fresh selected-segment verification even when ordinary installation is current", async () => {
  const fixture = frozenStory(); fixture.installation.status="current";fixture.installation.staleReasons=[];
  vi.spyOn(plotloomApi,"getProductionBridge").mockResolvedValue(bridgeState({installation:fixture.installation}));
  let release!: (value:{jobs:VideoJob[]})=>void;
  vi.spyOn(plotloomApi,"getVideoJobs").mockReturnValue(new Promise(resolve=>{release=resolve;}));
  await show(fixture);
  expect(host.querySelector("video")).toBeNull();expect(choiceButtons()).toEqual([]);
  await act(async () => release({jobs:fixture.jobs}));
  expect(host.querySelector('[data-testid="branching-video-job-decision-job"]')).not.toBeNull();
});

it("reads selected authority after installation metadata, closing a withdrawal during that read", async () => {
  const fixture = frozenStory();
  let release!: (value: ReturnType<typeof bridgeState>)=>void;
  vi.spyOn(plotloomApi,"getProductionBridge").mockReturnValue(new Promise(resolve=>{release=resolve;}));
  const media = vi.spyOn(plotloomApi,"getVideoJobs").mockResolvedValue({jobs:fixture.jobs.map(job=>({...job,selected:false,playbackSegment:null}))});
  await show(fixture);
  expect(media).not.toHaveBeenCalled();
  expect(host.querySelector("video")).toBeNull();
  await act(async () => release(bridgeState({installation:fixture.installation})));
  expect(media).toHaveBeenCalledTimes(1);
  expect(host.querySelector("video")).toBeNull();expect(choiceButtons()).toEqual([]);
});
