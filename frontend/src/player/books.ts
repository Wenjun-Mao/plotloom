import type { Archive } from "./archive";
import type { Story } from "./state";

type EvidenceEntry = { id: string; title: string; detail: string; source: string; revealedBy: string[]; revealWhen: "entered" | "completed" };

// These authored notes are deliberately keyed to encountered beats. The player
// engine does not infer facts from node IDs or expose material from future paths.
const evidence: EvidenceEntry[] = [
  { id: "card", title: "未登记的监控卡", detail: "卡片没有出现在正式交接清单里。它被放在交接物中，阿岚在许微打开之前按住了她的手。", source: "开袋时发现", revealedBy: ["opening"], revealWhen: "entered" },
  { id: "recording", title: "火灾当晚的监控", detail: "监控画面记录到阿岚碰倒电暖器。画面能留下动作，不能替任何人解释之后半年的沉默。", source: "看完监控", revealedBy: ["watch-memory", "watch-second", "hear-second"], revealWhen: "completed" },
  { id: "admission", title: "阿岚承认碰倒电暖器", detail: "她说那晚自己碰倒了电暖器，以为火已经灭了。", source: "阿岚开口", revealedBy: ["hear-confession", "watch-second"], revealWhen: "completed" },
  { id: "hidden-card", title: "藏卡半年", detail: "阿岚承认把监控卡藏了半年；这段时间许微因事故被调离放映岗。", source: "半年沉默的谈话", revealedBy: ["watch-admission", "hear-admission"], revealWhen: "completed" },
  { id: "correction", title: "更正说明", detail: "明早新馆主接收档案。把卡和更正说明放进交接袋，会让事故经过进入正式记录。", source: "听到交接安排", revealedBy: ["watch-admission", "hear-admission"], revealWhen: "completed" },
  { id: "signature", title: "阿岚愿意签名", detail: "阿岚表示愿意在说明上签名，并知道自己的名字也会留在记录里。", source: "听完解释", revealedBy: ["watch-n10", "hear-n10"], revealWhen: "completed" },
];

export type Knowledge = { revision: string; entered: string[]; completed: string[] };

export function readKnowledge(story: Story, raw: unknown): Knowledge {
  const empty: Knowledge = { revision: story.storyRevision, entered: [], completed: [] };
  if (!raw || typeof raw !== "object") return empty;
  const value = raw as Knowledge;
  if (value.revision !== story.storyRevision || !Array.isArray(value.entered) || !Array.isArray(value.completed)) return empty;
  const ids = new Set(story.nodes.map(node => node.id));
  return { revision: story.storyRevision,
    entered: [...new Set(value.entered.filter((id): id is string => typeof id === "string" && ids.has(id)))],
    completed: [...new Set(value.completed.filter((id): id is string => typeof id === "string" && ids.has(id)))] };
}

export function recordKnowledge(knowledge: Knowledge, nodeId: string, completed = false): Knowledge {
  return { ...knowledge,
    entered: knowledge.entered.includes(nodeId) ? knowledge.entered : [...knowledge.entered, nodeId],
    completed: completed && !knowledge.completed.includes(nodeId) ? [...knowledge.completed, nodeId] : knowledge.completed };
}

function el<K extends keyof HTMLElementTagNameMap>(tag: K, text = "", className = "") {
  const item = document.createElement(tag); item.textContent = text; if (className) item.className = className; return item;
}
function button(text: string, action: () => void) {
  const item = el("button", text); item.type = "button"; item.onclick = action; return item;
}

export function buildEvidenceBook(story: Story, enteredIds: string[], completedIds: string[]) {
  const panel = el("section", "", "book-panel evidence-book");
  panel.setAttribute("aria-labelledby", "book-title");
  panel.append(el("p", "放映室 · 物证册", "eyebrow"));
  const title = el("h2", "物证册"); title.id = "book-title"; panel.append(title);
  panel.append(el("p", "只收录你已经亲眼看过或亲耳听到的内容。", "book-intro"));
  const entered = new Set(enteredIds);
  const completed = new Set(completedIds);
  const available = evidence.filter(item => item.revealedBy.some(id => (item.revealWhen === "entered" ? entered : completed).has(id)));
  if (!available.length) panel.append(el("p", "这里还没有新记录。继续放映后，已遇见的线索会收进册中。", "book-empty"));
  for (const item of available) {
    const card = el("article", "", "evidence-card");
    card.append(el("h3", item.title), el("p", item.detail), el("small", `来源 · ${item.source}`));
    panel.append(card);
  }
  return panel;
}

export function buildHandoverBook(story: Story, archive: Archive, currentPath: string[], onFork: (path: string[]) => void) {
  const panel = el("section", "", "book-panel handover-book");
  panel.setAttribute("aria-labelledby", "book-title");
  panel.append(el("p", "放映室 · 路线记录", "eyebrow"));
  const title = el("h2", "交接簿"); title.id = "book-title"; panel.append(title);
  const routes = archive.routes;
  const known = [currentPath];
  const choices = known.flatMap(path => path.slice(0, -1).flatMap((id, index) => {
    const node = story.nodes.find(item => item.id === id);
    const edge = node?.edges.find(item => item.to === path[index + 1]);
    return edge?.label ? [{ title: node?.question || node?.title || "选择", label: edge.label }] : [];
  }));
  panel.append(el("h3", `本轮选择 · ${choices.length}`));
  if (!choices.length) panel.append(el("p", "选择会随着放映记在这里。", "book-empty"));
  for (const choice of choices) panel.append(el("p", `${choice.title}　›　${choice.label}`, "handover-choice"));
  panel.append(el("h3", `已归档路线 · ${routes.length}`));
  if (!routes.length) panel.append(el("p", "抵达结局后，路线会留在这里。", "book-empty"));
  for (const [index, route] of routes.entries()) {
    const ending = story.nodes.find(node => node.id === route.ending)?.ending;
    const row = el("article", "", "route-card");
    row.append(el("p", `路线 ${index + 1} · ${ending?.title ?? "结局"}`));
    const decisions = route.path.slice(0, -1).flatMap((id, cursor) => {
      const node = story.nodes.find(item => item.id === id);
      const edge = node?.edges.find(item => item.to === route.path[cursor + 1]);
      return edge?.label ? [edge.label] : [];
    });
    row.append(el("small", decisions.join(" → ") || "无显式选择"));
    row.append(button("回到这条路线最后一次选择", () => onFork([...route.path])));
    panel.append(row);
  }
  return panel;
}
