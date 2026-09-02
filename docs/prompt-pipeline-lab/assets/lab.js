(function initializePromptPipelineLab() {
  "use strict";

  const data = window.NFPromptLabData;
  if (!data) throw new Error("Prompt Pipeline Lab fixtures are unavailable.");

  const byId = (id) => document.getElementById(id);
  const clone = (value) => JSON.parse(JSON.stringify(value));
  const state = {
    mode: "interactive",
    preset: "defaults",
    serialTone: data.defaults.serialTone,
    promptTab: "request",
    responseScenario: "clean",
    responseStep: "envelope",
    mediaTab: "image",
  };

  const promptTabLabels = {
    request: "浏览器发给 Narrative Forge 后端的 POST 请求体",
    system: "发给文本模型的 system message",
    user: "发给文本模型的 user message",
    model: "后端发给 OpenAI-compatible 供应商的调用参数",
  };

  const toneLabels = {
    drama: "情感正剧",
    thriller: "悬疑惊悚",
    comedy: "轻喜剧",
    action: "动作冒险",
    romance: "爱情甜宠",
  };

  function textElement(tagName, className, text) {
    const element = document.createElement(tagName);
    if (className) element.className = className;
    element.textContent = text;
    return element;
  }

  function calculateStoryNodes(depth, branches) {
    let total = 0;
    for (let level = 0; level < depth; level += 1) total += branches ** level;
    return total;
  }

  function formValues() {
    return {
      title: byId("inputTitle").value,
      synopsis: byId("inputSynopsis").value,
      genre: byId("inputGenre").value,
      aspectRatio: byId("inputAspect").value,
      visualStyle: byId("inputStyle").value,
      character: byId("inputCharacter").value,
      treeDepth: Number(byId("inputDepth").value),
      branchCount: Number(byId("inputBranches").value),
      shotsPerNode: Number(byId("inputShotsPerNode").value),
      serialTone: state.serialTone,
      episodeTitle: byId("inputEpisodeTitle").value,
      episodeSynopsis: byId("inputEpisodeSynopsis").value,
      episodeObjective: byId("inputEpisodeObjective").value,
      episodeHook: byId("inputEpisodeHook").value,
      episodeEnding: byId("inputEpisodeEnding").value,
      episodeShotCount: Number(byId("inputEpisodeShots").value),
      includeCharacterCard: byId("includeCharacterCard").checked,
      includeSceneCard: byId("includeSceneCard").checked,
      characters: byId("includeCharacterCard").checked ? [clone(data.characterCard)] : [],
      sceneCards: byId("includeSceneCard").checked ? [clone(data.sceneCard)] : [],
      model: data.defaults.model,
      textBaseUrl: data.defaults.textBaseUrl,
    };
  }

  function applyPreset(name) {
    const preset = name === "custom" ? data.customPreset : data.defaults;
    state.preset = name;
    state.serialTone = preset.serialTone;
    byId("inputTitle").value = preset.title;
    byId("inputSynopsis").value = preset.synopsis;
    byId("inputGenre").value = preset.genre;
    byId("inputAspect").value = preset.aspectRatio;
    byId("inputStyle").value = preset.visualStyle;
    byId("inputCharacter").value = preset.character;
    byId("inputDepth").value = String(preset.treeDepth);
    byId("inputBranches").value = String(preset.branchCount);
    byId("inputShotsPerNode").value = String(preset.shotsPerNode);
    byId("inputEpisodeTitle").value = preset.episodeTitle;
    byId("inputEpisodeSynopsis").value = preset.episodeSynopsis;
    byId("inputEpisodeObjective").value = preset.episodeObjective;
    byId("inputEpisodeHook").value = preset.episodeHook;
    byId("inputEpisodeEnding").value = preset.episodeEnding;
    byId("inputEpisodeShots").value = String(preset.episodeShotCount);
    byId("includeCharacterCard").checked = name === "custom";
    byId("includeSceneCard").checked = name === "custom";
    document.querySelectorAll("[data-preset]").forEach((button) => {
      const active = button.dataset.preset === name;
      button.classList.toggle("is-active", active);
      button.setAttribute("aria-pressed", String(active));
    });
    renderPromptWorkbench();
    renderMediaPrompt();
  }

  function setMode(mode) {
    state.mode = mode;
    byId("interactiveControls").hidden = mode !== "interactive";
    byId("serialControls").hidden = mode !== "serial";
    document.querySelectorAll("[data-mode]").forEach((button) => {
      const active = button.dataset.mode === mode;
      button.classList.toggle("is-active", active);
      button.setAttribute("aria-pressed", String(active));
    });
    renderPromptWorkbench();
    renderMediaPrompt();
  }

  function pythonCompactJson(value) {
    if (Array.isArray(value)) return `[${value.map(pythonCompactJson).join(", ")}]`;
    if (value && typeof value === "object") {
      return `{${Object.entries(value)
        .map(([key, child]) => `${JSON.stringify(key)}: ${pythonCompactJson(child)}`)
        .join(", ")}}`;
    }
    return JSON.stringify(value);
  }

  function interactiveFrontendRequest(values) {
    return {
      model: values.model,
      text_base_url: values.textBaseUrl,
      text_api_key: "",
      title: values.title,
      synopsis: values.synopsis,
      genre: values.genre,
      character: values.character,
      characters: values.characters,
      scene_cards: values.sceneCards,
      visual_style: values.visualStyle,
      tree_depth: values.treeDepth,
      branch_count: values.branchCount,
      shots_per_node: values.shotsPerNode,
    };
  }

  function interactivePromptBundle(values) {
    const expectedStoryNodes = calculateStoryNodes(values.treeDepth, values.branchCount);
    const expectedNodes = expectedStoryNodes * values.shotsPerNode;
    const story = {
      title: values.title.slice(0, 80),
      synopsis: values.synopsis.slice(0, 6000),
      genre: values.genre.slice(0, 80),
      character: values.character.slice(0, 3000),
      characters: values.characters,
      scene_cards: values.sceneCards,
      visual_style: values.visualStyle.slice(0, 3000),
      tree_depth: values.treeDepth,
      branch_count: values.branchCount,
      shots_per_node: values.shotsPerNode,
      expected_story_nodes: expectedStoryNodes,
      expected_nodes: expectedNodes,
    };
    const system = "你是互动影游编剧兼分镜导演。请严格输出单个 JSON 对象，不要输出 Markdown、代码围栏或解释。剧情必须形成从起点到多个结局的有向树，每次玩家选择都应造成可感知的剧情差异。";
    const user = [
      "根据下面的项目设定生成完整剧情树。先设计 expected_story_nodes 个互动剧情节点，再把每个互动剧情节点拆成 shots_per_node 个连续分镜，最终 scenes 总数必须为 expected_nodes。同一互动剧情节点内部，前 shots_per_node-1 个分镜 choices 为空，并用 nextKey 指向本节点下一分镜；每个非结局互动剧情节点的最后一个分镜必须恰好拥有 branch_count 个 choices，且 choice.targetKey 必须指向目标互动剧情节点的第 1 个分镜；最后一层互动剧情节点的最后分镜 choices 为空。",
      `项目设定：${pythonCompactJson(story)}`,
      "返回结构：{\"startKey\":\"n0_s1\",\"characters\":[{\"name\":\"角色名\",\"ageRange\":\"年龄段\",\"gender\":\"性别呈现\",\"hair\":\"发型\",\"outfit\":\"服装\",\"props\":\"携带物品/特征\",\"emotion\":\"情绪基调\",\"performance\":\"表演风格\",\"notes\":\"备注\"}],\"sceneCards\":[{\"name\":\"场景名\",\"type\":\"室内|室外|走廊|车辆等\",\"lighting\":\"光线描述\",\"colorTone\":\"色调\",\"atmosphere\":\"氛围\",\"environment\":\"环境细节\",\"timeOfDay\":\"时段\",\"notes\":\"备注\"}],\"scenes\":[{\"key\":\"n0_s1\",\"storyNodeKey\":\"n0\",\"shotInNode\":1,\"shotsInNode\":shots_per_node,\"title\":\"...\",\"shot\":\"大全景|全景|中景|近景|特写\",\"duration\":8,\"action\":\"...\",\"dialogue\":\"...\",\"choices\":[{\"text\":\"...\",\"effect\":\"...\",\"targetKey\":\"n1_s1\"}],\"nextKey\":\"n0_s2\"}]}。key 必须唯一，nextKey 和 targetKey 必须指向 scenes 中存在的 key。每个分镜 action 只写一个不可再分的动作或表演节拍，避免把整个互动节点剧情塞进单镜；dialogue 只保留当前分镜实际说出的对白，单镜最长按 15 秒设计。如果已有角色卡，请保持角色身份一致并补充细节；如果暂无角色卡，请根据故事梗概创建所需角色。characters 数组中每个角色必须包含 name 字段，确保跨镜头角色外观连续。sceneCards 数组应列出本剧中出现的所有主要场景，每个场景卡必须包含 name 字段，其余字段描述该场景的固定视觉特征（光线、色调、氛围、环境、时段），用于跨镜头环境一致性。如果已有场景卡，请保持一致并补充细节；如果暂无场景卡，请根据剧情创建所需场景。",
    ].join("\n");
    return { system, user, story, expectedStoryNodes, expectedNodes };
  }

  function characterCardToText(card) {
    return [
      card.name, card.ageRange, card.gender, card.hair, card.outfit,
      card.props, card.emotion, card.performance, card.notes,
    ].filter(Boolean).join("，");
  }

  function serialUserPrompt(values) {
    const characterText = values.characters.length
      ? values.characters.map((card, index) => `\n  角色${index + 1}：${characterCardToText(card)}`).join("")
      : "暂无，请根据全剧梗概为本集创建所需角色卡";
    const sceneText = values.sceneCards.length
      ? values.sceneCards.map((card, index) => `\n  场景${index + 1}：${card.name}${card.type ? `（${card.type}）` : ""}${card.lighting ? `，光线：${card.lighting}` : ""}${card.atmosphere ? `，氛围：${card.atmosphere}` : ""}${card.environment ? `，环境：${card.environment}` : ""}${card.timeOfDay ? `，时段：${card.timeOfDay}` : ""}`).join("")
      : "暂无，请根据剧情为本集创建所需场景卡";
    return `你是一名专业短剧编剧。请为一部${toneLabels[values.serialTone] || "短剧"}创作第 1 集的分镜脚本，共 ${values.episodeShotCount} 个镜头。

【项目级设定】
片名：${values.title}
全剧梗概：${values.synopsis}
类型与基调：${values.genre} / ${values.serialTone}
已有角色卡：${characterText}
已有场景卡：${sceneText}
统一视觉风格：${values.visualStyle || "现代电影质感"}

【本集设定】
本集标题：${values.episodeTitle}
本集梗概：${values.episodeSynopsis || "根据全剧梗概推进"}
叙事目标：${values.episodeObjective || "推进主线与人物关系"}
开场钩子：${values.episodeHook || "前几个镜头迅速建立冲突"}
高潮与结尾：${values.episodeEnding || "形成高潮，并留下下一集悬念"}
上一集：无，这是开篇
下一集：第2集

返回严格的 JSON，格式如下（不要 markdown 围栏）：
{
  "startKey": "shot_1",
  "characters": [
    {
      "name": "角色名",
      "ageRange": "年龄段",
      "gender": "性别呈现",
      "hair": "发型",
      "outfit": "服装",
      "props": "携带物品/特征",
      "emotion": "情绪基调",
      "performance": "表演风格",
      "notes": "备注/补充"
    }
  ],
  "sceneCards": [
    {
      "name": "场景名",
      "type": "室内|室外|走廊|车辆等",
      "lighting": "光线描述",
      "colorTone": "色调",
      "atmosphere": "氛围",
      "environment": "环境细节",
      "timeOfDay": "时段",
      "notes": "备注/补充"
    }
  ],
  "scenes": [
    {
      "key": "shot_1",
      "episodeOrder": 1,
      "title": "开场钩子",
      "shot": "大全景",
      "duration": 8,
      "action": "场景描述与表演",
      "dialogue": "对白或旁白",
      "transition": "match",
      "entryState": "本镜开始时的人物姿势、视线、位置、道具与情绪",
      "exitState": "本镜结束时留给下一镜的人物姿势、视线、位置、道具与情绪",
      "nextKey": "shot_2"
    }
  ]
}

要求：
1. 严格返回 ${values.episodeShotCount} 个镜头，镜头之间线性连接，最后一个镜头 nextKey 为空字符串。
2. 先在内部把本集拆成 ${values.episodeShotCount} 个连续节拍，再逐镜输出；每个镜头只发生一个不可再分的事件或表演动作，禁止在任一 action 中复述本集梗概、叙事目标或完整结局。
3. 每镜 action 只描述该镜头可见的动作、表情、空间变化与即时结果，不写后续镜头内容，不使用“随后、接着、最终”等跨镜头概括。
4. dialogue 只包含当前镜头实际说出的对白或旁白，不得朗读 action 或剧情梗概。按每秒最多约 3 个中文字计算：4秒不超过7字、6秒不超过13字、8秒不超过19字、10秒不超过25字、12秒不超过31字、15秒不超过40字；需要更多对白时必须拆到后续镜头。
5. 人物身份、服装、地点状态和情绪在相邻镜头间连续，但连续性信息不得替代当前镜头事件。
6. 每镜必须给出 entryState 与 exitState；第 N 镜的 exitState 必须能直接成为第 N+1 镜的 entryState。保持人物屏幕方向、动作方向、视线、手中道具、环境光线和声音底噪连续。
7. transition 只能是 match、dissolve、cut、fade；同一场景连续动作优先 match，时间或地点轻微变化用 dissolve，强烈段落转换才用 cut 或 fade。
8. 如果已有角色卡，请保持角色身份一致并补充细节；如果暂无角色卡，请根据全剧梗概创建本集所需的所有角色。characters 数组中每个角色必须包含 name 字段，其余字段按需填写，确保跨镜头角色外观连续。
9. sceneCards 数组应列出本集出现的所有主要场景，每个场景卡必须包含 name 字段，其余字段描述该场景的固定视觉特征（光线、色调、氛围、环境、时段），用于跨镜头环境一致性。如果已有场景卡，请保持一致并补充细节；如果暂无场景卡，请根据剧情创建所需场景。`;
  }

  function serialPromptBundle(values) {
    return {
      system: "你是专业短剧编剧。必须只返回符合用户指定结构的 JSON，不要输出 Markdown 或解释。",
      user: serialUserPrompt(values),
    };
  }

  function promptViews(values) {
    if (state.mode === "interactive") {
      const bundle = interactivePromptBundle(values);
      const request = interactiveFrontendRequest(values);
      return {
        request: JSON.stringify(request, null, 2),
        system: bundle.system,
        user: bundle.user,
        model: [
          `POST ${values.textBaseUrl}/chat/completions`,
          "Authorization: Bearer <会话密钥或服务端环境密钥，仅在传输头中>",
          "",
          JSON.stringify({
            model: values.model,
            messages: [
              { role: "system", content: bundle.system },
              { role: "user", content: bundle.user },
            ],
            temperature: 0.7,
            max_tokens: 32767,
            stream: false,
          }, null, 2),
          "",
          "Narrative Forge 传输策略：read_timeout = 900 秒；max_attempts = 2。",
          "未配置：response_format、JSON Schema structured output、tool/function calling。",
        ].join("\n"),
        expectedStoryNodes: bundle.expectedStoryNodes,
        expectedNodes: bundle.expectedNodes,
      };
    }
    const bundle = serialPromptBundle(values);
    const request = {
      model: values.model,
      text_base_url: values.textBaseUrl,
      text_api_key: "",
      prompt: bundle.user,
    };
    return {
      request: JSON.stringify(request, null, 2),
      system: bundle.system,
      user: bundle.user,
      model: [
        `POST ${values.textBaseUrl}/chat/completions`,
        "Authorization: Bearer <会话密钥或服务端环境密钥，仅在传输头中>",
        "",
        JSON.stringify({
          model: values.model,
          messages: [
            { role: "system", content: bundle.system },
            { role: "user", content: bundle.user },
          ],
          stream: false,
          temperature: 0.8,
        }, null, 2),
        "",
        "Narrative Forge 传输策略：read_timeout = 900 秒；max_attempts = 2。",
        "短剧端点没有显式 max_tokens，也未配置 structured output 或工具调用。",
      ].join("\n"),
      expectedStoryNodes: null,
      expectedNodes: values.episodeShotCount,
    };
  }

  function renderSummary(values, views) {
    const summary = byId("promptSummary");
    summary.replaceChildren();
    const cells = state.mode === "interactive"
      ? [
        ["模式", "互动影游"],
        ["剧情节点", String(views.expectedStoryNodes)],
        ["目标分镜", String(views.expectedNodes)],
        ["名义结局", String(values.branchCount ** (values.treeDepth - 1))],
      ]
      : [
        ["模式", "AI 短剧"],
        ["当前集", "第 1 集"],
        ["目标分镜", String(values.episodeShotCount)],
        ["Prompt 所有者", "浏览器前端"],
      ];
    cells.forEach(([label, value]) => {
      const cell = document.createElement("div");
      cell.append(textElement("small", "", label), textElement("strong", "", value));
      summary.append(cell);
    });
  }

  function renderPromptWorkbench() {
    const values = formValues();
    const views = promptViews(values);
    renderSummary(values, views);
    byId("promptViewLabel").textContent = promptTabLabels[state.promptTab];
    byId("promptCode").textContent = views[state.promptTab];
    document.querySelectorAll("[data-prompt-tab]").forEach((button) => {
      const active = button.dataset.promptTab === state.promptTab;
      button.setAttribute("aria-selected", String(active));
      button.tabIndex = active ? 0 : -1;
      if (active) byId("promptPanel").setAttribute("aria-labelledby", button.id);
    });
    byId("copyStatus").textContent = state.mode === "interactive"
      ? "互动返回结构示例中的 shotsInNode 使用了未加引号的 literal shots_per_node；这段示例按源码原样保留，因此自身并不是合法 JSON。"
      : "短剧 user prompt 在浏览器中形成；后端只加固定 system message。密钥不进入 message content。";
  }

  function renderStages() {
    const lane = byId("pipelineLane");
    data.stages.forEach((stage, index) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = `pipeline-node${index === 0 ? " is-active" : ""}`;
      button.dataset.stageId = stage.id;
      button.setAttribute("aria-pressed", String(index === 0));
      button.append(textElement("span", "", stage.number), textElement("strong", "", stage.title));
      button.addEventListener("click", () => selectStage(stage.id));
      lane.append(button);
    });
    selectStage(data.stages[0].id);
  }

  function selectStage(stageId) {
    const stage = data.stages.find((item) => item.id === stageId) || data.stages[0];
    byId("stageNumber").textContent = stage.number;
    byId("stageSubtitle").textContent = stage.subtitle;
    byId("stageTitle").textContent = stage.title;
    byId("stageInput").textContent = stage.input;
    byId("stageAction").textContent = stage.action;
    byId("stageOutput").textContent = stage.output;
    byId("stageWarning").textContent = stage.warning;
    byId("stageSource").textContent = stage.source;
    document.querySelectorAll("[data-stage-id]").forEach((button) => {
      const active = button.dataset.stageId === stage.id;
      button.classList.toggle("is-active", active);
      button.setAttribute("aria-pressed", String(active));
    });
  }

  function cleanAssistantText(raw) {
    return String(raw)
      .replace(/<think>[\s\S]*?<\/think>/gi, "")
      .replace(/<think>[\s\S]*$/gi, "")
      .replace(/^```(?:json)?\s*/i, "")
      .replace(/\s*```$/i, "")
      .trim();
  }

  function extractFirstJsonObject(text) {
    const start = text.indexOf("{");
    if (start < 0) return text;
    let depth = 0;
    let inString = false;
    let escaped = false;
    for (let index = start; index < text.length; index += 1) {
      const character = text[index];
      if (inString) {
        if (escaped) escaped = false;
        else if (character === "\\") escaped = true;
        else if (character === "\"") inString = false;
        continue;
      }
      if (character === "\"") inString = true;
      else if (character === "{") depth += 1;
      else if (character === "}") {
        depth -= 1;
        if (depth === 0) return text.slice(start, index + 1);
      }
    }
    return text.slice(start);
  }

  function storyForScenario(scenario) {
    const story = clone(data.sampleStory);
    if (scenario === "duplicateKey") story.scenes[1].key = story.scenes[0].key;
    if (scenario === "badTarget") story.scenes[0].choices[0].targetKey = "missing_scene";
    if (scenario === "softMismatch") {
      story.scenes = story.scenes.filter((scene) => scene.key !== "n6_s1");
      story.scenes.find((scene) => scene.key === "n2_s1").choices[1].targetKey = "n5_s1";
      story.scenes[1].shot = "大特写";
      story.scenes[1].duration = 9;
      story.scenes[3].nextKey = "missing_scene";
    }
    return story;
  }

  function responsePipeline(scenario) {
    const story = storyForScenario(scenario);
    let content = JSON.stringify(story, null, 2);
    if (scenario === "thinkFence") {
      content = `<think>先规划七个节点，并检查分支。</think>\n\`\`\`json\n${content}\n\`\`\``;
    } else if (scenario === "invalidJson") {
      content = content.slice(0, Math.max(0, content.length - 190));
    }
    const envelope = {
      id: "chatcmpl_teaching_fixture",
      object: "chat.completion",
      model: "deepseek-v3",
      choices: [{ index: 0, message: { role: "assistant", content }, finish_reason: "stop" }],
      usage: { prompt_tokens: 2410, completion_tokens: 1860, total_tokens: 4270 },
    };
    const cleaned = cleanAssistantText(content);
    const jsonText = extractFirstJsonObject(cleaned);
    let parsed = null;
    let parseError = null;
    try {
      parsed = JSON.parse(jsonText);
    } catch (error) {
      parseError = "文本模型返回的剧情不是有效 JSON，请重试或更换文本模型。";
    }
    let installed = null;
    let installError = null;
    if (parsed) {
      try {
        installed = installTeachingStory(parsed, 7);
      } catch (error) {
        installError = error.message;
      }
    }
    return { envelope, content, cleaned, jsonText, parsed, parseError, installed, installError };
  }

  function installTeachingStory(generated, expectedCount) {
    if (!generated || !Array.isArray(generated.scenes) || !generated.scenes.length) {
      throw new Error("文本模型没有返回 scenes 数组。");
    }
    if (generated.scenes.length > 240) throw new Error("文本模型返回超过 240 个镜头，已拒绝导入。");
    const keys = new Set();
    generated.scenes.forEach((item, index) => {
      const key = String(item && item.key ? item.key : `n${index}`);
      if (keys.has(key)) throw new Error(`文本模型返回了重复的场景 key：${key}`);
      keys.add(key);
    });
    generated.scenes.forEach((item) => {
      (Array.isArray(item.choices) ? item.choices : []).forEach((choice) => {
        const targetKey = String(choice && choice.targetKey ? choice.targetKey : "");
        if (!targetKey || !keys.has(targetKey)) {
          throw new Error(`选项目标不存在：${targetKey || "（空）"}`);
        }
      });
    });
    const idByKey = new Map();
    generated.scenes.forEach((item, index) => {
      idByKey.set(String(item && item.key ? item.key : `n${index}`), `scene_docs_${String(index + 1).padStart(3, "0")}`);
    });
    const shots = new Set(["大全景", "全景", "中景", "近景", "特写"]);
    const durations = new Set([4, 6, 8, 10, 12, 15]);
    const scenes = generated.scenes.map((item, index) => {
      const key = String(item && item.key ? item.key : `n${index}`);
      const choices = (Array.isArray(item.choices) ? item.choices : []).map((choice, choiceIndex) => ({
        id: `choice_docs_${String(index + 1).padStart(3, "0")}_${choiceIndex + 1}`,
        text: String(choice.text || `选择 ${choiceIndex + 1}`).slice(0, 120),
        effect: String(choice.effect || "").slice(0, 240),
        targetSceneId: idByKey.get(String(choice.targetKey)) || "",
      }));
      return {
        id: idByKey.get(key),
        sourceKey: key,
        order: index,
        title: String(item.title || `剧情节点 ${index + 1}`).slice(0, 80),
        shot: shots.has(item.shot) ? item.shot : "中景",
        duration: durations.has(Number(item.duration)) ? Number(item.duration) : 8,
        action: String(item.action || "").slice(0, 6000),
        dialogue: String(item.dialogue || "").slice(0, 3000),
        choices,
        nextSceneId: idByKey.get(String(item.nextKey || "")) || "",
        isStart: String(generated.startKey || "") === key,
      };
    });
    if (!scenes.some((scene) => scene.isStart)) scenes[0].isStart = true;
    return {
      scenes,
      expectedCount,
      actualCount: scenes.length,
      warning: scenes.length === expectedCount
        ? ""
        : `期望 ${expectedCount} 镜，实际安装 ${scenes.length} 镜；运行时代码接受结果并显示提示。`,
    };
  }

  function setResponseStatus(kind, title, detail) {
    const status = byId("responseStatus");
    status.className = `response-status${kind ? ` is-${kind}` : ""}`;
    status.replaceChildren(textElement("strong", "", title), document.createTextNode(detail));
  }

  function renderCodeInto(container, text) {
    const pre = document.createElement("pre");
    const code = document.createElement("code");
    code.textContent = text;
    pre.append(code);
    container.append(pre);
  }

  function renderInstalledPreview(container, result) {
    const wrapper = document.createElement("div");
    wrapper.className = "installed-preview";
    const report = textElement("p", `install-report${result.warning ? " warning" : ""}`,
      result.warning || `安装通过：${result.actualCount} 个模型 key 已映射为内部 scene ID。`);
    const grid = document.createElement("div");
    grid.className = "installed-preview-grid";
    result.scenes.forEach((scene, index) => {
      const card = document.createElement("article");
      const flow = scene.choices.length
        ? `${scene.choices.length} 个选择`
        : (scene.nextSceneId ? "自动连接" : "结局");
      card.append(
        textElement("span", "", String(index + 1).padStart(2, "0")),
        textElement("strong", "", scene.title),
        textElement("small", "", `${scene.sourceKey} → ${scene.id}`),
        textElement("small", "", `${scene.shot} · ${scene.duration} 秒 · ${flow}`),
      );
      grid.append(card);
    });
    wrapper.append(report, grid);
    container.append(wrapper);
  }

  function renderUiPreview(container, result) {
    const wrapper = document.createElement("div");
    wrapper.className = "ui-preview";
    const reportText = result.warning
      ? `${result.warning} 下方列表只显示规范化后的项目状态。`
      : "教学构造已通过安装器。下方是 renderSceneList() 所消费字段的近似视觉投影。";
    wrapper.append(textElement("p", `install-report${result.warning ? " warning" : ""}`, reportText));
    const list = document.createElement("div");
    list.className = "ui-scene-list";
    result.scenes.forEach((scene, index) => {
      const item = document.createElement("article");
      item.className = `ui-scene-item${scene.isStart ? " is-start" : ""}`;
      const details = document.createElement("div");
      details.append(
        textElement("strong", "", scene.title),
        textElement("small", "", `${scene.shot} · ${scene.duration} 秒${scene.isStart ? " · 起点" : ""}`),
      );
      const flow = scene.choices.length
        ? `${scene.choices.length} 个选择`
        : (scene.nextSceneId ? "自动连接" : "结局");
      item.append(
        textElement("span", "", String(index + 1).padStart(2, "0")),
        details,
        textElement("small", "ui-flow-label", flow),
      );
      list.append(item);
    });
    wrapper.append(list);
    container.append(wrapper);
  }

  function renderResponseLab() {
    const result = responsePipeline(state.responseScenario);
    const view = byId("responseView");
    view.replaceChildren();
    const fixtureNote = "教学构造；不是仓库保存的模型原始响应。";
    if (state.responseStep === "envelope") {
      setResponseStatus("", "供应商响应 envelope", `后端原样转发给浏览器。${fixtureNote}`);
      renderCodeInto(view, JSON.stringify(result.envelope, null, 2));
      return;
    }
    if (state.responseStep === "content") {
      setResponseStatus("", "已提取 message.content", `只读取 choices[0].message.content。${fixtureNote}`);
      renderCodeInto(view, result.content);
      return;
    }
    if (state.responseStep === "cleaned") {
      setResponseStatus("", "有限清洗完成", "think 与外层围栏被删除；下一步只保留首个平衡 JSON 对象。");
      renderCodeInto(view, result.jsonText);
      return;
    }
    if (state.responseStep === "parsed") {
      if (result.parseError) {
        setResponseStatus("error", "JSON.parse 失败", result.parseError);
        renderCodeInto(view, `${result.parseError}\n\n解析器收到的文本：\n${result.jsonText}`);
      } else {
        setResponseStatus("warning", "JSON.parse 通过", "语法正确还不等于满足 scenes、key、连接或树形契约。");
        renderCodeInto(view, JSON.stringify(result.parsed, null, 2));
      }
      return;
    }
    if (state.responseStep === "installed") {
      if (result.parseError || result.installError) {
        const message = result.parseError || result.installError;
        setResponseStatus("error", "安装停止", message);
        renderCodeInto(view, `结果未写入 project.scenes。\n旧分镜继续保留。\n\n原因：${message}`);
      } else {
        setResponseStatus(result.installed.warning ? "warning" : "", "安装完成",
          result.installed.warning || "枚举、长度、连接和内部 ID 已按接收契约规范化。");
        renderInstalledPreview(view, result.installed);
      }
      return;
    }
    if (result.parseError || result.installError) {
      const message = result.parseError || result.installError;
      setResponseStatus("error", "没有新列表", "解析或安装失败，因此 renderSceneList() 不会看到新状态。");
      renderCodeInto(view, `分镜列表保持原状。\n\n失败原因：${message}`);
    } else {
      setResponseStatus(result.installed.warning ? "warning" : "", "分镜列表已重绘",
        result.installed.warning ? "宽松接收的结构也会成为可见列表。" : "UI 读取的是安装后的 scene，而非原始模型 key。" );
      renderUiPreview(view, result.installed);
    }
  }

  function mediaPrompts(values) {
    const scene = data.sampleStory.scenes[0];
    const character = data.sampleStory.characters[0];
    const place = data.sampleStory.sceneCards[0];
    const characterText = characterCardToText(character);
    const placeParts = [
      place.lighting ? `光照：${place.lighting}` : "",
      place.colorTone ? `色调：${place.colorTone}` : "",
      place.atmosphere ? `氛围：${place.atmosphere}` : "",
      place.environment ? `环境：${place.environment}` : "",
    ].filter(Boolean).join("，");
    const modeLabel = state.mode === "serial" ? "AI短剧" : `${values.genre}互动影游`;
    const imageLines = [
      `${modeLabel}的电影关键帧，${scene.shot}。`,
      state.mode === "serial" ? "这是当前视频的起始帧，人物、视线、位置、道具和环境必须准确处于入口状态：从稳定定场状态开始。" : "",
      `当前镜头唯一事件与表演：${scene.action}。`,
      `角色连续性设定：${characterText}。同一镜头内严格保持角色外观、发型、服装与道具一致。`,
      `场景连续性设定：${place.name}。${placeParts}。同一镜头内严格保持场景光照、色调和环境一致。`,
      values.visualStyle ? `视觉风格：${values.visualStyle}。` : "",
      `只表现当前镜头，不概括、不预演本集其他情节。构图适合${values.aspectRatio}画幅，电影灯光，无文字、无水印、无界面元素。`,
    ].filter(Boolean);
    const exitState = `${scene.action}；结尾保持可衔接的姿势与视线。`;
    const camera = `${scene.shot}电影镜头。 保持首帧人物身份、脸部、服装和场景结构一致。 自然呼吸与细微环境动态，运动连贯，镜头稳定，避免形体变形、闪烁、跳切和新增角色。`;
    const narrative = [
      "【当前镜头】",
      state.mode === "serial" ? "衔接方式：硬切。" : "",
      state.mode === "serial" ? "开头入口状态：从稳定定场状态开始。" : "",
      `本镜头唯一事件与表演：${scene.action}`,
      `本镜头对白 / 旁白：${scene.dialogue}`,
      state.mode === "serial" ? `结尾出口状态：${exitState}` : "",
      `时长：${scene.duration} 秒。对白必须在该时长内以自然、清晰、可听懂的语速完成，并保留必要停顿。`,
      state.mode === "serial" ? "开头约 0.3 秒准确保持入口状态，再自然开始动作；结尾约 0.3 秒收束到出口状态并稳定停留，期间避免新增动作或台词，为下一镜转场预留余量。" : "",
      "只执行上述一个镜头事件，不总结、不预演、不补演本集其他情节，不朗读剧情描述。动作、表情、视线和口型仅服务于当前对白；保持人物运动方向、屏幕方位和环境光线连续。画面不显示字幕或文字。",
      "【/当前镜头】",
    ].filter(Boolean).join("\n");
    return { image: imageLines.join("\n"), video: `${camera}\n\n${narrative}` };
  }

  function renderMediaPrompt() {
    const prompts = mediaPrompts(formValues());
    byId("mediaPromptCode").textContent = prompts[state.mediaTab];
    document.querySelectorAll("[data-media-tab]").forEach((button) => {
      const active = button.dataset.mediaTab === state.mediaTab;
      button.setAttribute("aria-selected", String(active));
      button.tabIndex = active ? 0 : -1;
      if (active) byId("mediaPromptPanel").setAttribute("aria-labelledby", button.id);
    });
  }

  function bindTabKeyboard(tabList, selector) {
    tabList.addEventListener("keydown", (event) => {
      if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) return;
      const tabs = Array.from(tabList.querySelectorAll(selector));
      const currentIndex = Math.max(0, tabs.indexOf(document.activeElement));
      let targetIndex = currentIndex;
      if (event.key === "ArrowLeft") targetIndex = (currentIndex - 1 + tabs.length) % tabs.length;
      if (event.key === "ArrowRight") targetIndex = (currentIndex + 1) % tabs.length;
      if (event.key === "Home") targetIndex = 0;
      if (event.key === "End") targetIndex = tabs.length - 1;
      event.preventDefault();
      tabs[targetIndex].focus();
      tabs[targetIndex].click();
    });
  }

  async function copyCurrentPrompt() {
    const content = byId("promptCode").textContent;
    try {
      if (navigator.clipboard && window.isSecureContext) {
        await navigator.clipboard.writeText(content);
      } else {
        const textarea = document.createElement("textarea");
        textarea.value = content;
        textarea.setAttribute("readonly", "");
        textarea.style.position = "fixed";
        textarea.style.opacity = "0";
        document.body.append(textarea);
        textarea.select();
        document.execCommand("copy");
        textarea.remove();
      }
      byId("copyStatus").textContent = "已复制当前教学视图；其中不含真实 API Key。";
    } catch (error) {
      byId("copyStatus").textContent = "浏览器阻止了剪贴板访问；可直接在代码区全选复制。";
    }
  }

  function bindEvents() {
    document.querySelectorAll("[data-mode]").forEach((button) => {
      button.addEventListener("click", () => setMode(button.dataset.mode));
    });
    document.querySelectorAll("[data-preset]").forEach((button) => {
      button.addEventListener("click", () => applyPreset(button.dataset.preset));
    });
    byId("restorePreset").addEventListener("click", () => applyPreset(state.preset));
    byId("promptControls").addEventListener("input", () => {
      renderPromptWorkbench();
      renderMediaPrompt();
    });
    byId("promptControls").addEventListener("change", () => {
      renderPromptWorkbench();
      renderMediaPrompt();
    });
    document.querySelectorAll("[data-prompt-tab]").forEach((button) => {
      button.addEventListener("click", () => {
        state.promptTab = button.dataset.promptTab;
        renderPromptWorkbench();
      });
    });
    byId("copyPrompt").addEventListener("click", copyCurrentPrompt);
    byId("responseScenario").addEventListener("change", (event) => {
      state.responseScenario = event.target.value;
      renderResponseLab();
    });
    document.querySelectorAll("[data-response-step]").forEach((button) => {
      button.addEventListener("click", () => {
        state.responseStep = button.dataset.responseStep;
        document.querySelectorAll("[data-response-step]").forEach((candidate) => {
          const active = candidate.dataset.responseStep === state.responseStep;
          candidate.classList.toggle("is-active", active);
          candidate.setAttribute("aria-pressed", String(active));
        });
        renderResponseLab();
      });
    });
    document.querySelectorAll("[data-media-tab]").forEach((button) => {
      button.addEventListener("click", () => {
        state.mediaTab = button.dataset.mediaTab;
        renderMediaPrompt();
      });
    });
    bindTabKeyboard(document.querySelector(".tab-list[role='tablist']"), "[role='tab']");
    bindTabKeyboard(document.querySelector(".media-output-tabs [role='tablist']"), "[role='tab']");
  }

  renderStages();
  bindEvents();
  applyPreset("defaults");
  renderResponseLab();
  renderMediaPrompt();
  document.body.dataset.labReady = "true";
}());
