import { Button } from "../../components";
import { ScriptPanel } from "../../pages/ScriptPanel";
import { GraphNodeDetails } from "./GraphNodeDetails";
import { useGraphWorkbench } from "./GraphWorkbenchContext";
import type { CreatorNavigate } from "./CreatorWorkbench";

export function CreatorStoryInspector({ projectId, disabled, active, onNavigate }: { projectId: string; disabled: boolean; active: boolean; onNavigate: CreatorNavigate }) {
  const owner = useGraphWorkbench();
  return <div hidden={!active}><GraphNodeDetails disabled={disabled} />
    <details><summary>场景、动作与对白</summary>
      <p>剧本与图草稿有独立的确认版本。未确认的图修改不会改写既有场次。</p>
      <ScriptPanel projectId={projectId} readOnly={disabled} active={active} refreshToken={owner.state?.bindingHash} contextSectionId={owner.selectedNodeId ?? undefined} onContinue={() => onNavigate("source", "storyboard-review")} />
      <Button onClick={() => onNavigate("source", "script")}>打开完整剧本工作台</Button>
    </details>
  </div>;
}
