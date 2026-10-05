import { useState } from "react";
import type { ProjectBrief, StoryBible, StoryGraph } from "../types";
import { Button, Field, PageHeader, Panel } from "../components";
import { DirectionPresets, genreGroups, visualGroups } from "./DirectionPresets";
import { ContextHelp, ContextHelpGroup } from "../components/ContextHelp";
import { StageGuide } from "../components/StageGuide";

type BriefPageProps = {
  value: ProjectBrief;
  hasSavedProject: boolean;
  saving: boolean;
  readOnly?: boolean;
  onSave: (brief: ProjectBrief) => Promise<unknown>;
  onSaveAndContinue: (brief: ProjectBrief) => Promise<void>;
  onContinueToSource?: () => void;
  onDraftChange?: (brief: ProjectBrief) => void;
  bible?: StoryBible;
  graph?: StoryGraph;
  proposalRunning?: boolean;
  proposalReady?: boolean;
  storyboardRunning?: boolean;
  onGenerateProposal?: (brief: ProjectBrief) => Promise<void>;
  onGenerateStoryboard?: () => Promise<void>;
  onReviewStage?: (stage: "bible" | "graph") => void;
  onContinueToPlanning?: () => void;
};

const defaultWorkingTitle = "未命名故事";

/**
 * The brief remains the canonical input. This page only composes its first two
 * canonical downstream stages into a review; it does not own proposal state.
 */
