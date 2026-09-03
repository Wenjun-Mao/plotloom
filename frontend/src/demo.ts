import type { PipelineRun, ProviderSettings, TraceEvent, WorkspaceProject } from "./types";

export const emptyStageContent: Pick<WorkspaceProject, "storyBible" | "storyGraph" | "sceneBeats" | "storyboard"> = {
  storyBible: { logline: "", premise: "", genre: "", tone: "", audience: "", narrativePromise: "", themes: [], worldRules: [], visualLanguage: "", knownFacts: [], openQuestions: [], sourceNotes: [], characters: [], locations: [], props: [] },
  storyGraph: { startNodeId: "", nodes: [], edges: [], joinContracts: [] },
  sceneBeats: { scenes: [], beats: [] },
  storyboard: { shots: [], shotBeatLinks: [] },
};

export const defaultProviderSettings: ProviderSettings = {
  profileId: "default",
  profileVersion: 0,
  profileHash: "",
  redirectPolicy: "no_follow",
  textProvider: null,
  textBaseUrl: "https://api.atlascloud.ai/v1",
  textModel: "deepseek-v3",
  textAuthMode: "bearer",
  textCapabilities: { chatCompletions: true, jsonObject: false, jsonSchema: false },
  textContextWindowTokens: 32768,
  textMaxOutputTokens: 8192,
  textTemperature: 0.2,
  textMaxConcurrency: 1,
  textConnectTimeoutSeconds: 10,
  textAttemptTimeoutSeconds: 300,
  imageProvider: null,
  imageBaseUrl: "https://api.atlascloud.ai/api/v1/model",
  imageModel: "openai/gpt-image-2/text-to-image",
  imageAuthMode: "bearer",
  videoProvider: null,
  videoBaseUrl: "https://api.atlascloud.ai/api/v1/model",
  videoModel: "xai/grok-imagine-video-v1.5/image-to-video",
  videoAuthMode: "bearer",
  textKeyAvailable: false,
  imageKeyAvailable: false,
  videoKeyAvailable: false,
  revision: 0,
  updatedAt: null,
};

