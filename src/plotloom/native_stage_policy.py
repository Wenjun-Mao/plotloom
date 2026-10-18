"""Source-owned pins for local candidate-only stages."""
from hashlib import sha256
from pathlib import Path
import subprocess
from .creative_handoff_contracts import CreativeHandoffError

NATIVE_STAGES = {"bridge-intent", "bridge-presentation", "video-directions"}

def native_execution_pin(stage, repository: Path):
    name = stage.removeprefix("bridge-")
    document = f"docs/creative-workflow/native-{stage}.md"
    script = f"scripts/{'video_directions' if stage == 'video-directions' else 'native_bridge_' + name}.py"
    skill = f".agents/skills/plotloom-{name}-specialist/SKILL.md"
    dirty = subprocess.run(["git", "-C", str(repository), "status", "--porcelain", "--", "src/plotloom", script, document, skill], capture_output=True, text=True, check=True)
    if dirty.stdout.strip():
        raise CreativeHandoffError("execution_pin_missing", "native execution source must be committed before preparing a package")
    revision = subprocess.run(["git", "-C", str(repository), "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
    return {"upstreamRevision": revision, "upstreamSkillHash": sha256((repository/document).read_bytes()).hexdigest(),
        "specialistSkillHash": sha256((repository/skill).read_bytes()).hexdigest()}
