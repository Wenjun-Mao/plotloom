import type {
  AudioPlan, Beat, ContinuityState, DialogueCue, DramaticScene, PipelineRun,
  ProviderSettings, Shot, Storyboard, TraceEvent, WorkspaceProject,
} from "./types";

const continuity = (note: string, facts: Record<string, unknown> = {}): ContinuityState => ({
  facts, entityStates: [], screenDirection: null, lighting: null, sound: null, notes: [note],
});

const audio = (durationUnits: number): AudioPlan => ({
  events: [{ id: "control-room-ambience", kind: "ambience", description: "控制室警报与通风系统底噪", startOffsetUnits: 0, durationUnits }],
});

const beat = (id: string, sceneId: string, order: number, description: string, purpose: string, entry: string, exit: string): Beat => ({
  id, sceneId, order, description, purpose, visibleEvent: description, immediateResult: exit, dramaticChange: purpose,
  entryState: continuity(entry), exitState: continuity(exit), continuityAnchors: [], continuityDelta: {},
});

const scene = (id: string, storyNodeId: string, title: string, objective: string, beatIds: string[], durationBudgetUnits: number, characterIds: string[] = ["char_ruanxing"], entryFacts: Record<string, unknown> = {}, exitFacts: Record<string, unknown> = {}): DramaticScene => ({
  id, storyNodeId, order: 1, title, objective, locationId: "loc_control", characterIds, beatIds,
  durationBudgetUnits, entryState: continuity("承接上一场", entryFacts), exitState: continuity("场景动作完成", exitFacts),
});

const shot = (id: string, sceneId: string, order: number, title: string, shotSize: Shot["shotSize"], durationUnits: number, action: string, cueIds: string[], characterIds: string[] = ["char_ruanxing"]): Shot => ({
  id, sceneId, order, title, shotSize, durationUnits, cameraAngle: "eye_level", cameraMovement: "stable", composition: "subject-led",
  visualIntent: action, motionIntent: action, action, transition: "cut", cueIds, audioPlan: audio(durationUnits),
  characterIds, locationId: "loc_control", propIds: [], requiredEntityStates: [], entryState: continuity("承接上一镜"), exitState: continuity("稳定停留"),
});

// The timing values are integer milliseconds and meet zh-CN/natural's 330ms-per-character floor.
const cue = (id: string, beatId: string, speakerId: string, text: string, estimatedDurationUnits: number): DialogueCue => ({
  id, beatId, order: 1, speakerId, voiceOver: null, text, language: "zh-CN", delivery: "natural", performanceNotes: "克制但紧迫", estimatedDurationUnits,
});

export const emptyStageContent: Pick<WorkspaceProject, "storyBible" | "storyGraph" | "sceneBeats" | "storyboard"> = {
  storyBible: { logline: "", premise: "", genre: "", tone: "", audience: "", narrativePromise: "", themes: [], worldRules: [], visualLanguage: "", knownFacts: [], openQuestions: [], sourceNotes: [], characters: [], locations: [], props: [] },
  storyGraph: { startNodeId: "", nodes: [], edges: [], joinContracts: [] },
  sceneBeats: { scenes: [], beats: [], dialogueCues: [] },
  storyboard: { shots: [], shotBeatLinks: [] },
};

export const defaultProviderSettings: ProviderSettings = {
  profileId: "default", profileVersion: 0, profileHash: "", redirectPolicy: "no_follow", textProvider: null, textBaseUrl: "https://api.atlascloud.ai/v1", textModel: "deepseek-v3", textAuthMode: "bearer", textCapabilities: { chatCompletions: true, jsonObject: false, jsonSchema: false }, textContextWindowTokens: 32768, textMaxOutputTokens: 8192, textTemperature: 0.2, textMaxConcurrency: 1, textConnectTimeoutSeconds: 10, textAttemptTimeoutSeconds: 300, imageProvider: null, imageBaseUrl: "https://api.atlascloud.ai/api/v1/model", imageModel: "openai/gpt-image-2/text-to-image", imageAuthMode: "bearer", videoProvider: null, videoBaseUrl: "https://api.atlascloud.ai/api/v1/model", videoModel: "xai/grok-imagine-video-v1.5/image-to-video", videoAuthMode: "bearer", textKeyAvailable: false, imageKeyAvailable: false, videoKeyAvailable: false, revision: 0, updatedAt: null,
};

