"""Exact Script-owned H3 speech spans; quoted instructions have no spoken authority."""
import re

from .provider_literals import text_hash


def script_literal_claims(request, candidate):
    if request.stage != "storyboard":
        return []
    script = request.input_artifacts.get("script.json", {})
    result = []
    for ei,episode in enumerate(candidate.get("episodes", [])):
        match_ep = next(((index,ep) for index,ep in enumerate(script.get("episodes", [])) if ep["ep"] == episode["ep"]), None)
        for si,segment in enumerate(episode.get("segments", [])):
            allowed = []
            if match_ep and 0 < segment.get("sceneIndex", 0) <= len(match_ep[1].get("scenes", [])):
                scene_index = segment["sceneIndex"] - 1
                for fi,flow in enumerate(match_ep[1]["scenes"][scene_index].get("flow", [])):
                    if not isinstance(flow.get("line"), str) or not any(cut.get("beats", [0,0])[0] <= fi+1 <= cut.get("beats", [0,0])[1] for cut in segment.get("cuts", [])):
                        continue
                    label = {"zh":"Chinese","zh-CN":"Chinese","en":"English","en-US":"English"}.get(flow.get("language",script.get("lang","zh")))
                    path = f"$.inputs.script_json.episodes[{match_ep[0]}].scenes[{scene_index}].flow[{fi}].line"
                    allowed.append((label,flow["line"],path))
            prompt = segment.get("h3Prompt", "")
            matches = list(re.finditer(r"<d>\[([^\]]+)\]([\s\S]*?)</d>", prompt))
            if len(re.findall(r"</?d>", prompt)) != 2*len(matches):
                raise ValueError("malformed or unowned spoken block")
            for match in matches:
                found = next(((text,path) for label,text,path in allowed if label == match[1] and match[2] in {text," "+text,text+" "," "+text+" "}),None)
                if found is None:
                    raise ValueError("spoken block differs from exact Script-owned dialogue")
                text,path = found; start = match.start(2)+(0 if match[2].startswith(text) else 1)
                result.append({"role":"spoken_dialogue", "candidateSpan":{"path":f"$.episodes[{ei}].segments[{si}].h3Prompt","start":start,"end":start+len(text),"text":text},
                    "sourceSpan":{"path":path,"start":0,"end":len(text),"text":text},"candidateFieldHash":text_hash(prompt),
                    "sourceFieldHash":text_hash(text),"sourceFactId":None})
    return result
