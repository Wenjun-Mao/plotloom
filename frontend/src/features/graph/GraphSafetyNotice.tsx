import { useGraphWorkbench } from "./GraphWorkbenchContext";

export interface GraphSafetyDiagnostic {
  code: string;
  identity: string;
  severity: number;
  previousSeverity: number;
  facts: Record<string, unknown>;
}

export function graphSafetyDiagnostics(value: unknown): GraphSafetyDiagnostic[] | null {
  if (!value || typeof value !== "object" || !("code" in value) || value.code !== "graph_edit_unsafe"
    || !("diagnostics" in value) || !Array.isArray(value.diagnostics) || !value.diagnostics.length) return null;
  return value.diagnostics.every(item => item && typeof item.code === "string" && typeof item.identity === "string"
    && typeof item.severity === "number" && typeof item.previousSeverity === "number" && item.facts && typeof item.facts === "object")
    ? value.diagnostics : null;
}

function guidance(item: GraphSafetyDiagnostic, title: string): [string, string] {
  const facts = item.facts;
  switch (item.code) {
    case "out_degree": return [`「${title}」修改后有 ${facts.actual} 条输出连接，最多允许 ${facts.limit} 条。`,
      facts.nodeKind === "ending" ? "结局不能连接后续。请选择其他起点。" : facts.nodeKind === "decision"
        ? "请复用或调整现有选项连接，或先删除一个选项，再添加新分支。" : "普通节点只能有一条后续。请调整原连接，或使用选择点表达分支。"];
    case "node_capacity": return [`修改后共有 ${facts.actual} 个节点，简报的节点预算为 ${facts.limit} 个。`, "请复用或删除现有节点，或先在简报中调整节点预算。"];
    case "edge_kind": return [`「${title}」的连接类型与节点类型不符。`, "选择点需要选项连接；其他节点需要普通后续。请调整连接的起点或类型。"];
    case "self_link": return [`「${title}」不能连接到自身。`, "请选择其他目标节点。"];
    case "cycle": return ["这次连接会新增或加重循环路线。", "请选择不会返回上游节点的目标，或先调整现有路线。"];
    case "start_input": return [`「${title}」是开场，不能接收输入连接。`, "请选择其他目标节点。"];
    case "unreviewed_merge": return [`「${title}」修改后接收 ${facts.actual} 个不同起点的输入，尚未声明汇合。`, "请在专业工作台明确添加并审阅汇合，或调整重复入口。"];
    case "unknown_endpoint": return ["连接引用了当前图中不存在的节点。", "请重新选择当前图中的起点或目标。"];
    case "invalid_start": return ["当前开场标记没有指向开场节点。", "请在专业工作台选择有效的开场节点。"];
    case "multiple_starts": return [`修改后有 ${facts.actual} 个开场节点，最多允许 ${facts.limit} 个。`, "请保留一个开场，调整其他节点类型。"];
    case "duplicate_node": case "duplicate_edge": case "duplicate_section":
      return ["修改产生了重复的结构标识。", "请重新读取图草稿，再准备修改；如重复持续出现，请核对技术详情。"];
    default: return ["这次修改新增或加重了结构问题。", "请调整结构后重新准备预览，并核对技术详情。"];
  }
}

export function GraphSafetyNotice({ className }: { className?: string }) {
  const owner = useGraphWorkbench();
  if (!owner.error) return null;
  const diagnostics = graphSafetyDiagnostics(owner.errorDetails);
  if (!diagnostics) return <p className={className} role="alert">{owner.error}</p>;
  return <section className={className} role="alert" aria-label="结构修改未通过">
    <strong>结构修改未通过</strong>
    {diagnostics.map(item => {
      const nodeId = item.facts.nodeId;
      const title = owner.draft?.mapping.sections.find(section => section.sectionId === nodeId)?.title.trim() || "待填写节点";
      const [constraint, action] = guidance(item, title);
      return <div key={item.identity}><p>{constraint}</p><p>{action}</p></div>;
    })}
    <p>本次结构修改未保存。调整后可重新准备预览。</p>
    <details><summary>技术详情</summary><pre>{JSON.stringify(owner.errorDetails, null, 2)}</pre></details>
  </section>;
}
