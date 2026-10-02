import { expect, type Locator } from "@playwright/test";

// Explicit translations for the authored synthetic browser fixture only.
const translations: Record<string, string> = {
  "气密门向两侧弹开，阮星冲入控制室。": "The airtight doors spring apart and Ruan Xing rushes into the control room.",
  "金色与青色实体键从主控台升起。": "Gold and cyan physical keys rise from the main console.",
  "月城建筑群从黑暗中逐区亮起金光。": "Moon City's buildings illuminate district by district with golden light from darkness.",
  "救生舱门在青色蒸汽中缓慢开启。": "The life-support pod door slowly opens in cyan steam.",
  "控制室警报与通风系统底噪": "Control-room alarms and the background hum of ventilation.",
  "年轻女声、压低语速": "A young female voice speaking slowly.",
  "虚弱男声、语句清晰": "A weak male voice with clear words.",
  "克制但紧迫": "Restrained but urgent.",
};

export async function freezeReviewedFixtureDirections(panel: Locator) {
  const production = panel.locator("#video-production");
  if (!await production.evaluate(element => (element as HTMLDetailsElement).open)) await production.locator("summary").first().click();
  const review = panel.getByTestId("h3-directions-review");
  if (!await review.evaluate(element => (element as HTMLDetailsElement).open)) await review.locator("summary").click();
  await review.getByRole("button", { name: "读取当前来源" }).click();
  await expect(review.locator("textarea").first()).toBeVisible();
  for (const field of await review.locator(".h3-direction-field").all()) {
    const source = (await field.locator(".h3-direction-source").innerText()).replace(/^来源：/, "");
    const english = translations[source] ?? (/^[\x20-\x7e]+$/.test(source) ? source : undefined);
    expect(english, `Fixture needs an explicit faithful translation: ${source}`).toBeTruthy();
    await field.locator("textarea").fill(english!);
  }
  await review.getByRole("checkbox").check();
  await review.getByRole("button", { name: "预览完整 H3 提示词" }).click();
  await expect(review.getByTestId("h3-frozen-review-inputs")).toBeVisible();
  await review.getByRole("button", { name: "冻结此说明并准备原片" }).click();
}
