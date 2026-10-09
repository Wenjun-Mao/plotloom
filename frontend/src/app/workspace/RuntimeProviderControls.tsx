import { Badge, Button } from "../../components";
import { formatUiTimestamp } from "../../ui-time";
import type { TextProviderProfilesResponse } from "../../types";
import type { useRuntimeCapabilities } from "./useRuntimeCapabilities";

type CapabilityRead = ReturnType<typeof useRuntimeCapabilities>;

export function ProviderSettingsLauncher({ capability, onOpen }: { capability: CapabilityRead; onOpen: () => void }) {
  if (capability.state === "failed") return <>
    <small role="status">暂时无法读取服务功能。</small>
    <Button variant="quiet" onClick={capability.retry}>重新读取服务功能</Button>
  </>;
  if (capability.state === "loading") return <small role="status">正在读取服务功能…</small>;
  if (!capability.data.apiTextPipeline) return <small>API 文本供应商未启用；助手配置请使用上方设置。</small>;
  return <><Button variant="quiet" onClick={onOpen}>供应商与会话密钥</Button><small>设置不会写入项目</small></>;
}

export function RuntimeTextStatus({ capability, catalog, loaded }: {
  capability: CapabilityRead; catalog: TextProviderProfilesResponse; loaded: boolean;
}) {
  if (capability.state !== "ready") return <Badge tone="warning">服务功能：{capability.state === "loading" ? "正在读取" : "尚未读入"}</Badge>;
  if (!capability.data.apiTextPipeline) return <Badge>API 文本供应商：未启用</Badge>;
  const active = loaded ? catalog.profiles.find(profile => profile.profileId === catalog.activeProfileId) : undefined;
  if (!active) return <Badge tone="warning">API 文本供应商：配置尚未读入</Badge>;
  const readiness = active.readiness;
  return <Badge tone={readiness?.state === "available" ? "ok" : ["unreachable", "authentication_failed", "model_mismatch", "capability_mismatch"].includes(readiness?.state || "unverified") ? "danger" : "warning"}>
    文本后端：{readiness?.state || "unverified"} · {active.profileId} · {readiness?.reasonCode || "readiness.not_checked"}
    {readiness?.observedAt ? ` · ${formatUiTimestamp(readiness.observedAt)}` : " · 未检测"}
  </Badge>;
}
