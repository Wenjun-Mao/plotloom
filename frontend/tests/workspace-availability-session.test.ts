import {act, createElement} from "react";
import {createRoot, type Root} from "react-dom/client";
import {afterEach, beforeEach, expect, it} from "vitest";
import {demoProject} from "../src/demo";
import {blankWorkspace, type ProjectLoadFailure} from "../src/app/workspace/contracts";
import {useWorkspaceSession, type WorkspaceProjectLoad, type WorkspaceSession} from "../src/app/workspace/useWorkspaceSession";

(globalThis as typeof globalThis & {IS_REACT_ACT_ENVIRONMENT: boolean}).IS_REACT_ACT_ENVIRONMENT = true;
let root: Root;
let session: WorkspaceSession;
const failure: ProjectLoadFailure = {projectId: "a", kind: "closed", diagnostic: "closed evidence"};
const incoming = (id = "a"): WorkspaceProjectLoad => ({
  project: {id, revision: 3, brief: demoProject.brief, lifecycleRevision: 2, lifecycleStatus: "active", archivedAt: null,
    createdAt: "2026-10-08", updatedAt: "2026-10-08"},
  stages: [], run: undefined, progress: undefined, review: null, media: [], drafts: [],
});
beforeEach(async () => {
  window.history.replaceState(null, "", "/?project=a&stage=storyboard&entity=shot%3Aone#shot-workbench");
  document.body.innerHTML = '<div id="test-root"></div>';
  root = createRoot(document.getElementById("test-root")!);
  function Harness() {session = useWorkspaceSession(); return null;}
  await act(async () => root.render(createElement(Harness)));
});
afterEach(async () => {await act(async () => root.unmount()); window.sessionStorage.clear();});

it("keeps a failed initial route as unavailable, not an accepted blank project", async () => {
  expect(session.connection).toBe("loading");
  await act(async () => session.rejectProjectLoad(undefined, failure));
  expect(session.project.id).toBeUndefined();
  expect(session.connection).toBe("error");
  expect(session.loadFailure).toEqual(failure);
  expect(session.route).toMatchObject({project: "a", stage: "storyboard", entity: "shot:one", hash: "shot-workbench"});
});

it("never presents accepted A as failed destination B", async () => {
  await act(async () => session.acceptProjectLoad(incoming()));
  await act(async () => session.navigateToProject({...session.route, project: "b"}, "push"));
  await act(async () => session.beginProjectLoad());
  await act(async () => session.rejectProjectLoad(undefined, {...failure, projectId: "b"}));
  expect(session.project.id).toBeUndefined();
  expect(session.route.project).toBe("b");
  expect(session.loadFailure?.projectId).toBe("b");
});

it("retains accepted matching payload references during pending and failed refresh", async () => {
  await act(async () => session.acceptProjectLoad(incoming()));
  const project = session.project, heads = session.stageHeads, media = session.mediaTasks, review = session.review;
  await act(async () => session.beginProjectLoad());
  expect(session.project).toBe(project);
  await act(async () => session.rejectProjectLoad(undefined, failure));
  expect(session.project).toBe(project);
  expect(session.stageHeads).toBe(heads);
  expect(session.mediaTasks).toBe(media);
  expect(session.review).toBe(review);
  expect(session.needsCanonicalRefresh("a")).toBe(true);
  expect(session.connection).toBe("error");
  await act(async () => session.beginProjectLoad());
  expect(session.loadFailure).toBeUndefined();
  await act(async () => {session.acceptProjectLoad(incoming()); session.clearCanonicalRefresh("a");});
  expect(session.loadFailure).toBeUndefined();
  expect(session.connection).toBe("connected");
  expect(session.needsCanonicalRefresh("a")).toBe(false);
});

it("clears availability when starting a genuine unsaved local workspace", async () => {
  await act(async () => session.rejectProjectLoad(undefined, failure));
  await act(async () => session.startLocalWorkspace({project: "", stage: "brief", entity: "", run: "", hash: ""},
    {project: blankWorkspace(), connection: "blank", onboarding: false}));
  expect(session.loadFailure).toBeUndefined();
  expect(session.connection).toBe("blank");
  expect(session.route.project).toBe("");
  expect(session.project.id).toBeUndefined();
});
