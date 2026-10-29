"""Duplicated standalone timing helpers must match trusted Python rules exactly."""
import json
import subprocess
from pathlib import Path

from plotloom.canonical_schema import DialogueDeliveryPace, default_dialogue_timing_profile

ROOT = Path(__file__).resolve().parents[1]


def test_standalone_rules_match_canonical_supported_and_fallback_policy():
    profile = default_dialogue_timing_profile()
    texts = ["I am here.", "Please keep the light on.", "extraordinarily", "请把灯留着。",
        " A 😀 B ", " A\nB\tC ", "\u0085A\u001cB\u3000", "", "   ", "one " * 30]
    cases = [{"text": text, "language": language, "delivery": delivery.value}
        for language in ("zh-CN", "en-US", "en", "fr-FR")
        for delivery in DialogueDeliveryPace for text in texts]
    expected = [profile.estimate_text_duration_units(**case) for case in cases]
    program = """
import { readFileSync } from 'node:fs';
import { dialogueMilliseconds as script } from './third_party/shuohao-skills/skills/novel-script/scripts/dialogue-timing.mjs';
import { dialogueMilliseconds as storyboard } from './third_party/shuohao-skills/skills/novel-storyboard/scripts/dialogue-timing.mjs';
const cases = JSON.parse(readFileSync(0, 'utf8'));
process.stdout.write(JSON.stringify([script, storyboard].map(f => cases.map(c => f(c.text, c.language, c.delivery)))));
"""
    result = subprocess.run(["node", "--input-type=module", "-e", program], cwd=ROOT,
        input=json.dumps(cases), capture_output=True, text=True, timeout=15, check=True)
    assert json.loads(result.stdout) == [expected, expected]
