import { createRoot } from "react-dom/client";
import { useEffect, useState } from "react";

import "../src/styles.css";
import { CreatorWorkflowNavigation } from "../src/app/workspace/CreatorWorkflowNavigation";
import type { PageId } from "../src/app/workspace/contracts";
import { sourceWorkflowTarget } from "../src/app/workspace/sourceWorkflowNavigation";

type LocalRoute = { project: string; stage: PageId; hash: string };

function currentRoute(): LocalRoute {
  const query = new URLSearchParams(window.location.search);
  const stage = query.get("stage") === "characters" ? "characters" : "source";
  const hash = sourceWorkflowTarget(decodeURIComponent(window.location.hash.replace(/^#/, ""))) || "source";
  return { project: query.get("project") || "u1a-local-fixture-a", stage, hash };
}

function Fixture() {
  const [route, setRoute] = useState(currentRoute);
  useEffect(() => {
    const restore = () => setRoute(currentRoute());
    window.addEventListener("popstate", restore);
    return () => window.removeEventListener("popstate", restore);
  }, []);
  useEffect(() => {
    const target = route.stage === "source" ? route.hash : "characters";
    requestAnimationFrame(() => document.getElementById(target)?.scrollIntoView({ block: "start" }));
  }, [route]);

  const navigate = ({ stage, hash = "" }: { stage: PageId; hash?: string }) => {
    const target = stage === "source" ? sourceWorkflowTarget(hash || "source") || "source" : "";
    const next = { project: route.project, stage, hash: target };
    const query = new URLSearchParams({ project: next.project, stage: next.stage });
    history.pushState(null, "", `${location.pathname}?${query.toString()}${target ? `#${target}` : ""}`);
    setRoute(next);
  };
  const switchProject = () => {
    const project = route.project.endsWith("-a") ? "u1a-local-fixture-b" : "u1a-local-fixture-a";
    const next = { project, stage: "source" as const, hash: "art" };
    history.pushState(null, "", `${location.pathname}?project=${project}&stage=source#art`);
    setRoute(next);
  };

  return <div className="app-shell" data-testid="u1a-local-workflow-fixture" data-project-id={route.project}>
    <aside className="sidebar"><div className="brand"><div className="brand-mark">PL</div><div><strong>Plotloom</strong><small>LOCAL NAVIGATION FIXTURE</small></div></div><CreatorWorkflowNavigation projectId={route.project} activePage={route.stage} activeHash={route.hash} disabled={false} onNavigate={navigate} /><details className="workspace-tools-navigation"><summary>编辑与工具</summary><nav aria-label="编辑与工具"><button type="button" onClick={() => navigate({ stage: "storyboard" })}><strong>分镜工作台</strong></button></nav></details></aside>
    <div className="workspace-shell"><main id="workspace-main" className="page source-outline-page"><header className="page-header"><div><span>TEST-ONLY · LOCAL FIXTURE</span><h1>U1a creator workflow navigation</h1><p>Static in-page navigation fixture. It makes no API call, project write, provider call, generation request, or creative acceptance.</p></div><button type="button" onClick={switchProject}>切换本地 fixture 项目</button></header>
      <section className="notice warning"><strong>模拟边界：</strong>这是长期保留在仓库中的本地导航演示，不是用户项目、持久化状态或产品验收。真实项目级定位与读者回归由浏览器测试覆盖。</section>
      <section id="source" className="panel"><h2>来源与大纲</h2><p>来源、路线与接受由此拥有。链接可直接载入或在同页间导航。</p></section>
      <section id="characters" className="panel"><h2>角色</h2><p>角色及外观参考仍由角色工作区拥有。</p></section>
      <section id="art" className="panel"><h2>美术参考</h2><p>环境与道具参考的现状、缺失和下一步由该嵌入式拥有者说明。</p></section>
      <section id="script" className="panel"><h2>剧本</h2><p>当前剧本及其阅读入口由该嵌入式拥有者说明。</p></section>
      <section id="storyboard-review" className="panel"><h2>分镜评审</h2><p>这是来源绑定的只读评审证据，不是镜头与媒体工作台。</p></section>
      <section id="storyboard" className="panel"><h2>分镜工作台</h2><p>保留的旧编辑器入口在“编辑与工具”中；它没有被伪装成来源绑定的评审。</p></section>
    </main></div>
  </div>;
}

createRoot(document.getElementById("root")!).render(<Fixture />);
