import { ProjectReportFrame } from "./ProjectReportFrame";

const reportCopy = {
  script: {
    subject: "剧本",
    explanation: "场次与台词已完整展开；报告内的折叠、复制和导出按钮已停用。",
  },
  storyboard: {
    subject: "分镜",
    explanation: "分段与提示词已完整展开；报告内的复制、导出和图片放大功能已停用。",
  },
} as const;

/** App-owned reading guidance never changes the original report or its isolation. */
export function StaticReportReader({ kind, url }: { kind: keyof typeof reportCopy; url: string }) {
  const { subject, explanation } = reportCopy[kind];
  return <details>
    <summary>阅读原始{subject}报告（只读）</summary>
    <p className="action-prerequisite">原始报告的只读展示：{explanation}原始报告独立保留，不会随当前{subject}修改。</p>
    <ProjectReportFrame sandbox="" referrerPolicy="no-referrer" title={`原始${subject}交付报告（只读）`} className="source-outline-report" url={url} />
  </details>;
}
