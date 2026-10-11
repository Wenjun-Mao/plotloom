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
export function GraphWorkflowActions(controls: Record<ActionId, ActionControl>) {
  const id = useId(), generationHelpId = `${id}-generation`;
  return <div className="graph-workflow-actions" role="group" aria-label="保存、确认与应用">
    {actions.map(action => {
      const helpId = `${id}-${action.id}`;
      return <div className="graph-workflow-action" key={action.id}>
        <Button {...controls[action.id]} aria-describedby={`${helpId} ${generationHelpId}`}>{action.label}</Button>
        <span id={helpId}>{action.explanation}</span>
      </div>;
    })}
    <p id={generationHelpId} className="graph-workflow-generation-help">三项操作均不会生成影片。</p>
  </div>;
}
