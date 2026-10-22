import type { TextBackendReadiness } from "../../types";
import { formatUiTimestamp } from "../../ui-time";

type Presentation = { label: string; remediation: string; tone: "ok" | "warning" | "danger" };
const states: Record<TextBackendReadiness["state"], Presentation> = {
  disabled: { label: "已停用", remediation: "启用此模型配置后，再测试连接。", tone: "warning" },
  missing_configuration: { label: "配置不完整", remediation: "补齐 API 根地址、文本模型和所需认证信息后，再测试连接。", tone: "warning" },
  unverified: { label: "尚未检测", remediation: "点击“测试连接”检查当前配置；此操作不生成文本。", tone: "warning" },
  checking: { label: "正在检测", remediation: "正在检查服务连接，请稍候；此操作不生成文本。", tone: "warning" },
  available: { label: "连接正常", remediation: "文本服务已就绪，可用于新的 API 文本任务。", tone: "ok" },
  unreachable: { label: "无法连接", remediation: "检查 API 根地址、网络和服务进程后，再测试连接。", tone: "danger" },
  authentication_failed: { label: "认证失败", remediation: "提供可用的服务器密钥或当前标签页临时密钥后，再测试连接。", tone: "danger" },
  model_mismatch: { label: "模型不匹配", remediation: "将文本模型改为服务提供的精确模型标识后，保存并测试连接。", tone: "danger" },
  capability_mismatch: { label: "能力不匹配", remediation: "核对受信任适配器、端点协议和能力声明后，再测试连接。", tone: "danger" },
};

export const readinessPresentation = (state: TextBackendReadiness["state"]) => states[state];

/** Exact protocol evidence stays readable, separate from the primary instruction. */
export function ReadinessDiagnostics({ readiness, label = "就绪诊断详情" }: {
  readiness: TextBackendReadiness; label?: string;
}) {
  return <details><summary>{label}</summary>
    <p>模型配置 {readiness.profileId} r{readiness.profileRevision} · {readiness.observedAt ? formatUiTimestamp(readiness.observedAt) : "尚未检测"}</p>
    <p>状态代码：<code>{readiness.state}</code> · 诊断代码：<code>{readiness.reasonCode}</code></p>
  </details>;
}

export function TextBackendReadinessNotice({ readiness }: { readiness: TextBackendReadiness }) {
  const presentation = readinessPresentation(readiness.state);
  return <div className="notice">
    <strong>就绪状态：{presentation.label}</strong><span>{presentation.remediation}</span>
    <ReadinessDiagnostics readiness={readiness} />
  </div>;
}