export const demoProject: WorkspaceProject = {
  revision: 1,
  stageRevisions: { story_bible: 1, story_graph: 1, scene_beats: 1, storyboard: 1 },
  brief: {
    title: "月城余晖",
    synopsis: "月城记忆控制室即将断电，维修学徒阮星必须在恢复全城记忆与释放被困弟弟之间选择。",
    genre: "科幻悬疑",
    visualStyle: "克制、紧迫的旧工业金属质感，琥珀记忆光与青色生命维持光形成稳定对照。",
    language: "zh-CN",
    aspectRatio: "16:9",
    targetPlaythroughSeconds: 180,
    decisionPointsPerPath: 2,
    endingCount: 3,
    nodeBudget: 10,
    maxOutDegree: 3,
    desiredJoinCount: 1,
    shotsPerSceneMin: 2,
    shotsPerSceneMax: 4,
  },
  storyBible: {
    logline: "倒计时归零前，一名维修学徒必须决定一座城市应该记住谁。",
    premise: "月城的记忆与救生系统共用一条即将断电的能源总线。",
    genre: "科幻悬疑",
    tone: "克制、紧迫",
    audience: "16+ 流媒体互动观众",
    narrativePromise: "每次选择都改变谁保有记忆与决定权。",
    themes: ["记忆与身份", "个人救援与集体责任", "被封死的第三条路"],
    worldRules: ["记忆恢复与救生舱共享同一能源总线", "应急杆已熔断且不可逆", "控制室只能接受一条最终指令"],
    visualLanguage: "旧工业金属、琥珀记忆光、青色生命维持光；镜头越接近选择越收紧。",
    knownFacts: ["安迪仍然活着", "能源只能支持一条主回路"],
    openQuestions: ["谁烧毁了应急杆"],
    sourceNotes: ["Plotloom 教学草案"],
    characters: [
      { id: "char_ruanxing", name: "阮星", role: "维修学徒 / 主角", description: "相信每个系统都能修复。", goal: "救出弟弟并保住城市记忆", traits: ["克制", "执拗"], visualIdentity: "短黑发、旧工作服、右手绝缘手套", continuityRules: ["绝缘手套始终在右手"] },
      { id: "char_andi", name: "安迪", role: "弟弟 / 救生舱乘员", description: "长期隐瞒病情。", goal: "让姐姐停止替自己做选择", traits: ["清醒", "虚弱"], visualIdentity: "苍白、额侧传感器闪烁", continuityRules: ["始终通过破损屏幕出现"] },
    ],
    locations: [{ id: "loc_control", name: "记忆控制室", description: "旧月城的能源核心。", visualIdentity: "旧工业金属与双路发光总线", continuityRules: ["金色在左，青色在右"] }],
    props: [{ id: "prop_lever", name: "应急杆", description: "已经熔断的第三路线。", visualIdentity: "焦黑断口", continuityRules: ["断裂后不可复原"] }],
  },
  storyGraph: {
    startNodeId: "arrival",
    nodes: [
      { id: "arrival", title: "冲入控制室", kind: "start", summary: "倒计时 47 秒，救生舱开始失压。" },
      { id: "diagnose", title: "诊断双重故障", kind: "decision", summary: "两条能源回路互斥。" },
      { id: "memory", title: "恢复全城记忆", kind: "scene", summary: "选择金色记忆总线。" },
      { id: "rescue", title: "释放弟弟", kind: "scene", summary: "选择青色救生总线。" },
      { id: "join", title: "弟弟请求自决", kind: "join", summary: "两条路径在通讯恢复处汇合。" },
      { id: "ending_city", title: "城市醒来", kind: "ending", summary: "记忆恢复，救生舱沉默。" },
      { id: "ending_brother", title: "两个人的黎明", kind: "ending", summary: "弟弟获救，城市失去名字。" },
      { id: "ending_choice", title: "由他选择", kind: "ending", summary: "阮星交出最后指令权。" },
    ],
    edges: [
      { id: "e1", sourceNodeId: "arrival", targetNodeId: "diagnose", kind: "continuation", choiceText: null, stateEffects: {} },
      { id: "e2", sourceNodeId: "diagnose", targetNodeId: "memory", kind: "choice", choiceText: "金色键", stateEffects: { memoryBus: "active" } },
      { id: "e3", sourceNodeId: "diagnose", targetNodeId: "rescue", kind: "choice", choiceText: "青色键", stateEffects: { rescueBus: "active" } },
      { id: "e4", sourceNodeId: "memory", targetNodeId: "join", kind: "continuation", choiceText: null, stateEffects: { channel: "open" } },
      { id: "e5", sourceNodeId: "rescue", targetNodeId: "join", kind: "continuation", choiceText: null, stateEffects: { channel: "open" } },
      { id: "e6", sourceNodeId: "join", targetNodeId: "ending_city", kind: "choice", choiceText: "替他决定", stateEffects: { ending: "city" } },
      { id: "e7", sourceNodeId: "join", targetNodeId: "ending_brother", kind: "choice", choiceText: "切向救生舱", stateEffects: { ending: "brother" } },
      { id: "e8", sourceNodeId: "join", targetNodeId: "ending_choice", kind: "choice", choiceText: "交出权限", stateEffects: { ending: "agency" } },
    ],
    joinContracts: [{ id: "join_contract_1", joinNodeId: "join", incomingNodeIds: ["memory", "rescue"], requiredStateKeys: ["channel"], allowedDifferences: ["memoryBus", "rescueBus"], reconciliation: "任一路径到达时都恢复一次通讯，再进入最终决定。", notes: "保留前序选择状态。" }],
  },
  sceneBeats: {
    scenes: [
      { id: "scene_arrival", storyNodeId: "arrival", title: "冲入控制室", objective: "建立倒计时与私人目标", locationId: "loc_control", characterIds: ["char_ruanxing"], beatIds: ["b1", "b2"], entryState: continuity("走廊红灯闪烁"), exitState: continuity("阮星扶住主控台") },
      { id: "scene_diagnose", storyNodeId: "diagnose", title: "诊断双重故障", objective: "建立互斥选择并封死第三条路", locationId: "loc_control", characterIds: ["char_ruanxing"], beatIds: ["b3", "b4"], entryState: continuity("双路均锁定"), exitState: continuity("焦黑断杆落地") },
    ],
    beats: [
      beat("b1", "scene_arrival", 1, "阮星撞开控制室气密门。", "建立倒计时压力", "走廊红灯闪烁", "阮星扶住主控台"),
      beat("b2", "scene_arrival", 2, "救生舱压力读数跌破安全线。", "暴露私人目标", "主控台待机", "青色读数持续下降"),
      beat("b3", "scene_diagnose", 1, "阮星依次触碰金色与青色回路图。", "建立互斥选择", "双路均锁定", "两枚实体键升起"),
      beat("b4", "scene_diagnose", 2, "她拉动应急杆，杆体在手中断裂。", "封死第三条路", "右手握杆", "焦黑断杆落地"),
    ],
  },
  storyboard: {
    shots: [
      shot("shot_01", "scene_arrival", 1, "门开", "wide", 6, "气密门向两侧弹开，阮星冲入控制室。", "安迪，撑住。"),
      shot("shot_02", "scene_arrival", 2, "压力下坠", "insert", 4, "青色压力数字从 19 跳到 18。", ""),
      shot("shot_03", "scene_diagnose", 3, "双键升起", "medium", 8, "金色与青色实体键从主控台升起。", "只能保住一边。"),
    ],
    shotBeatLinks: [
      { shotId: "shot_01", beatId: "b1", role: "primary", coverageWeight: 1 },
      { shotId: "shot_02", beatId: "b2", role: "primary", coverageWeight: 1 },
      { shotId: "shot_03", beatId: "b3", role: "primary", coverageWeight: 1 },
    ],
  },
  quarantines: [
    { id: "q1", stage: "story_graph", code: "GRAPH_ENDING_COUNT", message: "模型返回 2 个结局，合同要求 3 个。", rawOutput: "{\"nodes\":[...],\"endings\":[\"city\",\"brother\"]}", repairHint: "保留已有节点，增加一个由角色主动交出选择权形成的第三结局。" },
  ],
  staleStages: ["storyboard"],
};

