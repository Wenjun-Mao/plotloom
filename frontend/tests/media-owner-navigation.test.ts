import { afterEach, expect, it, vi } from "vitest";
import { revealMediaOwner } from "../src/features/media/media-owner-navigation";

afterEach(() => { document.body.replaceChildren(); vi.restoreAllMocks(); });

it("opens all owning disclosures before scrolling the keyframe target", () => {
  document.body.innerHTML = '<details><summary>Outer</summary><details><summary>Keyframes</summary><div id="shot-keyframe-review"></div></details></details>';
  const owners = Array.from(document.querySelectorAll("details"));
  const target = document.getElementById("shot-keyframe-review")!;
  const scroll = vi.spyOn(window, "scrollBy").mockImplementation(() => { expect(owners.every(owner => owner.open)).toBe(true); });
  vi.spyOn(window, "requestAnimationFrame").mockImplementation((callback) => { callback(0); return 1; });
  revealMediaOwner(target.id);
  expect(scroll).toHaveBeenCalledExactlyOnceWith({ behavior: "smooth", top: -12 });
});

it("uses the same disclosure contract for identity deep links", () => {
  document.body.innerHTML = '<details><summary>References</summary><div id="shot-character-references"></div></details>';
  const target = document.getElementById("shot-character-references")!;
  const scroll = vi.spyOn(window, "scrollBy").mockImplementation(() => {});
  vi.spyOn(window, "requestAnimationFrame").mockImplementation((callback) => { callback(0); return 1; });
  revealMediaOwner(target.id, "auto");
  expect(document.querySelector("details")!.open).toBe(true);
  expect(scroll).toHaveBeenCalledWith({ behavior: "auto", top: -12 });
});

it("leaves unknown or absent targets alone", () => {
  document.body.innerHTML = '<details><summary>Unrelated</summary><div id="unrelated"></div></details>';
  const schedule = vi.spyOn(window, "requestAnimationFrame");
  revealMediaOwner("unrelated");
  revealMediaOwner("shot-keyframe-review");
  expect(document.querySelector("details")!.open).toBe(false);
  expect(schedule).not.toHaveBeenCalled();
});
