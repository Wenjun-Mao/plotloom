import { useState } from "react";

const labels: Record<string, string> = {
  source: "故事标题", lang: "语言", params: "上游组织参数", adaptation: "改编说明",
  characters: "角色", scenes: "场景", props: "道具", beats: "叙事节拍", episodes: "结构条目",
  episodesCount: "上游条目数量", minutesPerEpisode: "每条目标时长（分钟）",
  genre: "类型", adaptMode: "改编方式", preferences: "创作偏好", core: "故事核心",
  keep: "保留内容", cut: "删减内容", merge: "合并内容", risks: "风险与处理",
  cutNote: "删减说明", mergeNote: "合并说明", what: "内容", why: "原因", evidence: "依据",
  plan: "处理方案", id: "标识", name: "名称", role: "角色定位", tier: "角色层级",
  arc: "人物变化", from: "来源依据", primary: "主要场景", reusePlan: "复用说明",
  function: "作用", beatIds: "关联节拍", type: "节拍类型", weight: "权重",
  episode: "所属结构条目", ep: "条目编号", setup: "铺垫", payoff: "结果",
  synopsis: "内容梗概", hook: "吸引点", suspense: "悬念说明", sceneIds: "关联场景",
  characterIds: "关联角色", propIds: "关联道具", warnings: "制作提示",
};

function fieldLabel(key: string, parent?: string) {
  return key === "episodes" && parent === "params" ? labels.episodesCount : labels[key] || key;
}

/** Render data as escaped React text; never execute the specialist's report HTML. */
function Value({ value, parent }: { value: unknown; parent?: string }) {
  if (value === null || value === undefined || value === "") return <span className="muted">未提供</span>;
  if (Array.isArray(value)) return value.length
    ? <ol className="outline-reader-list">{value.map((item, index) => <li key={index}><Value value={item} parent={parent} /></li>)}</ol>
    : <span className="muted">无</span>;
  if (typeof value === "object") return <dl className="outline-reader-fields">{Object.entries(value).map(([key, item]) => <div key={key}><dt>{fieldLabel(key, parent)}</dt><dd><Value value={item} parent={key} /></dd></div>)}</dl>;
  return <span>{typeof value === "boolean" ? value ? "是" : "否" : String(value)}</span>;
}

function record(value: unknown): Record<string, unknown> {
  return value !== null && typeof value === "object" && !Array.isArray(value) ? value as Record<string, unknown> : {};
}

export function OutlineReader({ outline }: { outline: Record<string, unknown> }) {
  const [beatView, setBeatView] = useState<"overview" | "table">("overview");
  const beats = Array.isArray(outline.beats) ? outline.beats : [];
  return <div className="outline-reader">
    <h3>{typeof outline.source === "string" ? outline.source : "候选大纲"}</h3>
    <p role="note" className="notice">以下按上游大纲的结构条目展示。“条目”不是已确认的成片集数；条目编号也不等于分支或结局数。每条时长是上游目标，不能直接相加作为单条播放路线的时长。最终形式与分支仍需审核确认。</p>
    {Object.entries(outline).filter(([key]) => key !== "source").map(([key, value]) => <section key={key} className="outline-reader-section">
      <h4>{fieldLabel(key)}</h4>
      {key === "beats" && Array.isArray(value) ? <>
        <div className="outline-reader-switch" role="group" aria-label="节拍展示方式">
          <button type="button" className="button" aria-pressed={beatView === "overview"} onClick={() => setBeatView("overview")}>顺序概览</button>
          <button type="button" className="button" aria-pressed={beatView === "table"} onClick={() => setBeatView("table")}>明细表</button>
        </div>
        <p className="muted">保留候选中的记录顺序；不是播放时间轴，互斥分支不代表连续播放。</p>
        {beatView === "overview" ? <Value value={beats} /> : <div className="outline-reader-table"><table>
          <caption>叙事节拍明细</caption>
          <thead><tr><th scope="col">节拍</th><th scope="col">所属结构条目</th><th scope="col">完整内容</th></tr></thead>
          <tbody>{beats.map((beat, index) => { const entry = record(beat); return <tr key={index}><th scope="row"><Value value={entry.id} /></th><td><Value value={entry.episode} /></td><td><Value value={beat} /></td></tr>; })}</tbody>
        </table>{!beats.length && <p>尚无节拍。</p>}</div>}
      </> : <Value value={value} parent={key} />}
    </section>)}
  </div>;
}
