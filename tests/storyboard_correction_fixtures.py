"""Fresh prospective Storyboard packets; no retained campaign mutation."""
import json
import shutil
import subprocess
from copy import deepcopy
from pathlib import Path

from tests.production_bridge_fixtures import _source_shaped_review_board
from tests.storyboard_brief_fixtures import real_example_request, canonical_example_schedule, brief_board

ROOT = Path(__file__).resolve().parents[1]


def bad_segment(board):
    result = deepcopy(board)
    first, second = result['episodes'][0]['segments'][:2]
    first['cuts'] += second['cuts'][:4]
    second['cuts'] = second['cuts'][4:]
    return result


def board_for_request(request):
    inputs = request['inputArtifacts']
    episodes = [item['episode'] for item in inputs['storyboard-admission.json']['sectionBindings']]
    value = _source_shaped_review_board(seconds=3, episodes=episodes)
    for episode in value['episodes']:
        for segment in episode['segments']:
            for cut in segment['cuts']:
                cut['characters'] = ['keeper']
    style = inputs.get('storyboard-style-contract.json')
    return brief_board(value, style['direction']) if style else value


def storyboard_case(tmp_path, *, saved=True):
    request, board, _binding = real_example_request('restrained watercolor collage')
    if not saved:
        artifacts = dict(request.input_artifacts)
        artifacts.pop('storyboard-style-contract.json')
        request = request.model_copy(update={'input_artifacts': artifacts})
        original = json.loads((ROOT / 'third_party/shuohao-skills/skills/novel-storyboard/examples/渡口-storyboard.json').read_bytes())
        board = canonical_example_schedule(artifacts['script.json'], original)
        board['params'] = dict(artifacts['storyboard-admission.json']['reviewTiming'])
    request = request.model_copy(update={'content_validation_contract': 'plotloom.typed-content-result.v1'})
    package = tmp_path / 'package'
    (package / 'inputs').mkdir(parents=True)
    for name, value in request.input_artifacts.items():
        (package / 'inputs' / name).write_text(json.dumps(value))
    return request, board


def run_typed(tmp_path, request, board):
    (tmp_path / 'package/request.json').write_text(json.dumps(request.model_dump(mode='json', by_alias=True)))
    (tmp_path / 'storyboard.json').write_text(json.dumps(board))
    return subprocess.run([shutil.which('node'), str(ROOT / 'scripts/storyboard-content-validation.mjs'),
        str(tmp_path / 'storyboard.json'), str(tmp_path / 'package/request.json')], capture_output=True, timeout=20)
