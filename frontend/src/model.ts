import type { RunExecutionTrace, RunTrace, SceneBeatPlan, ServerStageName, StoryGraph, Storyboard, TraceEvent, WorkspaceProject } from "./types";

export const serverStages: ServerStageName[] = ["story_bible", "story_graph", "scene_beats", "storyboard"];

export function toggleContiguousStageRange(
  current: ServerStageName[],
  toggled: ServerStageName,
): ServerStageName[] {
  const selected = serverStages.filter((stage) => current.includes(stage));
  if (selected.includes(toggled)) {
    const toggledIndex = selected.indexOf(toggled);
    // Removing an interior stage truncates the range at that dependency;
    // removing the first stage advances the range start.
    return toggledIndex === 0 ? selected.slice(1) : selected.slice(0, toggledIndex);
  }
  const indexes = [...selected, toggled].map((stage) => serverStages.indexOf(stage));
  const start = Math.min(...indexes);
  const end = Math.max(...indexes);
  return serverStages.slice(start, end + 1);
}

export function downstreamStages(stage: ServerStageName): ServerStageName[] {
  const index = serverStages.indexOf(stage);
  return index < 0 ? [] : serverStages.slice(index + 1);
}

export function markDownstreamStale(project: WorkspaceProject, stage: ServerStageName): WorkspaceProject {
  const staleStages = new Set(project.staleStages);
  downstreamStages(stage).forEach((name) => staleStages.add(name));
  return { ...project, staleStages: [...staleStages] };
}

export interface StoryRoute {
  id: string;
  label: string;
  nodeIds: string[];
}

export function deriveRoutes(graph: StoryGraph): StoryRoute[] {
  const bySource = new Map<string, typeof graph.edges>();
  graph.edges.forEach((edge) => bySource.set(edge.sourceNodeId, [...(bySource.get(edge.sourceNodeId) || []), edge]));
  const nodeById = new Map(graph.nodes.map((node) => [node.id, node]));
  const routes: StoryRoute[] = [];
  const visit = (nodeId: string, path: string[], labels: string[], seen: Set<string>) => {
    if (seen.has(nodeId)) return;
    const nextSeen = new Set(seen).add(nodeId);
    const nextPath = [...path, nodeId];
    const outgoing = bySource.get(nodeId) || [];
    if (!outgoing.length) {
      const ending = nodeById.get(nodeId)?.title || nodeId;
      routes.push({ id: nextPath.join("/"), label: [...labels, ending].filter(Boolean).join(" → "), nodeIds: nextPath });
      return;
    }
    outgoing.forEach((edge) => visit(edge.targetNodeId, nextPath, edge.choiceText ? [...labels, edge.choiceText] : labels, nextSeen));
  };
  visit(graph.startNodeId, [], [], new Set());
  return routes;
}

export interface StoryboardViewGroup {
  sceneId: string;
  storyNodeId: string;
  title: string;
  shots: Storyboard["shots"];
}

export function summarizeWorkUnitStatuses(trace?: RunExecutionTrace): string {
  if (!trace?.workUnits.length) return "0 work units";
  const order: RunExecutionTrace["workUnits"][number]["status"][] = [
    "succeeded",
    "running",
    "queued",
    "failed",
    "quarantined",
    "outcome_unknown",
    "cancelled",
  ];
  const counts = new Map<string, number>();
  trace.workUnits.forEach((unit) => counts.set(unit.status, (counts.get(unit.status) || 0) + 1));
  return order
    .filter((status) => counts.has(status))
    .map((status) => `${counts.get(status)} ${status}`)
    .join(" · ");
}

export function groupStoryboard(storyboard: Storyboard, plan: SceneBeatPlan, route?: StoryRoute): StoryboardViewGroup[] {
  const allowed = route ? new Set(route.nodeIds) : undefined;
  return plan.scenes
    .filter((scene) => !allowed || allowed.has(scene.storyNodeId))
    .map((scene) => ({
      sceneId: scene.id,
      storyNodeId: scene.storyNodeId,
      title: scene.title,
      shots: storyboard.shots.filter((shot) => shot.sceneId === scene.id).sort((a, b) => a.order - b.order),
    }))
    .filter((group) => group.shots.length > 0);
}

