import { Button, PageHeader, Panel } from "../../components";
import type { ProjectLoadFailure } from "./contracts";
import { projectUnavailableCopy } from "./projectAvailability";

export function ProjectUnavailable({ projectId, failure, onRetry, onDirectory }: {
  projectId: string; failure: ProjectLoadFailure | undefined; onRetry: () => void; onDirectory: () => void;
}) {
  const current = failure?.projectId === projectId ? failure : undefined;
  const copy = projectUnavailableCopy[current?.kind ?? "unavailable"];
  return <section className="page" data-testid="workspace-project-unavailable">
    <PageHeader title={copy.title} description={copy.description} />
    <Panel>
      <p>当前链接与页面位置仍保留。重新读取只检查已有内容，不会保存、生成或自动重新打开项目。</p>
      <div className="button-row">
        <Button variant={current?.kind === "closed" ? "primary" : "quiet"} onClick={onDirectory}>打开项目目录</Button>
        <Button variant={current?.kind === "closed" ? "quiet" : "primary"} onClick={onRetry}>重新读取项目</Button>
      </div>
      <ProjectLoadDetails projectId={projectId} failure={current} />
    </Panel>
  </section>;
}

export function ProjectLoadDetails({projectId, failure}: {projectId: string; failure: ProjectLoadFailure | undefined}) {
  return <details className="project-load-details"><summary>{failure?.kind === "continuation-failed" ? "查看续跑详情" : "查看读取详情"}</summary><p>项目：{projectId}</p>
    {failure?.projectId === projectId && <pre>{failure.diagnostic}</pre>}
  </details>;
}
