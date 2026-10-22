import { expect, it } from "vitest";
import { castTextPresentation, editCastText } from "../src/pages/cast-text-presentation";

it("separates only explicit suffix markers and round-trips their exact spacing", () => {
  for (const source of ["审慎（推断）", "轻柔 (推断)  ", "  温和  （推断）\n", "普通描述", "（推断）"]) {
    const view = castTextPresentation(source);
    expect(view.text + view.annotation).toBe(source);
    expect(editCastText(source, view.text)).toBe(source);
  }
  expect(editCastText("审慎（推断）", "内敛")).toBe("内敛（推断）");
});

it("does not reinterpret prose, internal parentheses, or unrecognized qualifications", () => {
  for (const source of ["把停顿理解为犹豫属于推断，不能把任一选择演成错误。", "原文未描述容貌；这些细节均为推断。", "审慎（推断），但愿意回应", "轻柔（待确认）"]) {
    expect(castTextPresentation(source)).toEqual({ text: source, annotation: "" });
  }
  expect(castTextPresentation(undefined)).toEqual({ text: "", annotation: "" });
});
