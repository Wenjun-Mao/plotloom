import { createRoot } from "react-dom/client";
import { useState } from "react";
import { AutopilotWorkspace } from "../src/features/autopilot/AutopilotWorkspace";
import "../src/styles.css";
import "../src/selection-controls.css";
import "../src/creator-ui.css";

function Journey({ projectId }: { projectId: string }) {
  const [readback, setReadback] = useState("");
  const refresh = async () => {
    const value = await fetch(`/api/v2/projects/${projectId}/art`).then(response => response.json());
    setReadback(JSON.stringify(value.acceptedArt));
  };
  return <main><h1>文字修正 · 来源验证真实路径</h1><p>隔离项目，真实控制器与主机验证；仅候选文字由确定性 CLI 生成，无提供方调用。</p>
    <AutopilotWorkspace projectId={projectId} revision={1} readOnly={false} onChanged={refresh} onVideo={() => undefined}>
      <button onClick={() => void refresh()}>读取已采用美术</button><pre data-testid="adopted-readback" style={{ whiteSpace: "pre-wrap", overflowWrap: "anywhere", maxHeight: 200, overflow: "auto" }}>{readback}</pre>
    </AutopilotWorkspace>
  </main>;
}
void fetch("/api/v2/fixture/text-retry").then(response => response.json()).then(value => {
  createRoot(document.getElementById("root")!).render(<Journey projectId={value.projectId} />);
});