const dialogueCues: DialogueCue[] = [
  cue("cue_b1", "b1", "char_ruanxing", "安迪，撑住。", 2400), cue("cue_b3", "b3", "char_ruanxing", "只能保住一边。", 2400), cue("cue_b4", "b4", "char_ruanxing", "没有第三条路了。", 2700), cue("cue_b5", "b5", "char_ruanxing", "月城会记得。", 2100), cue("cue_b6", "b6", "char_ruanxing", "我听见你了。", 2100), cue("cue_b7", "b7", "char_andi", "这一次，让我自己选。", 3300), cue("cue_b8", "b8", "char_ruanxing", "我不能再替你决定。", 3000), cue("cue_b10", "b10", "char_andi", "姐。", 900), cue("cue_b11", "b11", "char_andi", "谢谢你把它还给我。", 3300),
];

export const demoProject: WorkspaceProject = {
  revision: 1, stageRevisions: { story_bible: 1, story_graph: 1, scene_beats: 1, storyboard: 1 },
  brief: { title: "月城余晖", synopsis: "月城记忆控制室即将断电，维修学徒阮星必须在恢复全城记忆与释放被困弟弟之间选择。", genre: "科幻悬疑", visualStyle: "克制、紧迫的旧工业金属质感，琥珀记忆光与青色生命维持光形成稳定对照。", language: "zh-CN", aspectRatio: "16:9", targetPlaythroughSeconds: 180, decisionPointsPerPath: 2, endingCount: 3, nodeBudget: 10, maxOutDegree: 3, desiredJoinCount: 1, shotsPerSceneMin: 1, shotsPerSceneMax: 4 },
  storyBible: {
    logline: "倒计时归零前，一名维修学徒必须决定一座城市应该记住谁。", premise: "月城的记忆与救生系统共用一条即将断电的能源总线。", genre: "科幻悬疑", tone: "克制、紧迫", audience: "16+ 流媒体互动观众", narrativePromise: "每次选择都改变谁保有记忆与决定权。", themes: ["记忆与身份", "个人救援与集体责任", "被封死的第三条路"], worldRules: ["记忆恢复与救生舱共享同一能源总线", "应急杆已熔断且不可逆", "控制室只能接受一条最终指令"], visualLanguage: "旧工业金属、琥珀记忆光、青色生命维持光；镜头越接近选择越收紧。", knownFacts: ["安迪仍然活着", "能源只能支持一条主回路"], openQuestions: ["谁烧毁了应急杆"], sourceNotes: ["Plotloom 教学草案"],
    characters: [
      { id: "char_ruanxing", name: "阮星", role: "维修学徒 / 主角", description: "相信每个系统都能修复。", goal: "救出弟弟并保住城市记忆", traits: ["克制", "执拗"], visualAnchors: ["短黑发、旧工作服、右手绝缘手套"], soundAnchors: ["短促呼吸与工具碰撞"], voiceAnchors: ["年轻女声、压低语速"], allowedStates: ["focused", "strained"], continuityRules: ["绝缘手套始终在右手"] },
      { id: "char_andi", name: "安迪", role: "弟弟 / 救生舱乘员", description: "长期隐瞒病情。", goal: "让姐姐停止替自己做选择", traits: ["清醒", "虚弱"], visualAnchors: ["苍白、额侧传感器闪烁"], soundAnchors: ["破损通讯中的微弱电流"], voiceAnchors: ["虚弱男声、语句清晰"], allowedStates: ["awake", "weak"], continuityRules: ["始终通过破损屏幕出现"] },
    ],
    locations: [{ id: "loc_control", name: "记忆控制室", description: "旧月城的能源核心。", visualAnchors: ["旧工业金属与双路发光总线"], soundAnchors: ["警报与通风声"], allowedStates: ["locked", "active"], continuityRules: ["金色在左，青色在右"] }],
    props: [{ id: "prop_lever", name: "应急杆", description: "已经熔断的第三路线。", visualAnchors: ["焦黑断口"], soundAnchors: ["金属断裂声"], allowedStates: ["intact", "broken"], continuityRules: ["断裂后不可复原"] }],
  },
  storyGraph: {
    startNodeId: "arrival",
    nodes: [
      { id: "arrival", title: "冲入控制室", kind: "start", summary: "倒计时 47 秒，救生舱开始失压。" }, { id: "diagnose", title: "诊断双重故障", kind: "decision", summary: "两条能源回路互斥。" }, { id: "memory", title: "恢复全城记忆", kind: "scene", summary: "选择金色记忆总线。" }, { id: "rescue", title: "释放弟弟", kind: "scene", summary: "选择青色救生总线。" }, { id: "join", title: "弟弟请求自决", kind: "join", summary: "两条路径在通讯恢复处汇合。" }, { id: "final_decision", title: "交出最后指令", kind: "decision", summary: "阮星决定由谁承担最后一次选择。" }, { id: "ending_city", title: "城市醒来", kind: "ending", summary: "记忆恢复，救生舱沉默。" }, { id: "ending_brother", title: "两个人的黎明", kind: "ending", summary: "弟弟获救，城市失去名字。" }, { id: "ending_choice", title: "由他选择", kind: "ending", summary: "阮星交出最后指令权。" },
    ],
    edges: [
      { id: "e1", sourceNodeId: "arrival", targetNodeId: "diagnose", kind: "continuation", choiceText: null, stateEffects: {} }, { id: "e2", sourceNodeId: "diagnose", targetNodeId: "memory", kind: "choice", choiceText: "金色键", stateEffects: { memoryBus: "active" } }, { id: "e3", sourceNodeId: "diagnose", targetNodeId: "rescue", kind: "choice", choiceText: "青色键", stateEffects: { rescueBus: "active" } }, { id: "e4", sourceNodeId: "memory", targetNodeId: "join", kind: "continuation", choiceText: null, stateEffects: { channel: "open" } }, { id: "e5", sourceNodeId: "rescue", targetNodeId: "join", kind: "continuation", choiceText: null, stateEffects: { channel: "open" } }, { id: "e6", sourceNodeId: "join", targetNodeId: "final_decision", kind: "continuation", choiceText: null, stateEffects: {} }, { id: "e7", sourceNodeId: "final_decision", targetNodeId: "ending_city", kind: "choice", choiceText: "替他决定", stateEffects: { ending: "city" } }, { id: "e8", sourceNodeId: "final_decision", targetNodeId: "ending_brother", kind: "choice", choiceText: "切向救生舱", stateEffects: { ending: "brother" } }, { id: "e9", sourceNodeId: "final_decision", targetNodeId: "ending_choice", kind: "choice", choiceText: "交出权限", stateEffects: { ending: "agency" } },
    ],
    joinContracts: [{ id: "join_contract_1", joinNodeId: "join", incomingNodeIds: ["memory", "rescue"], requiredStateKeys: ["channel"], allowedDifferences: [], reconciliation: "任一路径到达时都恢复一次通讯，再进入最终决定。", notes: "保留前序选择状态。" }],
  },
  sceneBeats: {
    scenes: [
      scene("scene_arrival", "arrival", "冲入控制室", "建立倒计时与私人目标", ["b1", "b2"], 10000), scene("scene_diagnose", "diagnose", "诊断双重故障", "建立互斥选择并封死第三条路", ["b3", "b4"], 13000), scene("scene_memory", "memory", "接通记忆总线", "让城市记忆路线付出私人代价", ["b5"], 7000, ["char_ruanxing", "char_andi"], {}, { channel: "open" }), scene("scene_rescue", "rescue", "接通救生总线", "让营救路线显露集体代价", ["b6"], 7000, ["char_ruanxing", "char_andi"], {}, { channel: "open" }), scene("scene_join", "join", "通讯汇合", "让安迪重新取得表达意愿的机会", ["b7"], 8000, ["char_ruanxing", "char_andi"], { channel: "open" }), scene("scene_final_decision", "final_decision", "最后指令", "把最终选择权摆到阮星面前", ["b8"], 6000, ["char_ruanxing", "char_andi"]), scene("scene_ending_city", "ending_city", "城市醒来", "收束恢复记忆的代价", ["b9"], 8000), scene("scene_ending_brother", "ending_brother", "两个人的黎明", "收束营救弟弟的代价", ["b10"], 8000, ["char_ruanxing", "char_andi"]), scene("scene_ending_choice", "ending_choice", "由他选择", "收束交还选择权的后果", ["b11"], 8000, ["char_ruanxing", "char_andi"]),
    ],
    beats: [
      beat("b1", "scene_arrival", 1, "阮星撞开控制室气密门。", "建立倒计时压力", "走廊红灯闪烁", "阮星扶住主控台"), beat("b2", "scene_arrival", 2, "救生舱压力读数跌破安全线。", "暴露私人目标", "主控台待机", "青色读数持续下降"), beat("b3", "scene_diagnose", 1, "阮星依次触碰金色与青色回路图。", "建立互斥选择", "双路均锁定", "两枚实体键升起"), beat("b4", "scene_diagnose", 2, "她拉动应急杆，杆体在手中断裂。", "封死第三条路", "右手握杆", "焦黑断杆落地"), beat("b5", "scene_memory", 1, "阮星按下金色键，城市记忆索引开始回流。", "兑现集体记忆的诱惑与代价", "金色键已按下", "城市记忆开始恢复"), beat("b6", "scene_rescue", 1, "阮星按下青色键，安迪的救生舱恢复压力。", "兑现私人营救的诱惑与代价", "青色键已按下", "救生舱通讯恢复"), beat("b7", "scene_join", 1, "破损屏幕亮起，安迪要求姐姐让自己决定。", "让分支汇流到同一伦理问题", "通讯通道恢复", "最后指令等待确认"), beat("b8", "scene_final_decision", 1, "三条最终指令同时出现在阮星面前。", "建立第二个决定点", "最后指令等待确认", "选择已经写入系统"), beat("b9", "scene_ending_city", 1, "金色光流越过月城，安迪的屏幕熄灭。", "呈现恢复城市记忆的结局", "金色总线满载", "城市灯光逐区亮起"), beat("b10", "scene_ending_brother", 1, "救生舱门打开，远处的城市标识逐一归零。", "呈现救出弟弟的结局", "青色总线满载", "救生舱门打开"), beat("b11", "scene_ending_choice", 1, "安迪在屏幕另一端按下自己的选择。", "呈现交还主体性的结局", "权限移交完成", "安迪按下自己的选择"),
    ],
    dialogueCues,
  },
  storyboard: {
    shots: [
      shot("shot_01", "scene_arrival", 1, "门开", "wide", 6000, "气密门向两侧弹开，阮星冲入控制室。", ["cue_b1"]), shot("shot_02", "scene_arrival", 2, "压力下坠", "insert", 4000, "青色压力数字从 19 跳到 18。", []), shot("shot_03", "scene_diagnose", 1, "双键升起", "medium", 8000, "金色与青色实体键从主控台升起。", ["cue_b3"]), shot("shot_04", "scene_diagnose", 2, "断杆", "insert", 5000, "应急杆在阮星手中断裂，焦黑断口冒出白烟。", ["cue_b4"]), shot("shot_05", "scene_memory", 1, "记忆回流", "wide", 7000, "金色光流沿城市索引高速扩散。", ["cue_b5"], ["char_ruanxing", "char_andi"]), shot("shot_06", "scene_rescue", 1, "舱压恢复", "medium", 7000, "青色生命维持曲线重新抬升。", ["cue_b6"], ["char_ruanxing", "char_andi"]), shot("shot_07", "scene_join", 1, "弟弟开口", "medium", 8000, "破损屏幕上的安迪缓慢抬眼。", ["cue_b7"], ["char_ruanxing", "char_andi"]), shot("shot_08", "scene_final_decision", 1, "三条指令", "insert", 6000, "三枚指令键在阮星指尖下依次亮起。", ["cue_b8"], ["char_ruanxing", "char_andi"]), shot("shot_09", "scene_ending_city", 1, "城市醒来", "wide", 8000, "月城建筑群从黑暗中逐区亮起金光。", []), shot("shot_10", "scene_ending_brother", 1, "舱门开启", "wide", 8000, "救生舱门在青色蒸汽中缓慢开启。", ["cue_b10"], ["char_ruanxing", "char_andi"]), shot("shot_11", "scene_ending_choice", 1, "他的选择", "medium", 8000, "安迪的手落在屏幕另一端的确认键上。", ["cue_b11"], ["char_ruanxing", "char_andi"]),
    ],
    shotBeatLinks: [["shot_01", "b1"], ["shot_02", "b2"], ["shot_03", "b3"], ["shot_04", "b4"], ["shot_05", "b5"], ["shot_06", "b6"], ["shot_07", "b7"], ["shot_08", "b8"], ["shot_09", "b9"], ["shot_10", "b10"], ["shot_11", "b11"]].map(([shotId, beatId]) => ({ shotId, beatId, role: "primary" as const, coverageWeight: 1 })),
  } satisfies Storyboard,
  quarantines: [{ id: "q1", stage: "story_graph", code: "GRAPH_ENDING_COUNT", message: "模型返回 2 个结局，合同要求 3 个。", rawOutput: "{\"nodes\":[...],\"endings\":[\"city\",\"brother\"]}", repairHint: "保留已有节点，增加一个由角色主动交出选择权形成的第三结局。" }], staleStages: [],
};