export const demoRun: PipelineRun = {
  id: "run_demo_01",
  projectId: "project_demo",
  kind: "pipeline",
  parentRunId: null,
  repairStage: null,
  repairSource: null,
  providerSnapshot: {},
  status: "quarantined",
  requestedStages: ["story_bible", "story_graph", "scene_beats", "storyboard"],
  canonicalSnapshot: {
    projectId: "project_demo",
    projectRevision: demoProject.revision,
    brief: demoProject.brief,
    stageHeads: Object.fromEntries((["story_bible", "story_graph", "scene_beats", "storyboard"] as const).map((stage) => [stage, {
      stage,
      status: stage === "storyboard" ? "stale" as const : "ready" as const,
      revision: demoProject.stageRevisions[stage],
      entityRevisionId: `demo-${stage}-r1`,
      contentHash: `demo-${stage}-hash`,
      inputRevisions: {},
      staleReasons: stage === "storyboard" ? ["教学草案中的上游示例已变化"] : [],
      updatedAt: "2026-08-30T00:00:00Z",
    }])) as PipelineRun["canonicalSnapshot"]["stageHeads"],
    snapshotHash: "demo-snapshot-hash",
    capturedAt: "2026-08-30T00:00:00Z",
  },
  instructions: null,
  legacyUnsealed: false,
  resultRevisionIds: [],
  error: "教学草案中的剧情图验证失败",
  createdAt: "2026-08-30T00:00:00Z",
  startedAt: "2026-08-30T00:00:01Z",
  finishedAt: "2026-08-30T00:00:17Z",
};

export const demoTrace: TraceEvent[] = [
  { id: "t1", at: "10:42:01", stage: "story_bible", kind: "prompt", title: "Story bible prompt compiled", status: "ok", systemPrompt: "你是 Plotloom · 叙织的故事圣经编辑器。只返回符合合同的 JSON。", userPrompt: "根据项目简报建立人物、世界规则与视觉语言。\n片名：月城余晖\n目标时长：180 秒。" },
  { id: "t2", at: "10:42:08", stage: "story_bible", kind: "validation", title: "Schema and continuity checks passed", status: "ok", detail: "2 characters · 3 world rules · 3 themes" },
  { id: "t3", at: "10:42:09", stage: "story_graph", kind: "prompt", title: "Graph generation requested", status: "ok", systemPrompt: "构造有向无环叙事图；遵守节点预算、出度和结局数。", userPrompt: "节点预算 10；每路径 2 个决定；3 个结局；期望 1 个汇合。" },
  { id: "t4", at: "10:42:17", stage: "story_graph", kind: "validation", title: "Graph contract rejected", status: "error", detail: "GRAPH_ENDING_COUNT: expected 3, received 2", payload: { expectedEndingCount: 3, actualEndingCount: 2 } },
  { id: "t5", at: "10:42:17", stage: "story_graph", kind: "error", title: "Output moved to quarantine", status: "warning", detail: "No project stage was overwritten. Repair can reuse the raw output." },
];

function continuity(note: string) {
  return {
    facts: {},
    characterStates: {},
    propStates: {},
    locationState: null,
    screenDirection: null,
    lighting: null,
    sound: null,
    notes: [note],
  };
}

function beat(id: string, sceneId: string, order: number, description: string, purpose: string, entry: string, exit: string) {
  return { id, sceneId, order, description, purpose, visibleEvent: description, dialogue: "", immediateResult: exit, dramaticChange: purpose, entryState: continuity(entry), exitState: continuity(exit), continuityAnchors: [], continuityDelta: {} };
}

function shot(id: string, sceneId: string, order: number, title: string, shotSize: "wide" | "insert" | "medium", durationSeconds: number, action: string, dialogue: string) {
  return { id, sceneId, order, title, shotSize, durationSeconds, cameraAngle: "eye_level", cameraMovement: "stable", composition: "subject-led", visualIntent: action, motionIntent: action, action, dialogue, audio: "控制室警报底噪", transition: "cut", characterIds: ["char_ruanxing"], locationId: "loc_control", propIds: [], entryState: continuity("承接上一镜"), exitState: continuity("稳定停留") };
}
