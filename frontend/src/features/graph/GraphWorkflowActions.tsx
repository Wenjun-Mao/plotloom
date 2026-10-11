import { useId, type ComponentProps } from "react";
import { Button } from "../../components";

type ActionControl = Pick<ComponentProps<typeof Button>, "disabled" | "onClick" | "variant">;
type ActionId = "save" | "confirm" | "apply";
const actions: { id: ActionId; label: string; explanation: string }[] = [
  { id: "save", label: "保存图草稿", explanation: "保存修改，仍是草稿。" },
  { id: "confirm", label: "确认图内容", explanation: "确认版本，不应用路线。" },
  { id: "apply", label: "应用到故事路线", explanation: "启用已确认的故事路线。" },
];

/** Shared presentation only; each view retains its own admission and handlers. */
export function GraphWorkflowActions(controls: Record<ActionId, ActionControl> & { status?: string }) {
  const id = useId(), titleId = `${id}-title`, scopeId = `${id}-scope`, generationHelpId = `${id}-generation`;
  return <section className="graph-workflow-bar" aria-labelledby={titleId} aria-describedby={scopeId}>
    <header>
      <h2 id={titleId}>整张剧情图 · 保存与应用</h2>
      <p id={scopeId} className="graph-workflow-scope">作用于全部节点和连接，不仅是当前选中的节点。</p>
    </header>
    <div className="graph-workflow-actions" role="group" aria-label="保存、确认与应用">
      {actions.map(action => {
        const helpId = `${id}-${action.id}`;
        return <div className="graph-workflow-action" key={action.id}>
          <Button {...controls[action.id]} aria-describedby={`${scopeId} ${helpId} ${generationHelpId}`}>{action.label}</Button>
          <span id={helpId}>{action.explanation}</span>
        </div>;
      })}
    </div>
    <footer>
      <p id={generationHelpId} className="graph-workflow-generation-help">三项操作均不会生成影片。</p>
      {controls.status && <p className="graph-workflow-status">{controls.status}</p>}
    </footer>
  </section>;
}
