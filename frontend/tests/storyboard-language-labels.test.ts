import { expect, it } from "vitest";
import { cameraLabel, shotSizeLabel } from "../src/pages/storyboard-presentation";

it("renders current upstream shot sizes and camera directions in Chinese without changing their IDs", () => {
  for (const value of ["extreme-wide", "wide", "medium", "close", "extreme-close"])
    expect(shotSizeLabel(value)).toMatch(/[\u3400-\u9fff]/);
  for (const value of ["Static Shot", "Push In", "Pull Out", "Zoom In", "Zoom Out", "Pan Left", "Pan Right",
    "Truck Left", "Truck Right", "Tilt Up", "Tilt Down", "Pedestal Up", "Pedestal Down", "Arc Shot",
    "Tracking Shot", "Shake Slightly", "Shake Strongly", "POV", "Roll Clockwise", "Roll Counterclockwise"])
    expect(cameraLabel(value)).toMatch(/[\u3400-\u9fff]/);
  expect(cameraLabel("Authored custom movement")).toBe("Authored custom movement");
});