const demoStageHead = (stage: "story_bible" | "story_graph" | "scene_beats" | "storyboard", status: "ready" | "stale") => ({ stage, status, revision: 1, schemaVersion: 2 as const, entityRevisionId: `demo-${stage}-r1`, contentHash: `demo-${stage}-hash`, inputRevisions: {}, staleReasons: status === "stale" ? ["教学草案中的上游示例已变化"] : [], updatedAt: "2026-08-30T00:00:00Z" });

export const demoRun: PipelineRun = {
  id: "run_demo_01", projectId: "project_demo", kind: "pipeline", parentRunId: null, repairStage: null, repairSource: null, workUnitRepairScopeId: null, providerSnapshot: {}, status: "quarantined", requestedStages: ["story_bible", "story_graph", "scene_beats", "storyboard"], canonicalSnapshot: { projectId: "project_demo", projectRevision: demoProject.revision, brief: demoProject.brief, stageHeads: { story_bible: demoStageHead("story_bible", "ready"), story_graph: demoStageHead("story_graph", "ready"), scene_beats: demoStageHead("scene_beats", "ready"), storyboard: demoStageHead("storyboard", "stale") }, snapshotHash: "demo-snapshot-hash", capturedAt: "2026-08-30T00:00:00Z" }, instructions: null, legacyUnsealed: false, resultRevisionIds: [], error: "教学草案中的剧情图验证失败", failureCode: "validation.canonical_rejected", failedStage: "story_graph", createdAt: "2026-08-30T00:00:00Z", startedAt: "2026-08-30T00:00:01Z", finishedAt: "2026-08-30T00:00:17Z",
};

