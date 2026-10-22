import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { expect, it } from "vitest";
import { TextBackendReadinessNotice } from "../src/app/workspace/TextBackendReadiness";
import type { TextBackendReadiness } from "../src/types";

const cases: Array<[TextBackendReadiness["state"], string]> = [
  ["disabled", "已停用"], ["missing_configuration", "配置不完整"], ["unverified", "尚未检测"],
  ["checking", "正在检测"], ["available", "连接正常"], ["unreachable", "无法连接"],
  ["authentication_failed", "认证失败"], ["model_mismatch", "模型不匹配"], ["capability_mismatch", "能力不匹配"],
];

it.each(cases)("presents %s naturally and preserves exact evidence in closed details", (state, label) => {
  const readiness: TextBackendReadiness = { state, profileId: "exact-profile", profileRevision: 7,
    reasonCode: `readiness.${state}`, observedAt: "2026-10-09T12:00:00Z" };
  const host = document.createElement("div");
  host.innerHTML = renderToStaticMarkup(createElement(TextBackendReadinessNotice, { readiness }));
  const primary = [...host.children[0].children].filter(element => element.tagName !== "DETAILS").map(element => element.textContent).join("");
  expect(primary).toContain(`就绪状态：${label}`);
  expect(primary).not.toContain(state); expect(primary).not.toContain(readiness.reasonCode);
  expect(primary).not.toContain("Profile"); expect(primary).not.toContain("Key");
  const details = host.querySelector("details")!;
  expect(details.open).toBe(false); expect(details.querySelector("summary")!.textContent).toBe("就绪诊断详情");
  expect([...details.querySelectorAll("code")].map(code => code.textContent)).toEqual([state, readiness.reasonCode]);
  expect(details.textContent).toContain("exact-profile r7");
});
