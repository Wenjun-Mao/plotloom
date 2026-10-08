import { Button } from "../../components";

export type DraftNavigationIntent = "navigate" | "archive" | "close";

const intentCopy: Record<DraftNavigationIntent, {
  title: string; action: string; help: string; save: string; discard: string;
}> = {
  navigate: {
    title: "保存当前草稿？", action: "即将离开当前页面", save: "保存并切换", discard: "丢弃",
    help: "保存会按当前阶段的保存方式写入项目，不代表确认内容或批准。丢弃只移除本标签页尚未保存的修改；项目中已保存的草稿不会删除。",
  },
  archive: {
    title: "归档前保存当前修改？", action: "即将归档当前项目", save: "保存并归档", discard: "丢弃本页修改并归档",
    help: "保存会按当前阶段的保存方式写入项目，不代表确认内容或批准。丢弃只移除本标签页尚未保存的修改，已保存的草稿仍保留。归档后项目为只读，可在项目目录中恢复。",
  },
  close: {
    title: "保存草稿并关闭项目？", action: "即将关闭当前项目", save: "保存草稿并关闭", discard: "丢弃当前草稿并关闭",
    help: "保存会将修改保留为可恢复草稿，不会确认正式内容或批准。丢弃会删除当前阶段对应的那一份草稿，已确认内容不变；草稿处理成功后才会关闭项目。",
  },
};

export function DraftNavigationDialog({ intent, onSave, onDiscard, onCancel }: {
  intent: DraftNavigationIntent; onSave: () => void; onDiscard: () => void; onCancel: () => void;
}) {
  const copy = intentCopy[intent];
  return <div className="modal" role="dialog" aria-modal="true" aria-labelledby="draft-navigation-title">
    <button className="modal-backdrop" aria-label="继续编辑" onClick={onCancel} />
    <section className="modal-card compact">
      <header><div><span>未保存的草稿</span><h2 id="draft-navigation-title">{copy.title}</h2></div></header>
      <div className="modal-body"><div className="notice warning"><strong>{copy.action}</strong><span>{copy.help}</span></div></div>
      <footer>
        <Button variant="quiet" onClick={onCancel}>取消</Button>
        <Button variant="danger" onClick={onDiscard}>{copy.discard}</Button>
        <Button variant="primary" onClick={onSave}>{copy.save}</Button>
      </footer>
    </section>
  </div>;
}
