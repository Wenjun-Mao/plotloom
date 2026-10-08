import { afterEach, expect, it, vi } from "vitest";
import { revealMediaOwner } from "../src/features/media/media-owner-navigation";

afterEach(() => { document.body.replaceChildren(); vi.restoreAllMocks(); });

it("opens all owning disclosures before scrolling the keyframe target", () => {
  document.body.innerHTML = '<details><summary>Outer</summary><details><summary>Keyframes</summary><div id="shot-keyframe-review"></div></details></details>';
  const owners = Array.from(document.querySelectorAll("details"));
  const target = document.getElementById("shot-keyframe-review")!;
  const scroll = vi.fn(() => expect(owners.every((owner) => owner.open)).toBe(true));
  target.scrollIntoView = scroll;
  vi.spyOn(window, "requestAnimationFrame").mockImplementation((callback) => { callback(0); return 1; });
  revealMediaOwner(target.id);
  expect(scroll).toHaveBeenCalledExactlyOnceWith({ behavior: "smooth", block: "start" });
});

it("uses the same disclosure contract for identity deep links", () => {
  document.body.innerHTML = '<details><summary>References</summary><div id="shot-character-references"></div></details>';
  const target = document.getElementById("shot-character-references")!;
  target.scrollIntoView = vi.fn();
  vi.spyOn(window, "requestAnimationFrame").mockImplementation((callback) => { callback(0); return 1; });
  revealMediaOwner(target.id, "auto");
  expect(document.querySelector("details")!.open).toBe(true);
  expect(target.scrollIntoView).toHaveBeenCalledWith({ behavior: "auto", block: "start" });
});

it("leaves unknown or absent targets alone", () => {
  document.body.innerHTML = '<details><summary>Unrelated</summary><div id="unrelated"></div></details>';
  const schedule = vi.spyOn(window, "requestAnimationFrame");
  revealMediaOwner("unrelated");
  revealMediaOwner("shot-keyframe-review");
  expect(document.querySelector("details")!.open).toBe(false);
  expect(schedule).not.toHaveBeenCalled();
});