export const demoTrace: TraceEvent[] = [
  { id: "t1", at: "10:42:01", stage: "story_bible", kind: "prompt", title: "Story bible prompt compiled", status: "ok", systemPrompt: "你是 Plotloom · 叙织的故事圣经编辑器。只返回符合合同的 JSON。", userPrompt: "根据项目简报建立人物、世界规则与视觉语言。\n片名：月城余晖\n目标时长：180 秒。" },
  { id: "t2", at: "10:42:08", stage: "story_bible", kind: "validation", title: "Schema and continuity checks passed", status: "ok", detail: "2 characters · 3 world rules · 3 themes" },
  { id: "t3", at: "10:42:09", stage: "story_graph", kind: "prompt", title: "Graph generation requested", status: "ok", systemPrompt: "构造有向无环叙事图；遵守节点预算、出度和结局数。", userPrompt: "节点预算 10；每路径 2 个决定；3 个结局；期望 1 个汇合。" },
  { id: "t4", at: "10:42:17", stage: "story_graph", kind: "validation", title: "Graph contract rejected", status: "error", detail: "GRAPH_ENDING_COUNT: expected 3, received 2", payload: { expectedEndingCount: 3, actualEndingCount: 2 } },
  { id: "t5", at: "10:42:17", stage: "story_graph", kind: "error", title: "Output moved to quarantine", status: "warning", detail: "No project stage was overwritten. Repair can reuse the raw output." },
];
