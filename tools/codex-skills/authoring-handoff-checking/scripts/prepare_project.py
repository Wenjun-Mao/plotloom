"""Prepare current-source episode cases for the named Plotloom production."""
import argparse
import copy
import re
from pathlib import Path
from common import digest, evidence, pin, read, save, verify_case


def prepare(root, output):
    root = Path(root).resolve()
    base = root / "docs/roadmap/别叫我的名字-shuohao-production"
    meta_path = base / "storyboard-sources.json"
    overrides_path = base / "selected-source-overrides.json"
    combined_path = base / "storyboard.json"
    meta, overrides, combined = read(meta_path), read(overrides_path), read(combined_path)
    if meta["combinedSha256"] != digest(combined_path) or meta["selectedSegmentRevisions"] != overrides:
        raise ValueError("current source metadata is stale")
    sources = {"manifest": pin(meta_path), "overrides": pin(overrides_path), "storyboard": pin(combined_path)}
    for name in ("outline", "script", "staging"):
        row = meta[name]
        if digest(row["file"]) != row["sha256"]:
            raise ValueError(f"stale {name}")
        sources[name] = pin(row["file"])
    expected = []
    original_lines = []
    for i, row in enumerate(meta["storyboards"]):
        if row["episode"] != f"E{i+1:02}" or Path(row["file"]).resolve() != (base / f"storyboard/E{i+1:02}/storyboard.json").resolve() or digest(row["file"]) != row["sha256"]:
            raise ValueError("stale episode source")
        name = f"episode{i+1}"
        sources[name] = pin(row["file"])
        ep = copy.deepcopy(read(row["file"])["episodes"][0])
        for j, segment in enumerate(ep["segments"]):
            sid = segment["id"]
            original_lines.extend(re.findall(r"<d>(.*?)</d>", segment["h3Prompt"]))
            if sid in overrides:
                rev = overrides[sid]
                path = Path(rev["sourceFile"]).resolve(strict=True)
                if not path.is_relative_to((base / "storyboard").resolve()) or digest(path) != rev["sourceSha256"]:
                    raise ValueError(f"stale override: {sid}")
                name = f"override-{sid}"
                sources[name] = pin(path)
                replacements = [s for e in read(path)["episodes"] for s in e["segments"] if s["id"] == sid]
                if len(replacements) != 1 or [(c["beats"], c["seconds"]) for c in replacements[0]["cuts"]] != [(c["beats"], c["seconds"]) for c in segment["cuts"]]:
                    raise ValueError(f"invalid override: {sid}")
                ep["segments"][j] = replacements[0]
        expected.append(ep)
    if expected != combined["episodes"] or set(overrides) - {s["id"] for e in expected for s in e["segments"]}:
        raise ValueError("combined source differs from current authority")
    selected_lines = [line for e in combined["episodes"] for segment in e["segments"]
                      for line in re.findall(r"<d>(.*?)</d>", segment["h3Prompt"])]
    if original_lines != selected_lines:
        raise ValueError("override changed original dialogue blocks")
    opening = root / "docs/roadmap/别叫我的名字-storyboard-shuohao-sample/别叫我的名字-E01-01-storyboard.json"
    if read(opening)["episodes"][0]["segments"][0] != combined["episodes"][0]["segments"][0]:
        raise ValueError("opening source differs")
    sources["opening"] = pin(opening)
    outline, script, staging = (read(sources[k]["file"]) for k in ("outline", "script", "staging"))
    for i, ep in enumerate(combined["episodes"]):
        n = ep["ep"]
        if outline["episodes"][i]["ep"] != n or script["episodes"][i]["ep"] != n:
            raise ValueError("episode order mismatch")
        ev = [evidence("outline", f"/episodes/{i}", "outline"), evidence("script", f"/episodes/{i}", "script")]
        ev += [evidence("staging", f"/scenes/{j}", f"staging-{j+1}") for j, x in enumerate(staging["scenes"]) if x["ep"] == n]
        for direction, neighbor in (("previous", i - 1), ("next", i + 1)):
            if 0 <= neighbor < len(combined["episodes"]):
                ev.append(evidence("outline", f"/episodes/{neighbor}", f"{direction}:outline"))
                ev.append(evidence("script", f"/episodes/{neighbor}", f"{direction}:script"))
                neighbor_segments = combined["episodes"][neighbor]["segments"]
                j = len(neighbor_segments) - 1 if direction == "previous" else 0
                for key in ("cuts", "blocking", "soundscape", "h3Prompt"):
                    if key in neighbor_segments[j]:
                        ev.append(evidence("storyboard", f"/episodes/{neighbor}/segments/{j}/{key}", f"{direction}:{key}"))
        for j, segment in enumerate(ep["segments"]):
            sid = segment["id"]
            for key in ("cuts", "blocking", "soundscape", "h3Prompt"):
                if key in segment:
                    ev.append(evidence("storyboard", f"/episodes/{i}/segments/{j}/{key}", f"{sid}:{key}"))
        case = {"schemaVersion": 1, "skillVersion": "0.1.1", "caseId": f"E{n:02}", "sources": sources, "evidence": ev}
        verify_case(case)
        save(Path(output) / f"E{n:02}.json", case)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--project", required=True)
    p.add_argument("--output", required=True, help="new output directory")
    args = p.parse_args()
    out = Path(args.output)
    if out.exists():
        raise ValueError("output directory already exists")
    prepare(args.project, out)


if __name__ == "__main__":
    main()