export function traceEvents(trace: RunTrace, executionTrace?: RunExecutionTrace): TraceEvent[] {
  const correctionLimit = typeof trace.run.providerSnapshot.maxSemanticCorrections === "number"
    ? trace.run.providerSnapshot.maxSemanticCorrections
    : 2;
  const maxAttempts = Math.max(1, correctionLimit + 1);
  const usageByAttempt = new Map<string, { inputTokens: number | null; outputTokens: number | null }>();
  trace.artifacts.forEach((artifact) => {
    if (artifact.kind !== "response" || !artifact.attemptId || !artifact.content || typeof artifact.content !== "object") return;
    const usage = (artifact.content as Record<string, unknown>).usage;
    if (!usage || typeof usage !== "object") return;
    const values = usage as Record<string, unknown>;
    usageByAttempt.set(artifact.attemptId, {
      inputTokens: typeof values.inputTokens === "number" ? values.inputTokens : null,
      outputTokens: typeof values.outputTokens === "number" ? values.outputTokens : null,
    });
  });
  const attempts = trace.attempts.map((attempt) => ({
    id: attempt.id,
    at: attempt.startedAt,
    stage: attempt.stage,
    kind: attempt.status === "failed" ? "error" as const : "request" as const,
    title: `Attempt ${attempt.attemptNumber}/${maxAttempts} · ${attempt.status}`,
    status: attempt.status === "failed" ? "error" as const : attempt.status === "running" ? "pending" as const : "ok" as const,
    detail: [
      `Outcome: ${attempt.outcomeUnknown ? "unknown" : attempt.outcomeCode || attempt.status}`,
      `Lineage: ${attempt.attemptKind === "correction" ? `correction ← ${attempt.sourceAttemptId || "prior attempt"}` : "primary"}`,
      `Elapsed: ${formatAttemptDuration(attempt.startedAt, attempt.finishedAt)}`,
      formatAttemptUsage(usageByAttempt.get(attempt.id)),
      attempt.error ? `Failure: ${attempt.error}` : "",
      [attempt.provider, attempt.model].filter(Boolean).join(" · "),
    ].filter(Boolean).join("\n"),
  }));
  const artifacts = trace.artifacts
    .filter((artifact): artifact is typeof artifact & { stage: ServerStageName } => Boolean(artifact.stage))
    .map((artifact) => {
      const content = artifact.content && typeof artifact.content === "object"
        ? artifact.content as Record<string, unknown>
        : {};
      const messages = Array.isArray(content.messages) ? content.messages : [];
      const promptFor = (role: "system" | "user") => messages
        .filter((message): message is { role: string; content: string } => (
          Boolean(message)
          && typeof message === "object"
          && (message as Record<string, unknown>).role === role
          && typeof (message as Record<string, unknown>).content === "string"
        ))
        .map((message) => message.content)
        .join("\n\n");
      const accepted = artifact.kind === "validation" ? content.accepted : undefined;
      const issues = artifact.kind === "validation" && Array.isArray(content.issues)
        ? content.issues
        : [];
      const artifactStatus: TraceEvent["status"] = accepted === false
        ? "error"
        : accepted === true && issues.length > 0
          ? "warning"
          : "ok";
      return {
        id: artifact.id,
        at: artifact.createdAt,
        stage: artifact.stage,
        kind: artifact.kind === "canonical" || artifact.kind === "media" ? "install" as const : artifact.kind,
        title: `${artifact.kind} artifact`,
        status: artifactStatus,
        systemPrompt: artifact.kind === "prompt" ? promptFor("system") : undefined,
        userPrompt: artifact.kind === "prompt" ? promptFor("user") : undefined,
        payload: artifact.content,
        detail: `sha256:${artifact.contentHash.slice(0, 12)} · ${artifact.mediaType}`,
      };
    });
  const topology = executionTrace?.storyGraphTopology;
  const topologyEvent: TraceEvent[] = topology ? [{
    id: `topology:${topology.topologyHash}`,
    at: topology.createdAt,
    stage: "story_graph",
    kind: "validation",
    title: "Story graph topology frozen",
    status: "ok",
    detail: `Topology: sha256:${topology.topologyHash.slice(0, 12)} · generation plan ${topology.generationPlanHash.slice(0, 12)}`,
    payload: topology.topology,
  }] : [];
  return [...attempts, ...artifacts, ...topologyEvent].sort((left, right) => left.at.localeCompare(right.at));
}

function formatAttemptDuration(startedAt: string, finishedAt: string | null): string {
  if (!finishedAt) return "running";
  const elapsed = Date.parse(finishedAt) - Date.parse(startedAt);
  return Number.isFinite(elapsed) && elapsed >= 0 ? `${elapsed} ms` : "unavailable";
}

function formatAttemptUsage(usage: { inputTokens: number | null; outputTokens: number | null } | undefined): string {
  if (!usage) return "Tokens: unavailable";
  return `Tokens: input ${usage.inputTokens ?? "—"} · output ${usage.outputTokens ?? "—"}`;
}

export function mergeProjectResponse(current: WorkspaceProject, incoming: Partial<WorkspaceProject>): WorkspaceProject {
  return {
    ...current,
    ...incoming,
    brief: incoming.brief || current.brief,
    storyBible: incoming.storyBible || current.storyBible,
    storyGraph: incoming.storyGraph || current.storyGraph,
    sceneBeats: incoming.sceneBeats || current.sceneBeats,
    storyboard: incoming.storyboard || current.storyboard,
    quarantines: incoming.quarantines || current.quarantines,
    staleStages: incoming.staleStages || current.staleStages,
    stageRevisions: incoming.stageRevisions || current.stageRevisions,
  };
}

export const stageLabels: Record<ServerStageName, string> = {
  story_bible: "故事圣经",
  story_graph: "剧情 DAG",
  scene_beats: "场景节拍",
  storyboard: "分镜脚本",
};
