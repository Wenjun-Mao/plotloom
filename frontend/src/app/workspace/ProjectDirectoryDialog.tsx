import { Button, ErrorNotice } from "../../components";
import type { ProjectListItem } from "../../types";
import type { LifecycleAction } from "./useProjectLifecycle";

export function ProjectDirectoryDialog({ projects, currentProjectId, showArchived, error, notice, loading, busy = false, hasMore, onLoadMore, onArchived, onBlank, onSample, onOpen, onAction, explicitProjectClose, onClose }: {
  projects: ProjectListItem[]; currentProjectId?: string; showArchived: boolean; error: string; notice?: string; loading: boolean; busy?: boolean; hasMore: boolean;
  onLoadMore: () => void; onArchived: (show: boolean) => void; onBlank: () => void; onSample: () => void;
  onOpen: (project: ProjectListItem) => void; onAction: (project: ProjectListItem, action: LifecycleAction) => Promise<void>;
  explicitProjectClose: boolean; onClose: () => void;
}) {
  const rowBusy = busy || loading;
  return <div className="modal" role="dialog" aria-modal="true" aria-labelledby="project-directory-title">
    <button className="modal-backdrop" aria-label="关闭窗口" disabled={busy} onClick={onClose} />
    <section className="modal-card directory-dialog">
      <header><div><span>选择已有项目或创建新项目</span><h2 id="project-directory-title">项目目录</h2></div><button aria-label="关闭窗口" disabled={busy} onClick={onClose}>×</button></header>
      <div className="modal-body">
        <div className="directory-onboarding"><Button variant="primary" disabled={busy} onClick={onBlank}>新建空白项目</Button><Button disabled={busy} onClick={onSample}>打开示例项目</Button><label><input type="checkbox" disabled={busy} checked={showArchived} onChange={event => onArchived(event.target.checked)} /> 显示归档项目</label></div>
        <p className="action-prerequisite">关闭项目不会删除内容；下次可重新打开。归档用于收起项目，永久删除是单独的操作。</p>
        {loading && <p className="action-prerequisite" role="status">正在读取项目目录，请稍候。</p>}
        {notice && <div className="notice" role="status">{notice}</div>}
        {error && <ErrorNotice message={error} />}
        {!error && !loading && !projects.length && <div className="empty-state"><strong>还没有可用项目</strong><p>从空白项目开始，或先浏览教学示例。</p></div>}
        <div className="directory-list">{projects.map(item => {
          const archived = item.lifecycleStatus === "archived" || Boolean(item.archivedAt);
          const closed = item.operationalState === "closed";
          return <article key={item.id} className="directory-item" data-project-id={item.id}>
            <button className="directory-open" disabled={rowBusy} onClick={() => onOpen(item)}><strong>{item.brief.title || "未命名项目"}</strong><small>{closed ? "已关闭 · 可安全复制" : archived ? "已归档 · 只读" : item.id === currentProjectId ? "当前项目" : "可打开"} · r{item.revision} · {new Date(item.updatedAt).toLocaleString()}</small></button>
            <div className="directory-actions">
              <Button variant="quiet" disabled={rowBusy} onClick={() => void onAction(item, "duplicate")}>复制</Button>
              {closed ? <Button variant="quiet" disabled={rowBusy} onClick={() => void onAction(item, "open")}>重新打开</Button> : archived ? <><Button variant="quiet" disabled={rowBusy} onClick={() => void onAction(item, "restore")}>恢复</Button><Button variant="danger" disabled={rowBusy} onClick={() => void onAction(item, "delete")}>永久删除</Button></> : <>
                <Button variant="quiet" disabled={rowBusy} onClick={() => void onAction(item, "archive")}>归档</Button>
                {explicitProjectClose && <><Button variant="quiet" disabled={rowBusy} onClick={() => void onAction(item, "close")}>保存并关闭项目</Button><Button variant="danger" disabled={rowBusy} onClick={() => void onAction(item, "force_close")}>强制关闭</Button></>}
              </>}
            </div>
          </article>;
        })}</div>
        {hasMore && <div className="directory-more"><Button disabled={loading || busy} onClick={onLoadMore}>{loading ? "正在加载…" : "加载更多项目"}</Button></div>}
      </div>
      <footer><Button variant="quiet" disabled={busy} onClick={onClose}>关闭窗口</Button></footer>
    </section>
  </div>;
}