export function BriefPage({ value, hasSavedProject, saving, readOnly = false, onSave, onSaveAndContinue, onContinueToSource, onDraftChange, bible, graph, proposalRunning = false, proposalReady = true, storyboardRunning = false, onGenerateProposal, onGenerateStoryboard, onReviewStage, onContinueToPlanning }: BriefPageProps) {
  const [draft, setDraft] = useState(value);
  const set = <K extends keyof ProjectBrief>(key: K, next: ProjectBrief[K]) => setDraft((current) => {
    const updated = { ...current, [key]: next };
    onDraftChange?.(updated); return updated;
  });
  const numeric = <K extends keyof ProjectBrief>(key: K, raw: string) => set(key, Number(raw) as ProjectBrief[K]);
  const canonicalDraft = (): ProjectBrief => ({ ...draft, title: draft.title.trim() || defaultWorkingTitle });
  const validDuration = Number.isInteger(draft.targetPlaythroughSeconds) && draft.targetPlaythroughSeconds >= 3;
  const canSave = !readOnly && !saving && Boolean(draft.synopsis.trim()) && validDuration;
  const saveHint = readOnly ? "项目当前只读，无法保存修改。" : saving ? "正在保存，请稍候。" : !draft.synopsis.trim() ? "填写故事梗概后即可保存；片名可稍后补充。" : !validDuration ? "目标游玩时长需填写至少 3 秒的整数。" : hasSavedProject ? "保存修改不会覆盖已确认的来源内容。" : "保存后进入来源与大纲，继续完善故事内容。";
  const hasProposal = Boolean(bible?.logline && graph?.nodes.length);
  const decisions = graph?.nodes.filter((node) => node.kind === "decision") || [];
  const endings = graph?.nodes.filter((node) => node.kind === "ending") || [];
  const graphNodes = new Map(graph?.nodes.map((node) => [node.id, node]) || []);
  const choiceEdges = (graph?.edges || []).filter((edge) => edge.kind === "choice");
  const choiceSources = (graph?.nodes || []).filter((node) => choiceEdges.some((edge) => edge.sourceNodeId === node.id));
  const choicesFor = (nodeId: string) => choiceEdges.filter((edge) => edge.sourceNodeId === nodeId);
  return <div className="page">
    <PageHeader title="项目简报" description={hasSavedProject ? "修改项目的创作目标；保存后留在本页，已有来源不会被覆盖。" : "先写一个梗概，再进入来源与大纲。保存不会自动生成或确认故事内容。"} actions={<div className="page-action-group">
      {hasSavedProject
        ? <Button variant="primary" busy={saving} disabled={!canSave} aria-describedby="brief-save-hint" onClick={() => void onSave(canonicalDraft())}>{saving ? "保存中…" : "保存修改"}</Button>
        : <Button variant="primary" busy={saving} disabled={!canSave} aria-describedby="brief-save-hint" onClick={() => void onSaveAndContinue(canonicalDraft())}>{saving ? "保存中…" : "保存并继续到来源"}</Button>}
      <p id="brief-save-hint" className="action-prerequisite">{saveHint}</p>
      {hasSavedProject && onContinueToSource && <Button variant="quiet" disabled={saving} onClick={onContinueToSource}>返回来源与大纲</Button>}
    </div>} />
    <StageGuide title={hasSavedProject ? "修改当前项目的创作设置" : "从故事想法开始"}>{hasSavedProject ? "修改结构后，已保存的分支及后续内容需要重新检查；旧内容与媒体仍保留。新任务必须使用当前设置，不会自动重建或替换已安装投产。来源正文独立保存，不随简报梗概改写。" : "写清主角、处境和观众要做的选择。剧情结构与分镜设置可保留默认值，后续仍可调整。"}</StageGuide>
    <div className="two-column wide-left brief-layout">
      <Panel className="form-card">
        <div className="section-title"><strong>故事想法</strong><p className="required-legend">* 为必填项；其他信息可稍后完善。</p></div>
        <Field label="片名"><input placeholder={defaultWorkingTitle} value={draft.title} onChange={(event) => set("title", event.target.value)} /><small>可选工作片名；留空时保存为“未命名故事”。</small></Field>
        <Field label="故事梗概" required><textarea aria-required="true" rows={5} placeholder="主角遇到了什么？观众可以替主角做什么选择？不同选择会带来怎样的结局？" value={draft.synopsis} onChange={(event) => set("synopsis", event.target.value)} /></Field>
        <DirectionPresets label="类型" groups={genreGroups} selections={draft.genreSelections || []} detail={draft.genre || ""} disabled={readOnly || saving} onSelections={value => set("genreSelections", value)} onDetail={value => set("genre", value)} />
        <DirectionPresets label="视觉风格" groups={visualGroups} selections={draft.visualStyleSelections || []} detail={draft.visualStyle || ""} disabled={readOnly || saving} onSelections={value => set("visualStyleSelections", value)} onDetail={value => set("visualStyle", value)} />
        <div className="field-grid three">
          <Field label="语言"><select value={draft.language} onChange={(event) => set("language", event.target.value)}><option value="zh-CN">简体中文</option><option value="en-US">English</option></select></Field>
          <Field label="画幅"><select value={draft.aspectRatio} onChange={(event) => set("aspectRatio", event.target.value)}><option>16:9</option><option>9:16</option><option>1:1</option></select></Field>
          <Field label="目标游玩时长（秒）" required><input aria-required="true" type="number" min={3} value={draft.targetPlaythroughSeconds} onChange={(event) => numeric("targetPlaythroughSeconds", event.target.value)} /><small>至少 3 秒；这是创作目标，不是最终播放时长的承诺。</small></Field>
        </div>
      </Panel>
      <div className="stack">
        <Panel className="form-card">
          <details open>
            <summary>剧情结构与分镜</summary>
            <p className="action-prerequisite">这些设置决定完整播放路线的结构。系统先检查可行性，再由助手填入剧情；无法实现的组合会说明原因，不会静默修改设置。镜头偏好用于后续分镜。</p>
          <ContextHelpGroup><div className="field-grid two">
            <div className="structural-setting"><div><span>每次完整播放的选择次数</span><ContextHelp label="每次完整播放的选择次数">观众从开场看到结局，途中需要做几次选择；不是每次选择的选项数量。</ContextHelp></div><input aria-label="每次完整播放的选择次数" disabled={readOnly || saving} type="number" min={0} value={draft.decisionPointsPerPath} onChange={event => numeric("decisionPointsPerPath", event.target.value)} /></div>
            <div className="structural-setting"><div><span>不同结局的数量</span><ContextHelp label="不同结局的数量">故事包含多少个不同结局；多条播放路线可以通往同一个结局。</ContextHelp></div><input aria-label="不同结局的数量" disabled={readOnly || saving} type="number" min={1} value={draft.endingCount} onChange={event => numeric("endingCount", event.target.value)} /></div>
            <div className="structural-setting"><div><span>剧情节点数量上限</span><ContextHelp label="剧情节点数量上限">整个故事可使用多少个剧情节点，包括开场、发展、选择、汇合和结局；不是分镜镜头数量。</ContextHelp></div><input aria-label="剧情节点数量上限" disabled={readOnly || saving} type="number" min={1} value={draft.nodeBudget} onChange={event => numeric("nodeBudget", event.target.value)} /></div>
            <div className="structural-setting"><div><span>每次选择的最多选项数</span><ContextHelp label="每次选择的最多选项数">一个选择点最多可以提供几个选项；不是完整播放路线的总数。</ContextHelp></div><input aria-label="每次选择的最多选项数" disabled={readOnly || saving} type="number" min={1} max={6} value={draft.maxOutDegree} onChange={event => numeric("maxOutDegree", event.target.value)} /></div>
            <div className="structural-setting"><div><span>分支汇合次数</span><ContextHelp label="分支汇合次数">整个故事安排多少个汇合点；分开的播放路线在此汇合，之后共用后续剧情。</ContextHelp></div><input aria-label="分支汇合次数" disabled={readOnly || saving} type="number" min={0} value={draft.desiredJoinCount} onChange={event => numeric("desiredJoinCount", event.target.value)} /></div>
          </div></ContextHelpGroup>
          <div className="range-summary"><span>每场分镜</span><strong>{draft.shotsPerSceneMin}–{draft.shotsPerSceneMax}</strong></div>
          <div className="field-grid two compact">
            <Field label="最少"><input type="number" min={1} value={draft.shotsPerSceneMin} onChange={(event) => numeric("shotsPerSceneMin", event.target.value)} /></Field>
            <Field label="最多"><input type="number" min={draft.shotsPerSceneMin} value={draft.shotsPerSceneMax} onChange={(event) => numeric("shotsPerSceneMax", event.target.value)} /></Field>
          </div>
          <Field label="镜头数量规则"><select value={draft.shotCountPolicy} onChange={(event) => set("shotCountPolicy", event.target.value as ProjectBrief["shotCountPolicy"])}><option value="advisory">创作建议（超出时提示）</option><option value="strict">严格限制（超出时阻止确认）</option></select><small>这只控制每场镜头数量；镜头时长、资源与供应商能力限制仍须满足。</small></Field>
          </details>
        </Panel>
      </div>
    </div>
    {onGenerateProposal && <Panel className="brief-alternate-workflow"><details><summary>其他工作流：旧版故事提案</summary><p>{hasSavedProject ? "直接从简报生成故事设定与分支图。通常请从左侧“来源与大纲”开始，逐步审阅并确认。" : "直接从简报生成故事设定与分支图。通常请先使用上方“保存并继续到来源”，逐步审阅并确认。"}</p><Button variant="quiet" busy={proposalRunning} disabled={!canSave || proposalRunning} onClick={() => void onGenerateProposal(canonicalDraft())}>{proposalRunning ? "正在生成提案…" : "生成故事提案"}</Button>{!canSave && <p className="action-prerequisite">{saveHint}</p>}</details></Panel>}
    {hasProposal && bible && graph && <div className="stack proposal-review" data-testid="story-proposal-review">
      <Panel>
        <div className="section-title"><span>待审阅的故事提案</span><strong>{bible.logline}</strong></div>
        <p>{bible.premise}</p>
        <div className="field-grid two">
          <div><strong>人物</strong><ul>{bible.characters.map((character) => <li key={character.id}>{character.name}{character.role ? ` · ${character.role}` : ""}{character.goal ? `：${character.goal}` : ""}</li>)}</ul></div>
          <div><strong>设定</strong><ul>{bible.locations.map((location) => <li key={location.id}>{location.name}{location.description ? `：${location.description}` : ""}</li>)}</ul></div>
        </div>
      </Panel>
      <Panel>
        <div className="section-title"><span>分支与结局</span><strong>{decisions.length} 个选择点 · {endings.length} 个结局</strong></div>
        {choiceSources.length ? <ul>{choiceSources.map((node) => <li key={node.id}><strong>{node.title}</strong>：{node.summary}<ul>{choicesFor(node.id).map((edge) => { const target = graphNodes.get(edge.targetNodeId); return <li key={edge.id}><strong>{edge.choiceText || "未命名选择"}</strong> → {target?.kind === "ending" ? "结局：" : "节点："}<strong>{target?.title || edge.targetNodeId}</strong>{target?.summary ? `：${target.summary}` : ""}</li>; })}</ul></li>)}</ul> : <p>此提案尚未定义选择节点。</p>}
        {endings.length ? <ul>{endings.map((node) => <li key={node.id}><strong>{node.title}</strong>：{node.summary}</li>)}</ul> : <p>此提案尚未定义结局。</p>}
      </Panel>
      <Panel>
        <div className="section-title"><span>后续创作</span><strong>故事设定与分支图</strong></div>
        <p>已推导：{graph.nodes.length} 个叙事节点、{graph.edges.filter((edge) => edge.kind === "choice").length} 个选择、{endings.length} 个结局。场景与分镜仅在下方明确请求后生成；媒体不在本步骤内。</p>
        <p>计划目标：每条路径约 {draft.targetPlaythroughSeconds} 秒、每场偏好 {draft.shotsPerSceneMin}–{draft.shotsPerSceneMax} 个镜头（{draft.shotCountPolicy === "strict" ? "严格限制" : "超出时提示"}）；这些不是成本或实际时长估算。</p>
        {!proposalReady && <p className="event-detail">提案的上游内容已变更。请重新生成故事设定与分支图后，再进入分镜规划；不会覆盖任何下游内容。</p>}
        <div className="button-row"><Button variant="quiet" onClick={() => onReviewStage?.("bible")}>细化人物与设定</Button><Button variant="quiet" onClick={() => onReviewStage?.("graph")}>细化分支与结局</Button>{onContinueToPlanning && <Button variant="quiet" disabled={!proposalReady} onClick={onContinueToPlanning}>进入场景编辑</Button>}{onGenerateStoryboard && <Button variant="primary" busy={storyboardRunning} disabled={readOnly || !proposalReady || saving || storyboardRunning} onClick={() => void onGenerateStoryboard()}>{storyboardRunning ? "正在生成场景与分镜…" : "生成可编辑场景与分镜"}</Button>}</div>
      </Panel>
    </div>}
  </div>;
}
